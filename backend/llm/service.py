"""Persistence service for V2 six-stage AI pipeline analysis results.

Follows the same pattern as backend/db/report_service.py: a typed model in,
a Text/JSON-blob row out, owned by the requesting user.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.db.models import V2Analysis

from .schemas import (
    CandidateProfile,
    Explanation,
    JobProfile,
    MatchAnalysis,
    MatchScore,
    SkillGaps,
)


def save_analysis(
    db: Session,
    user_id: int,
    candidate_name: str,
    job_description: str,
    candidate_profile: CandidateProfile,
    job_profile: JobProfile,
    match_analysis: MatchAnalysis,
    match_score: MatchScore,
    explanation: Explanation,
    skill_gaps: SkillGaps,
) -> V2Analysis:
    """Persist a complete typed V2 analysis result, owned by user_id."""
    record = V2Analysis(
        user_id=user_id,
        candidate_name=candidate_name,
        job_description=job_description,
        overall_score=match_score.overall_score,
        candidate_profile=candidate_profile.model_dump_json(),
        job_profile=job_profile.model_dump_json(),
        match_analysis=match_analysis.model_dump_json(),
        match_score=match_score.model_dump_json(),
        explanation=explanation.model_dump_json(),
        skill_gaps=skill_gaps.model_dump_json(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_analysis_by_id(db: Session, analysis_id: int, user_id: int) -> V2Analysis | None:
    """Return a persisted analysis by id, enforcing ownership."""
    return (
        db.query(V2Analysis)
        .filter(V2Analysis.id == analysis_id, V2Analysis.user_id == user_id)
        .first()
    )


def analysis_to_dict(record: V2Analysis) -> dict[str, object]:
    """Convert a V2Analysis ORM instance to a JSON-serializable dictionary."""
    return {
        "id": record.id,
        "user_id": record.user_id,
        "candidate_name": record.candidate_name,
        "job_description": record.job_description,
        "overall_score": record.overall_score,
        "candidate_profile": json.loads(record.candidate_profile),
        "job_profile": json.loads(record.job_profile),
        "match_analysis": json.loads(record.match_analysis),
        "match_score": json.loads(record.match_score),
        "explanation": json.loads(record.explanation),
        "skill_gaps": json.loads(record.skill_gaps),
        "created_at": record.created_at.isoformat() if record.created_at else "",
    }


__all__ = ["save_analysis", "get_analysis_by_id", "analysis_to_dict"]
