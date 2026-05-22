"""Extraction-quality heuristics for weak-OCR and sparse-text detection.

Deterministic rules only — no ML, no LLMs.
"""

from __future__ import annotations

_MIN_CHARS_FOR_REASONABLE_EXTRACTION = 100
_MIN_WORDS_FOR_REASONABLE_EXTRACTION = 20
_MAX_GARBAGE_RATIO = 0.30  # >30% non-alpha chars suggests OCR noise


def estimate_text_quality(text: str) -> dict:
    """Score extraction quality on a 0-100 scale and return human labels."""
    if not text or not text.strip():
        return {
            "quality_score": 0,
            "quality_label": "no_text",
            "detail": "No text was extracted from the file.",
            "is_low_quality": True,
        }

    stripped = text.strip()
    char_count = len(stripped)
    word_count = len(stripped.split())
    alpha_chars = sum(1 for ch in stripped if ch.isalpha())
    garbage_ratio = 1.0 - (alpha_chars / max(char_count, 1))
    avg_word_len = alpha_chars / max(word_count, 1)

    reasons: list[str] = []
    is_low = False

    if char_count < _MIN_CHARS_FOR_REASONABLE_EXTRACTION:
        reasons.append("Very short extracted text — possible OCR failure.")
        is_low = True

    if word_count < _MIN_WORDS_FOR_REASONABLE_EXTRACTION:
        reasons.append("Very few words detected — resume content may be missing.")
        is_low = True

    if garbage_ratio > _MAX_GARBAGE_RATIO:
        reasons.append(
            f"High non-alphabetic content ({garbage_ratio:.0%}) — "
            "scan quality may reduce verification accuracy."
        )
        is_low = True

    if avg_word_len < 2.5:
        reasons.append("Unusually short words — possible OCR corruption.")
        is_low = True

    # 0-100 quality score
    score = 100
    score -= max(0, int((garbage_ratio / _MAX_GARBAGE_RATIO) * 40))
    if char_count < 500:
        score -= 25
    if word_count < 100:
        score -= 15
    score = max(0, min(100, score))

    if score >= 80:
        label = "good"
    elif score >= 50:
        label = "fair"
    elif score >= 20:
        label = "poor"
    else:
        label = "unusable"

    return {
        "quality_score": score,
        "quality_label": label,
        "char_count": char_count,
        "word_count": word_count,
        "garbage_ratio": round(garbage_ratio, 3),
        "is_low_quality": is_low,
        "detail": " ".join(reasons) if reasons else "Extracted text appears usable.",
    }