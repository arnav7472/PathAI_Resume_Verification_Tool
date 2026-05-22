"""Resume text normalisation (the only active function in this file).

parse_resume_text was removed — it was only reachable via dead code in the
/verify endpoint (removed). The canonical extraction pipeline lives in
verification/pipeline.py (via analysis_engine).
"""

from __future__ import annotations

import re


def normalize_resume_text(text: str) -> str:
    """Normalize resume text for deterministic parsing and scoring."""
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").lower()
    normalized = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", "", normalized)
    normalized = re.sub(r"[ \t\f\v]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = "\n".join(line.strip() for line in normalized.split("\n"))
    normalized = re.sub(r"[ ]+\n", "\n", normalized)
    normalized = re.sub(r"\n[ ]+", "\n", normalized)
    return normalized.strip()
