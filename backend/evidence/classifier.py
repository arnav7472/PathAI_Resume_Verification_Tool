"""Evidence quality levels: demonstrated, supported, mentioned, weak, missing."""

from __future__ import annotations

import re
from typing import Literal

from ..verification.knowledge import ACTION_VERBS, BUZZWORDS
from .text import contains_phrase

EvidenceLevel = Literal["demonstrated", "supported", "mentioned", "weak", "missing"]

_IMPLEMENTATION_SECTIONS = frozenset({"experience", "projects", "achievements"})
_CONTEXT_SECTIONS = frozenset({"experience", "projects", "education", "certifications", "achievements"})
_SKILLS_ONLY_SECTION = "skills"


def _has_strong_action(sentence: str) -> bool:
    lower = sentence.lower()
    for verb in ACTION_VERBS:
        if re.search(rf"\b{re.escape(verb)}ing\b|\b{re.escape(verb)}\b", lower):
            return True
    return False


def _has_quant(sentence: str) -> bool:
    return bool(
        re.search(
            r"\b\d+%|\b\d+x\b|\b\d{1,3}(?:,\d{3})+\b|\$\s*\d|\b\d+\s*(?:users|requests|ms|sec|servers|nodes|pods|clusters|teams)\b",
            sentence,
            re.I,
        )
    )


def _is_skills_list_line(sentence: str) -> bool:
    if len(sentence) > 220:
        return True
    lower = sentence.lower()
    if re.search(r"\b(skills?|technologies|tech stack|stack:|proficient in)\b", lower):
        return True
    comma_count = sentence.count(",")
    return comma_count >= 3 and len(sentence) < 400


def _is_vague(sentence: str) -> bool:
    if any(contains_phrase(sentence, w) for w in BUZZWORDS):
        return True
    if _is_skills_list_line(sentence) and not _has_strong_action(sentence):
        return True
    return False


def classify_skill_evidence(
    skill: str,
    aliases: list[str],
    section: str,
    sentence: str,
    *,
    also_in_implementation: bool,
    only_skills_hits: bool,
) -> EvidenceLevel:
    """
    Classify a single sentence hit for a skill given aggregate context flags.
    """
    if section == _SKILLS_ONLY_SECTION and only_skills_hits and not also_in_implementation:
        if _is_vague(sentence):
            return "weak"
        return "mentioned"

    if section in _IMPLEMENTATION_SECTIONS:
        if _has_strong_action(sentence) or _has_quant(sentence):
            return "demonstrated"
        return "supported"

    if section in _CONTEXT_SECTIONS:
        return "supported"

    if section == "certifications":
        return "supported"

    if section == "education":
        if len(sentence) > 80 and re.search(r"\b(project|thesis|developed|implemented|built)\b", sentence, re.I):
            return "supported"
        return "weak"

    if section == "summary":
        return "weak" if _is_vague(sentence) else "supported"

    if _is_vague(sentence) or len(sentence) < 24:
        return "weak"

    return "supported"


def aggregate_skill_level(
    per_snippet_levels: list[EvidenceLevel],
    *,
    has_any_hit: bool,
    required_by_jd: bool,
) -> EvidenceLevel:
    if not has_any_hit:
        return "missing" if required_by_jd else "weak"
    if not per_snippet_levels:
        return "weak"
    priority = ["demonstrated", "supported", "mentioned", "weak", "missing"]
    best: EvidenceLevel = "missing"
    for lvl in per_snippet_levels:
        if priority.index(lvl) < priority.index(best):
            best = lvl
    return best


def indirect_skill_reference(skill: str, sentence: str) -> bool:
    """e.g. SQL implied by PostgreSQL when skill is SQL."""
    if skill != "SQL":
        return False
    return bool(re.search(r"\b(postgres(?:ql)?|mysql|sqlite|relational\s+db)\b", sentence, re.I))

