"""
FastAPI service for Path-ai Verify.

Architecture: single production pipeline at verification/pipeline.py
              (analysis_engine.py is the public adapter).
              scoring/  → retained active scoring module.
              parser/   → file parsers (docx, pdf).
              parsers/  → section parsers.
              evidence/ → evidence extraction & classification.
              timeline/ → employment timeline analysis.
              verification/ → core pipeline, JD extraction, skills discovery.

              DEAD MODULES ARCHIVED (backend/_archive/):
                scorer/     → duplicate of scoring/, only used in dead code.
                signals/    → duplicate signal logic, only used in dead code.
              Dead code removed from /verify endpoint (legacy signal path after return).

Local development:
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.db.config import get_db, init_db as db_init
from backend.db.service import (
    get_ranking_detail,
    get_ranking_history,
    save_ranking_session,
    delete_ranking_session,
)
from backend.auth.depends import get_current_user, require_role
from backend.auth.routes import router as auth_router
from backend.llm.routes import router as v2_analyze_router
from backend.db.models import User
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import asyncio

from backend.analysis_engine import analyze_resume
from backend.parser.docx_parser import extract_text_from_docx
from backend.parser.pdf_parser import extract_text_from_pdf, extract_text_from_pdf_detailed
from backend.parser.resume_parser import normalize_resume_text
from backend.parser.extraction_quality import estimate_text_quality
from backend.reporting.pdf_report import build_pdf_report
from backend.scoring.scorer import score_resume_text
from backend.db.report_service import save_report, get_user_reports, get_report_by_id, delete_report, report_to_dict
from backend.db.config import SessionLocal as DbSessionLocal


class RankCandidateRequest(BaseModel):
    """Single candidate entry for the /rank endpoint."""
    name: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1, max_length=200_000)
    job_description: str | None = Field(default=None, max_length=100_000)
    strictness: str = Field(default="medium", pattern="^(low|medium|high)$")
    cross_reference_sync: bool = True


class RankRequest(BaseModel):
    """Request body for ranking multiple candidates against a JD."""
    job_description: str = Field(..., min_length=1, max_length=100_000)
    candidates: list[RankCandidateRequest] = Field(..., min_length=1, max_length=100)
    strictness: str = Field(default="medium", pattern="^(low|medium|high)$")
    cross_reference_sync: bool = True


class RankedCandidateResult(BaseModel):
    """Single ranked candidate output entry."""
    candidate_name: str
    rank_score: float
    compatibility: float
    confidence: float
    risk: float


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


class _SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach default security headers on every response."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self' data:;"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class _HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """Reject non-HTTPS requests in production when behind a TLS-terminating reverse proxy."""
    async def dispatch(self, request: Request, call_next):
        if os.getenv("ENVIRONMENT", "").lower() == "production":
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
            if forwarded_proto.lower() != "https":
                raise HTTPException(
                    status_code=400,
                    detail="HTTPS required. Ensure a TLS-terminating reverse proxy is configured.",
                )
        return await call_next(request)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
DIST_ASSETS_DIR = DIST_DIR / "assets"
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
]


app = FastAPI(title="Path-ai Verify API")
app.include_router(auth_router)
app.include_router(v2_analyze_router)


@app.on_event("startup")
async def on_startup():
    """Initialize database tables on application startup."""
    try:
        db_init()
        logger.info("Database tables created successfully.")
    except Exception as exc:
        logger.warning("Database initialization skipped: %s", exc)


def _get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "")
    configured = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return configured or DEFAULT_CORS_ORIGINS


app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,[IP_ADDRESS],testserver,pathai-resume-verification-tool.onrender.com,pathai-verify-v2.onrender.com").split(",") if h.strip()],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(_HTTPSEnforcementMiddleware)
app.add_middleware(_SecurityHeadersMiddleware)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
PDF_CONTENT_TYPES = {"application/pdf"}
DOCX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
GENERIC_BINARY_CONTENT_TYPES = {"application/octet-stream", ""}


class ResumeTextRequest(BaseModel):
    """Text-only scoring boundary used by /score-resume, not the main UI flow."""

    text: str = Field(..., min_length=1)
    job_description: str | None = Field(default=None, max_length=100_000)
    strictness: str = Field(default="medium", pattern="^(low|medium|high)$")
    cross_reference_sync: bool = True


class VerifyRequest(BaseModel):
    """Primary verification API contract consumed by the React dashboard."""

    text: str = Field(..., min_length=1, max_length=200_000)
    job_description: str | None = Field(default=None, max_length=100_000)
    strictness: str = Field(default="medium", pattern="^(low|medium|high)$")
    cross_reference_sync: bool = True
    github: str | None = Field(default=None, max_length=500)
    linkedin: str | None = Field(default=None, max_length=500)


def clean_text(text: str) -> str:
    return normalize_resume_text(text)


def detect_file_kind(filename: str, content_type: str | None) -> str:
    suffix = Path(filename).suffix.lower()
    normalized_content_type = (content_type or "").lower()

    if suffix == ".pdf" and normalized_content_type in (PDF_CONTENT_TYPES | GENERIC_BINARY_CONTENT_TYPES):
        return "pdf"

    if suffix == ".docx" and normalized_content_type in DOCX_CONTENT_TYPES:
        return "docx"

    raise HTTPException(
        status_code=400,
        detail="Unsupported file type. Only PDF and DOCX files are allowed.",
    )


def validate_file_signature(file_kind: str, file_bytes: bytes) -> None:
    if file_kind == "pdf":
        if not file_bytes.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")
        return

    if file_kind == "docx":
        import zipfile
        from io import BytesIO
        try:
            with zipfile.ZipFile(BytesIO(file_bytes)) as zf:
                names = set(zf.namelist())
                if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                    raise HTTPException(status_code=400, detail="Uploaded file is not a valid DOCX.")
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid DOCX.")


async def read_uploaded_file(upload: UploadFile) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(1_048_576)  # 1 MB chunk
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Uploaded file is too large.")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return data


def ensure_extracted_text(cleaned_text: str) -> None:
    if not cleaned_text:
        raise HTTPException(
            status_code=422,
            detail="No extractable text found in the uploaded file.",
        )


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


# ── Protected endpoints (auth MVP) ────────────────────────────────────────────


@app.get("/api/protected/manager-only")
async def manager_only(current_user: User = Depends(require_role("manager"))):
    """Example endpoint accessible only by users with role=manager."""
    return {
        "message": "This endpoint is restricted to managers.",
        "user": current_user.username,
        "role": current_user.role,
    }


@app.get("/api/protected/me")
async def protected_me(current_user: User = Depends(get_current_user)):
    """Example endpoint accessible by any authenticated user (any role)."""
    return {
        "message": "You are authenticated.",
        "user": current_user.username,
        "role": current_user.role,
    }


@app.get("/api/protected/candidate-only")
async def candidate_only(current_user: User = Depends(require_role("candidate"))):
    """Example endpoint accessible only by users with role=candidate."""
    return {
        "message": "This endpoint is restricted to candidates.",
        "user": current_user.username,
        "role": current_user.role,
    }


@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)) -> JSONResponse:
    """Upload boundary: validate file identity before dispatching to parsers."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    file_kind = detect_file_kind(file.filename, file.content_type)
    file_bytes = await read_uploaded_file(file)
    validate_file_signature(file_kind, file_bytes)

    extraction_warnings: list[str] = []

    try:
        if file_kind == "pdf":
            extracted_text, pdf_meta = extract_text_from_pdf_detailed(file_bytes)
            extraction_warnings.extend(pdf_meta.get("warnings", []))
            
            # Quality assessment for text-only input (no file) is done downstream
            quality = pdf_meta.get("quality", {})
            if quality and quality.get("is_low_quality"):
                extraction_warnings.append(
                    f"Low-quality scan may reduce verification accuracy."
                )
        else:
            extracted_text = extract_text_from_docx(file_bytes)
            # DOCX is typically reliable, but check for empty edge case
            if estimate_text_quality is not None:
                quality = estimate_text_quality(extracted_text)
                if quality.get("is_low_quality"):
                    extraction_warnings.append(quality["detail"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to parse uploaded file: %s", file.filename)
        raise HTTPException(status_code=500, detail=str(exc) or "Failed to parse uploaded file.") from exc
    finally:
        await file.close()

    cleaned_text = clean_text(extracted_text)
    ensure_extracted_text(cleaned_text)
    logger.info("Processed %s file: %s", file_kind, file.filename)
    return JSONResponse(content={"text": cleaned_text, "warnings": extraction_warnings})


@app.post("/score-resume")
async def score_resume(payload: ResumeTextRequest) -> JSONResponse:
    """Legacy-compatible text score endpoint; frontend currently uses /verify."""

    cleaned_text = clean_text(payload.text)
    if not cleaned_text:
        raise HTTPException(status_code=400, detail="Resume text must not be empty.")

    result = score_resume_text(cleaned_text)
    analysis = analyze_resume(
        cleaned_text,
        payload.job_description or "",
        payload.strictness,
        payload.cross_reference_sync,
    )
    result.update(
        {
            "compatibility_score": analysis["compatibility_score"],
            "missing_skills": analysis["missing_skills"],
            "matched_skills": analysis["matched_skills"],
            "action_verbs": analysis["action_verbs"],
        }
    )
    logger.info("Scored resume text with confidence %.2f", result["confidence"])
    return JSONResponse(content=result)


@app.post("/verify")
async def verify_resume(payload: VerifyRequest) -> JSONResponse:
    """Main report endpoint: normalize text, run deterministic analysis, shape UI payload."""

    cleaned_text = clean_text(payload.text)
    if not cleaned_text:
        raise HTTPException(status_code=400, detail="Resume text must not be empty.")

    analysis = analyze_resume(
        cleaned_text,
        payload.job_description or "",
        payload.strictness,
        payload.cross_reference_sync,
    )
    verdict = (
        "high_risk"
        if analysis["risk_score"] >= 70
        else "needs_review"
        if analysis["risk_score"] >= 35
        else "likely_consistent"
    )
    logger.info(
        "Verified resume with JD: compatibility=%s confidence=%s risk=%s strictness=%s cross_reference=%s",
        analysis["compatibility_score"],
        analysis["confidence"],
        analysis["risk_score"],
        analysis["strictness"],
        analysis["cross_reference_sync"],
    )
    return JSONResponse(
        content={
            "risk_score": analysis["risk_score"],
            "confidence": analysis["confidence"],
            "compatibility_score": analysis["compatibility_score"],
            "verdict": verdict,
            "findings": analysis["findings"],
            "claims": analysis["claims"],
            "evidence": analysis["evidence"],
            "timeline": analysis["timeline"],
            "timeline_analysis": analysis.get("timeline_analysis", {}),
            "skill_timeline_insights": analysis.get("skill_timeline_insights", []),
            "resume_sections": analysis.get("resume_sections", {}),
            "skills": analysis["skills"],
            "action_verbs": analysis["action_verbs"],
            "matched_skills": analysis["matched_skills"],
            "missing_skills": analysis["missing_skills"],
            "weak_areas": analysis["weak_areas"],
            "job_requirements": analysis["job_requirements"],
            "consistency_findings": analysis["consistency_findings"],
            "strictness": analysis["strictness"],
            "cross_reference_sync": analysis["cross_reference_sync"],
        }
    )


class PdfReportRequest(BaseModel):
    """Request body for PDF report generation — reuses same analysis."""
    text: str = Field(..., min_length=1, max_length=200_000)
    job_description: str | None = Field(default=None, max_length=100_000)
    strictness: str = Field(default="medium", pattern="^(low|medium|high)$")
    cross_reference_sync: bool = True


@app.post("/report/pdf")
async def generate_pdf_report(payload: PdfReportRequest):
    """Generate a downloadable verification PDF.

    Reuses the same deterministic pipeline as /verify but returns
    a recruiter-readable PDF document instead of JSON.
    """
    cleaned_text = clean_text(payload.text)
    if not cleaned_text:
        raise HTTPException(status_code=400, detail="Resume text must not be empty.")

    analysis = analyze_resume(
        cleaned_text,
        payload.job_description or "",
        payload.strictness,
        payload.cross_reference_sync,
    )

    # Pass extraction warnings from pipeline
    pdf_bytes = build_pdf_report(analysis)

    from fastapi.responses import Response
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=verification_report.pdf",
            "Content-Length": str(len(pdf_bytes)),
        },
    )


