"""Weighted confidence scoring with banded variance (no flat 82% repeats)."""

from __future__ import annotations

import hashlib
from typing import Literal

from ..evidence.extractor import EvidenceHit
from ..verification.knowledge import SECTION_WEIGHT, STRICTNESS

EvidenceLevel = Literal["demonstrated", "supported", "mentioned", "weak", "missing"]

_LEVEL_BANDS: dict[EvidenceLevel, tuple[int, int]] = {
    "demonstrated": (85, 98),
    "supported": (70, 84),
    "mentioned": (45, 69),
    "weak": (20, 44),
    "missing": (0, 19),
}


def _jitter(skill: str, claim_key: str, lo: int, hi: int) -> int:
    """Deterministic variance keeps repeated claims from all showing identical scores."""

    raw = hashlib.sha256(f"{skill}|{claim_key}|confidence".encode()).hexdigest()
    n = int(raw[:8], 16)
    span = max(0, hi - lo)
    return lo + (n % (span + 1))


def weighted_base_score(hits: list[EvidenceHit], *, strictness: str) -> float:
    """Convert section quality and match strength into a structural confidence base."""

    if not hits:
        return 0.0
    s = STRICTNESS.get(strictness, STRICTNESS["medium"])
    total = 0.0
    for h in hits:
        w = SECTION_WEIGHT.get(h.section, 3)
        # Bonus for experience/projects sections - they carry more weight
        section_bonus = 1.2 if h.section in ("experience", "projects") else 1.0
        total += w * section_bonus * (0.85 + 0.15 * min(1.0, max(0.0, h.match_score)))
    if not hits:
        return 0.0
    avg = total / max(1, len(hits))
    if strictness == "high":
        avg -= s.get("inflated_penalty", 14) * 0.15
    elif strictness == "low":
        avg += 6
    return max(0.0, min(100.0, avg * 1.15))


def confidence_for_claim(
    skill: str,
    level: EvidenceLevel,
    hits: list[EvidenceHit],
    *,
    strictness: str,
    claim_type: str = "skill",
) -> int:
    """Keep confidence inside the evidence tier band while nudging by source quality."""

    lo, hi = _LEVEL_BANDS[level]
    base = weighted_base_score(hits, strictness=strictness) if hits else 0.0

    key = f"{claim_type}:{skill}"
    if level == "missing":
        return _jitter(skill, key, max(0, lo), hi)

    # Blend structural weight into the band without collapsing to a single number.
    mid = (lo + hi) / 2
    blended = (0.45 * base + 0.55 * mid) / 100.0
    span = hi - lo
    pos_in_span = blended * span
    anchor = lo + int(pos_in_span)
    anchor = max(lo, min(hi, anchor))

    j = _jitter(skill, key, -3, 3)
    final = max(lo, min(hi, anchor + j))
    return int(final)
