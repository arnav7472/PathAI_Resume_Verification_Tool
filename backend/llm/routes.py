"""FastAPI routes for the V2 six-stage AI pipeline.

POST /v2/analyze runs the deterministic pipeline in backend/llm/pipeline.py
(no LLM/API call) and persists the complete typed result via
backend/llm/service.py. Manager-only, mirroring the auth pattern used by
/rank and /reports.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.auth.depends import require_role
from backend.db.config import get_db
from backend.db.models import User

from . import pipeline
from .schemas import (
    CandidateProfile,
    Explanation,
    JobProfile,
    MatchAnalysis,
    MatchScore,
    SkillGaps,
)
from .service import save_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2", tags=["v2-analyze"])


class AnalyzeV2Request(BaseModel):
    """Request body for POST /v2/analyze."""

    candidate_name: str = Field(..., min_length=1, max_length=500)
    resume_text: str = Field(..., min_length=1, max_length=200_000)
    job_description: str = Field(..., min_length=1, max_length=100_000)


class AnalyzeV2Response(BaseModel):
    """Response body for POST /v2/analyze: the complete typed pipeline result."""

    id: int
    candidate_name: str
    candidate_profile: CandidateProfile
    job_profile: JobProfile
    match_analysis: MatchAnalysis
    match_score: MatchScore
    explanation: Explanation
    skill_gaps: SkillGaps


@router.post("/analyze", response_model=AnalyzeV2Response)
async def analyze_v2(
    payload: AnalyzeV2Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> AnalyzeV2Response:
    """Run the six-stage V2 pipeline (Resume+JD -> ... -> SkillGaps) and persist it."""

    resume_text = payload.resume_text.strip()
    job_description = payload.job_description.strip()
    candidate_name = payload.candidate_name.strip()

    if not resume_text:
        raise HTTPException(status_code=400, detail="resume_text must not be empty.")
    if not job_description:
        raise HTTPException(status_code=400, detail="job_description must not be empty.")
    if not candidate_name:
        raise HTTPException(status_code=400, detail="candidate_name must not be empty.")

    try:
        candidate_profile = pipeline.build_candidate_profile(resume_text)
        job_profile = pipeline.build_job_profile(job_description)
        match_analysis = pipeline.analyze_match(candidate_profile, job_profile)
        match_score = pipeline.compute_match_score(match_analysis)
        explanation = pipeline.generate_explanation(match_analysis, match_score)
        skill_gaps = pipeline.compute_skill_gaps(candidate_profile, job_profile)
    except Exception as exc:
        logger.exception("V2 analysis pipeline failed for candidate=%s", candidate_name)
        raise HTTPException(
            status_code=500,
            detail="Analysis pipeline failed to process the request.",
        ) from exc

    try:
        record = save_analysis(
            db,
            user_id=current_user.id,
            candidate_name=candidate_name,
            job_description=job_description,
            candidate_profile=candidate_profile,
            job_profile=job_profile,
            match_analysis=match_analysis,
            match_score=match_score,
            explanation=explanation,
            skill_gaps=skill_gaps,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist V2 analysis for candidate=%s", candidate_name)
        raise HTTPException(
            status_code=500,
            detail="Failed to persist analysis result.",
        ) from exc

    logger.info(
        "V2 analysis persisted id=%d user_id=%d candidate=%s overall_score=%d",
        record.id, current_user.id, candidate_name, match_score.overall_score,
    )

    return AnalyzeV2Response(
        id=record.id,
        candidate_name=candidate_name,
        candidate_profile=candidate_profile,
        job_profile=job_profile,
        match_analysis=match_analysis,
        match_score=match_score,
        explanation=explanation,
        skill_gaps=skill_gaps,
    )


__all__ = ["router", "AnalyzeV2Request", "AnalyzeV2Response"]