def _derive_name_from_filename(filename: str) -> str:
    """Extract candidate name from filename by removing extension and replacing separators."""
    stem = Path(filename).stem
    # Replace common separators with spaces, then clean up
    name = stem.replace("_", " ").replace("-", " ").replace(".", " ")
    # Title-case and collapse whitespace
    parts = name.split()
    if not parts:
        return filename
    return " ".join(p.capitalize() for p in parts)


def _extract_text_from_bytes(file_kind: str, file_bytes: bytes) -> str:
    """Extract text from raw file bytes using the appropriate parser."""
    if file_kind == "pdf":
        extracted_text, _ = extract_text_from_pdf_detailed(file_bytes)
    else:
        extracted_text = extract_text_from_docx(file_bytes)
    return clean_text(extracted_text)


@app.post("/rank-files")
async def rank_from_files(
    job_description: str = Form(..., min_length=1, max_length=100_000),
    files: list[UploadFile] = File(..., min_length=2, max_length=100),
    strictness: str = Form(default="medium"),
    cross_reference_sync: bool = Form(default=True),
    current_user: User = Depends(require_role("manager")),
) -> JSONResponse:
    """Upload multiple resume files + JD, extract text, rank candidates.
    
    Reuses the same deterministic pipeline as /rank and /verify.
    Candidate names are derived from filenames when possible.
    """
    # Validate strictness server-side
    if strictness not in ("low", "medium", "high"):
        raise HTTPException(status_code=422, detail="strictness must be one of: low, medium, high")

    logger.info(
        "Rank-from-files: %d files submitted, strictness=%s",
        len(files),
        strictness,
    )

    # Process each file: detect type, extract text, derive name
    candidates_data: list[tuple[str, str]] = []  # (name, text)

    for upload in files:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="Each uploaded file must have a filename.")

        file_kind = detect_file_kind(upload.filename, upload.content_type)
        file_bytes = await read_uploaded_file(upload)
        validate_file_signature(file_kind, file_bytes)

        try:
            extracted_text = _extract_text_from_bytes(file_kind, file_bytes)
        except Exception as exc:
            logger.exception("Failed to parse file: %s", upload.filename)
            raise HTTPException(
                status_code=422,
                detail=f"Failed to extract text from '{upload.filename}': {exc}",
            ) from exc
        finally:
            await upload.close()

        ensure_extracted_text(extracted_text)

        name = _derive_name_from_filename(upload.filename)
        candidates_data.append((name, extracted_text))
        logger.info("Extracted text from %s (derived name: %s)", upload.filename, name)

    # Build the same RankRequest payload and reuse the ranking logic
    rank_payload = RankRequest(
        job_description=job_description,
        candidates=[
            RankCandidateRequest(name=name, text=text)
            for name, text in candidates_data
        ],
        strictness=strictness,
        cross_reference_sync=cross_reference_sync,
    )

    results = await _execute_rank(rank_payload)

    # Persist to database (best-effort)
    rank_files_id = None
    try:
        from backend.db.config import SessionLocal
        db_local = SessionLocal()
        try:
            ranking = save_ranking_session(
                db_local,
                job_description=job_description,
                strictness=strictness,
                cross_reference_sync=cross_reference_sync,
                results=results,
                user_id=current_user.id,
            )
            rank_files_id = ranking.id
            logger.info("Ranking session saved to database (id=%d).", rank_files_id)
        finally:
            db_local.close()
    except Exception as exc:
        logger.warning("Failed to save ranking session: %s", exc)

    cleaned = _strip_internal_fields(results)
    logger.info("Rank-from-files complete — %d candidates ranked", len(cleaned))
    return JSONResponse(content={
        "ranking_id": rank_files_id,
        "candidates": cleaned,
    })


