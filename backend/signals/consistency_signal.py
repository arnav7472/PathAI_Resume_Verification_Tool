"""Consistency signals: cross-reference findings, buzzwords, keyword stuffing, skill density."""

from __future__ import annotations

import re
from typing import Any

from ..evidence.text import contains_phrase, split_sentences
from ..verification.knowledge import ACTION_VERBS, BUZZWORDS

# Thresholds for detecting inflation patterns
_STUFFED_SKILL_COUNT = 6  # max distinct skills per sentence before flagging
_DENSITY_WINDOW = 3       # look at 3-sentence windows for density
_STUFFED_WARNING = "appears in a sentence with many other skills; may be keyword-stuffed."


def _is_keyword_stuffed_sentence(sentence: str) -> bool:
    """Detect a sentence that is primarily a dense list of skills."""
    # Count capitalized tech-like tokens (e.g. Python, Docker, AWS, React)
    tokens = re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*|#\w+|\w+\+{2}", sentence)
    return len(tokens) >= _STUFFED_SKILL_COUNT and not any(contains_phrase(sentence, v) for v in ACTION_VERBS)


def _skill_density_warning(sentence: str) -> bool:
    """Flag very densely packed skill mentions (likely tech-stack listing)."""
    tokens = re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", sentence)
    return len(tokens) >= _STUFFED_SKILL_COUNT


def compute_consistency_findings(
    claims: list[dict[str, Any]],
    text: str,
    *,
    cross_reference_sync: bool,
) -> list[dict[str, Any]]:
    """Generate consistency findings per claim and detect buzzword-only sentences.

    Also detects keyword stuffing and unrealistic skill density.

    Returns a list of finding dicts with keys: claim, status, evidence.
    """
    consistency_findings: list[dict[str, Any]] = []

    if not cross_reference_sync:
        return consistency_findings

    for c in claims:
        if c.get("type") != "skill":
            continue
        lvl = c.get("evidence_level")
        sk = str(c.get("skill", ""))
        if lvl in ("demonstrated", "supported", None):
            continue
        if lvl == "mentioned":
            consistency_findings.append(
                {
                    "claim": f"{sk} appears primarily as a keyword or in the skills section without implementation bullets.",
                    "status": lvl,
                    "evidence": [e.get("snippet", "") for e in (c.get("evidence") or [])][:2],
                }
            )
        elif lvl == "weak":
            consistency_findings.append(
                {
                    "claim": f"{sk} is only loosely described; strengthen with outcomes or system context.",
                    "status": lvl,
                    "evidence": [e.get("snippet", "") for e in (c.get("evidence") or [])][:2],
                }
            )
        elif lvl == "missing":
            consistency_findings.append(
                {
                    "claim": f"{sk} is expected from the job description but was not located in parsed resume sections.",
                    "status": lvl,
                    "evidence": [],
                }
            )

    sentences = split_sentences(text)
    for sentence in sentences:
        if any(contains_phrase(sentence, w) for w in BUZZWORDS):
            hit_verb = any(contains_phrase(sentence, v) for v in ACTION_VERBS)
            if not hit_verb:
                consistency_findings.append({"claim": sentence[:120], "status": "buzzword", "evidence": [sentence[:240]]})

    # Keyword stuffing detection: check sentences for dense skill listings
    for sentence in sentences:
        if _is_keyword_stuffed_sentence(sentence):
            consistency_findings.append(
                {
                    "claim": f"Keyword stuffing detected: '{sentence[:100]}'",
                    "status": "buzzword",
                    "evidence": [sentence[:240]],
                }
            )

    # Skill density: look for sentences with many skills listed without action context
    for sentence in sentences:
        if _skill_density_warning(sentence):
            claim_text = f"High skill density: '{sentence[:100]}' (multiple skills without action context)"
            # Avoid duplicate with stuffing check
            if not any(claim_text in f.get("claim", "") for f in consistency_findings):
                consistency_findings.append(
                    {"claim": claim_text, "status": "buzzword", "evidence": [sentence[:240]]}
                )

    return consistency_findings
