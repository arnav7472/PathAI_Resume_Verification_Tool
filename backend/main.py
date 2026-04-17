"""
FastAPI service for Path-ai Verify.

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
    from backend.parser.docx_parser import extract_text_from_docx
    from backend.parser.pdf_parser import extract_text_from_pdf
    from backend.parser.resume_parser import normalize_resume_text, parse_resume_text
    from backend.scorer.scoring import score_verification
    from backend.scoring.scorer import score_resume_text
    from backend.signals.consistency_signal import compute_consistency_signal
    from backend.signals.depth_signal import compute_depth_signal
    from backend.signals.skill_signal import compute_skill_signal
except ImportError:
    from parser.docx_parser import extract_text_from_docx
    from parser.pdf_parser import extract_text_from_pdf
    from parser.resume_parser import normalize_resume_text, parse_resume_text
    from scorer.scoring import score_verification
    from scoring.scorer import score_resume_text
    from signals.consistency_signal import compute_consistency_signal
    from signals.depth_signal import compute_depth_signal
    from signals.skill_signal import compute_skill_signal


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
    "http://127.0.0.1:3000",\n    "http://localhost:5173",\n    "http://127.0.0.1:5173",\n    "https://*.vercel.app",\n]

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
    text: str = Field(..., min_length=1)


class VerifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200_000)
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


def _build_claims(parsed_resume: dict) -> list[dict[str, object]]:
    claims: list[dict[str, object]] = []

    for skill, count in parsed_resume["skill_counts"].items():
        claims.append(
            {
                "type": "skill",
                "value": " ".join(part.capitalize() for part in skill.split()),
                "evidence_count": count,
            }
        )

    if parsed_resume["years_experience"] is not None:
        claims.append({"type": "experience", "value": f'{parsed_resume["years_experience"]} years'})

    if parsed_resume["has_senior_title"]:
        claims.append({"type": "title", "value": "Senior-level title detected"})

    return claims


def _build_verify_response(parsed_resume: dict, verification_result: dict) -> dict:
    confidence = int(verification_result["confidence"])
    risk_score = max(0, min(100, 100 - confidence))
    findings = [
        {"message": flag, "severity": verification_result["risk"].lower()}
        for flag in verification_result["flags"]
    ]

    if not findings:
        findings.append(
            {
                "message": "No major heuristic contradictions detected.",
                "severity": "low",
            }
        )

    if risk_score >= 60:
        verdict = "high_risk"
    elif risk_score >= 30:
        verdict = "needs_review"
    else:
        verdict = "likely_consistent"

    return {
        "risk_score": risk_score,
        "confidence": confidence,
        "verdict": verdict,
        "findings": findings,
        "claims": _build_claims(parsed_resume),
        "timeline": parsed_resume["timeline"],
    }


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    file_kind = detect_file_kind(file.filename, file.content_type)
    file_bytes = await read_uploaded_file(file)
    validate_file_signature(file_kind, file_bytes)

    try:
        if file_kind == "pdf":
            extracted_text = extract_text_from_pdf(file_bytes)
        else:
            extracted_text = extract_text_from_docx(file_bytes)
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
    return JSONResponse(content={"text": cleaned_text})


@app.post("/score-resume")
async def score_resume(payload: ResumeTextRequest) -> JSONResponse:
    cleaned_text = clean_text(payload.text)
    if not cleaned_text:
        raise HTTPException(status_code=400, detail="Resume text must not be empty.")

    result = score_resume_text(cleaned_text)
    logger.info("Scored resume text with confidence %.2f", result["confidence"])
    return JSONResponse(content=result)


@app.post("/verify")
async def verify_resume(payload: VerifyRequest) -> JSONResponse:
    cleaned_text = clean_text(payload.text)
    if not cleaned_text:
        raise HTTPException(status_code=400, detail="Resume text must not be empty.")

    parsed_resume = parse_resume_text(cleaned_text)
    skill_signal = compute_skill_signal(parsed_resume["skill_counts"])
    depth_signal = compute_depth_signal(parsed_resume["text"], parsed_resume["skill_counts"])
    consistency_signal = compute_consistency_signal(
        skills_count=sum(parsed_resume["skill_counts"].values()),
        years_experience=parsed_resume["years_experience"],
        has_senior_title=parsed_resume["has_senior_title"],
        depth_score=depth_signal["score"],
    )

    result = score_verification(
        skills=parsed_resume["skills"],
        skill_signal=skill_signal,
        depth_signal=depth_signal,
        consistency_signal=consistency_signal,
    )

    logger.info(
        "Verified resume: confidence=%s risk=%s github=%s linkedin=%s",
        result["confidence"],
        result["risk"],
        bool(payload.github and payload.github.strip()),
        bool(payload.linkedin and payload.linkedin.strip()),
    )
    return JSONResponse(content=_build_verify_response(parsed_resume, result))


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