async def _execute_rank(payload: RankRequest) -> list[dict[str, object]]:
    """Shared ranking logic used by /rank and /rank-files."""
    async def evaluate(candidate: RankCandidateRequest) -> dict[str, object]:
        text = clean_text(candidate.text)
        if not text:
            raise HTTPException(
                status_code=400,
                detail=f"Candidate '{candidate.name}' provided empty resume text.",
            )

        jd = candidate.job_description or payload.job_description
        analysis = analyze_resume(
            text,
            jd,
            candidate.strictness or payload.strictness,
            candidate.cross_reference_sync if candidate.cross_reference_sync is not None else payload.cross_reference_sync,
        )

        compatibility = float(analysis["compatibility_score"])
        confidence = float(analysis["confidence"])
        risk = float(analysis["risk_score"])

        rank_score = round(
            max(
                 0,
                min(
                    100,
                    compatibility * 0.7
                    + confidence * 0.2
                    - risk * 0.1,
                ),
            ),
            2,
        )

        return {
            "candidate_name": candidate.name,
            "rank_score": rank_score,
            "compatibility": compatibility,
            "confidence": confidence,
            "risk": risk,
            "_resume_text": text,  # internal field for persistence, stripped from response
            "_analysis_data": analysis,  # full pipeline output for candidate detail view
        }

    results = await asyncio.gather(*[evaluate(c) for c in payload.candidates])
    results.sort(key=lambda r: r["rank_score"], reverse=True)
    return results


