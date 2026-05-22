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

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from backend.analysis_engine import analyze_resume
    from backend.parser.docx_parser import extract_text_from_docx
    from backend.parser.pdf_parser import extract_text_from_pdf, extract_text_from_pdf_detailed
    from backend.parser.resume_parser import normalize_resume_text
    from backend.parser.extraction_quality import estimate_text_quality
    from backend.scoring.scorer import score_resume_text
except ImportError:
    from analysis_engine import analyze_resume
    from parser.docx_parser import extract_text_from_docx
    from parser.pdf_parser import extract_text_from_pdf, extract_text_from_pdf_detailed
    from parser.resume_parser import normalize_resume_text
    from parser.extraction_quality import estimate_text_quality
    from scoring.scorer import score_resume_text


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
DIST_ASSETS_DIR = DIST_DIR / "assets"
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


app = FastAPI(title="Path-ai Verify API")


def _get_allowed_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "")
    configured = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    return configured or DEFAULT_CORS_ORIGINS


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
PDF_CONTENT_TYPES = {"application/pdf"}
DOCX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
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

    if file_kind == "docx" and not file_bytes.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid DOCX.")


async def read_uploaded_file(upload: UploadFile) -> bytes:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file is too large.")
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