def _strip_internal_fields(results: list[dict]) -> list[dict]:
    """Remove internal-use-only fields before returning to the client."""
    return [
        {k: v for k, v in r.items() if not k.startswith("_")}
        for r in results
    ]


@app.post("/rank")
async def rank_candidates(
    payload: RankRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> dict:
    """Rank multiple candidates against a shared job description.

    Each candidate is run through the same deterministic pipeline as /verify.
    A composite rank_score is computed from the pipeline outputs.

    Formula:
      rank_score = compatibility_score * 0.7 + confidence * 0.2 - risk_score * 0.1

    Returns an object with ranking_id (if persisted) and candidates array.
    """
    logger.info(
        "Ranking %d candidates for JD (strictness=%s, cross_reference=%s)",
        len(payload.candidates),
        payload.strictness,
        payload.cross_reference_sync,
    )

    results = await _execute_rank(payload)
    ranking_id = None

    # Persist to database (best-effort, non-blocking)
    try:
        ranking = save_ranking_session(
            db,
            job_description=payload.job_description,
            strictness=payload.strictness,
            cross_reference_sync=payload.cross_reference_sync,
            results=results,
            user_id=current_user.id,
        )
        ranking_id = ranking.id
        logger.info("Ranking session saved to database (id=%d).", ranking_id)
    except Exception as exc:
        logger.warning("Failed to save ranking session: %s", exc)

    cleaned = _strip_internal_fields(results)
    logger.info("Ranking complete — %d candidates evaluated", len(results))
    return {
        "ranking_id": ranking_id,
        "candidates": cleaned,
    }


@app.get("/rankings")
async def list_rankings(
    db: Session = Depends(get_db),
    limit: int = 50,
    current_user: User = Depends(require_role("manager")),
) -> list[dict]:
    """Return the most recent ranking sessions (summary)."""
    return get_ranking_history(db, limit=limit, user_id=current_user.id)


@app.get("/rankings/{ranking_id}")
async def get_ranking(
    ranking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> dict:
    """Return a single ranking session with full candidate results."""
    detail = get_ranking_detail(db, ranking_id, user_id=current_user.id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Ranking session not found.")
    return detail


@app.get("/rankings/{ranking_id}/candidates/{ranking_candidate_id}")
async def get_ranking_candidate_detail(
    ranking_id: int,
    ranking_candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> dict:
    """Return full analysis details for a specific candidate in a ranking session."""
    from backend.db.models import RankingCandidate as RankingCandidateModel

    detail = get_ranking_detail(db, ranking_id, user_id=current_user.id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Ranking session not found.")

    # Find the specific candidate in the ranking
    target = None
    for c in detail.get("candidates", []):
        if c.get("ranking_candidate_id") == ranking_candidate_id:
            target = c
            break

    if target is None:
        raise HTTPException(status_code=404, detail="Candidate not found in this ranking session.")

    return {
        "ranking_id": ranking_id,
        "candidate_name": target["candidate_name"],
        "rank_score": target["rank_score"],
        "compatibility": target["compatibility"],
        "confidence": target["confidence"],
        "risk": target["risk"],
        "job_description": detail.get("job_description", ""),
        "strictness": detail.get("strictness", "medium"),
        "cross_reference_sync": detail.get("cross_reference_sync", True),
        "resume_text": target.get("resume_text", ""),
        "analysis_data": target.get("analysis_data"),
    }


@app.delete("/rankings/{ranking_id}")
async def delete_ranking(
    ranking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> dict:
    """Delete a ranking session owned by the current user.

    Verifies ownership before deletion. Returns 403 if the ranking
    belongs to another user, 404 if it doesn't exist.
    """
    deleted = delete_ranking_session(db, ranking_id, user_id=current_user.id)
    if not deleted:
        # Check if the ranking exists at all to distinguish 403 vs 404
        from backend.db.models import Ranking
        exists = db.query(Ranking).filter(Ranking.id == ranking_id).first() is not None
        if exists:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to delete this ranking session.",
            )
        raise HTTPException(status_code=404, detail="Ranking session not found.")
    logger.info("Deleted ranking id=%d (user_id=%d)", ranking_id, current_user.id)
    return {"detail": "Ranking session deleted successfully."}


# ── Reports endpoints (manager-only) ──────────────────────────────────────────


class SaveReportRequest(BaseModel):
    """Request body for persisting a verification report."""
    candidate_name: str = Field(..., min_length=1, max_length=500)
    job_description: str = Field(default="", max_length=100_000)
    risk_score: int = Field(..., ge=0, le=100)
    confidence: int = Field(..., ge=0, le=100)
    compatibility_score: int = Field(..., ge=0, le=100)
    verdict: str = Field(..., pattern="^(likely_consistent|needs_review|high_risk|unknown)$")
    strictness: str = Field(default="medium", pattern="^(low|medium|high)$")
    cross_reference_sync: bool = True
    analysis_data: dict | None = None


@app.post("/reports")
async def create_report(
    payload: SaveReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> dict:
    """Persist a verification report owned by the current user."""
    report = save_report(
        db=db,
        user_id=current_user.id,
        candidate_name=payload.candidate_name,
        job_description=payload.job_description,
        risk_score=payload.risk_score,
        confidence=payload.confidence,
        compatibility_score=payload.compatibility_score,
        verdict=payload.verdict,
        strictness=payload.strictness,
        cross_reference_sync=payload.cross_reference_sync,
        analysis_data=payload.analysis_data,
    )
    logger.info("Saved report id=%d for user_id=%d", report.id, current_user.id)
    return report_to_dict(report)


@app.get("/reports")
async def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> list[dict]:
    """Return all reports owned by the current user."""
    reports = get_user_reports(db, user_id=current_user.id)
    return [report_to_dict(r) for r in reports]


@app.delete("/reports/{report_id}")
async def delete_report_endpoint(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> dict:
    """Delete a report owned by the current user.

    Verifies ownership before deletion. Returns 403 if the report
    belongs to another user, 404 if it doesn't exist.
    """
    report = get_report_by_id(db, report_id, current_user.id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete this report.",
        )
    delete_report(db, report_id, current_user.id)
    logger.info("Deleted report id=%d (user_id=%d)", report_id, current_user.id)
    return {"detail": "Report deleted successfully."}


if DIST_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_ASSETS_DIR), name="assets")


if DIST_DIR.exists():

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(DIST_DIR / "index.html")


    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        requested_path = DIST_DIR / full_path
        if requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(DIST_DIR / "index.html")
