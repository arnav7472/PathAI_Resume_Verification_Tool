"""Sentence-level evidence extraction with section labels."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from ..parsers.section_parser import SectionKey, all_indexed_sentences
from ..verification.knowledge import SKILL_ALIASES
from .classifier import aggregate_skill_level, classify_skill_evidence, indirect_skill_reference
from .text import contains_phrase, snippet_signature, truncate_snippet

EvidenceLevel = Literal["demonstrated", "supported", "mentioned", "weak", "missing"]


@dataclass
class EvidenceHit:
    section: str
    snippet: str
    raw_sentence: str
    match_score: float


def _alias_match_score(sentence: str, aliases: list[str]) -> float:
    best = 0.0
    for alias in aliases:
        if contains_phrase(sentence, alias):
            best = max(best, min(1.0, len(alias) / 22.0 + 0.42))
    return best


def _section_priority(section: SectionKey) -> float:
    order = {
        "experience": 1.0,
        "projects": 0.92,
        "achievements": 0.88,
        "certifications": 0.72,
        "education": 0.65,
        "skills": 0.45,
        "summary": 0.42,
        "other": 0.35,
    }
    return order.get(section, 0.3)


def _is_noise_sentence(sentence: str, aliases: list[str]) -> bool:
    if len(sentence) > 520:
        return True
    if re.match(r"^[\d\-–—\s|/·•,]+$", sentence.strip()):
        return True
    lower = sentence.lower()
    if sum(lower.count(a.lower()) for a in aliases if len(a) > 2) > 6:
        return True
    return False


def _match_sentence(sentence: str, skill: str, aliases: list[str]) -> bool:
    if any(contains_phrase(sentence, a) for a in aliases):
        return True
    if skill == "SQL" and indirect_skill_reference(skill, sentence):
        return True
    return False


def extract_skill_evidence(
    skill: str,
    sections: dict[str, Any],
    *,
    required_by_jd: bool,
    global_used_snippets: set[str],
) -> tuple[list[EvidenceHit], EvidenceLevel]:
    """Select the best sentence snippets for one skill and summarize evidence strength."""

    aliases = SKILL_ALIASES.get(skill, [skill.lower()])
    indexed = all_indexed_sentences(sections)

    all_matches: list[tuple[SectionKey, str]] = []
    for section, sentence in indexed:
        if _match_sentence(sentence, skill, aliases):
            all_matches.append((section, sentence))

    impl_hit = any(s in ("experience", "projects", "achievements") for s, _ in all_matches)
    only_skills_hits = bool(all_matches) and all(s == "skills" for s, _ in all_matches)

    candidates: list[tuple[float, SectionKey, str]] = []
    for section, sentence in all_matches:
        # Implementation sections outrank skills lists because they show use, not just mention.
        base = _alias_match_score(sentence, aliases) + _section_priority(section) * 0.55
        if _is_noise_sentence(sentence, aliases):
            base -= 0.28
        candidates.append((base, section, sentence))

    candidates.sort(key=lambda x: -x[0])

    def build_hits(use_global_skip: bool) -> tuple[list[EvidenceHit], list[EvidenceLevel]]:
        local_levels: list[EvidenceLevel] = []
        hits_out: list[EvidenceHit] = []
        seen_sig: set[str] = set()

        for score, section, sentence in candidates[:12]:
            snip = truncate_snippet(sentence)
            sig = snippet_signature(snip)
            # Prefer unique snippets across claims, but allow reuse if this skill has no evidence.
            if use_global_skip and sig in global_used_snippets and len(hits_out) > 0:
                continue
            if sig in seen_sig:
                continue
            seen_sig.add(sig)

            lvl = classify_skill_evidence(
                skill,
                aliases,
                section,
                sentence,
                also_in_implementation=impl_hit,
                only_skills_hits=only_skills_hits,
            )
            local_levels.append(lvl)
            hits_out.append(
                EvidenceHit(
                    section=section,
                    snippet=snip,
                    raw_sentence=sentence,
                    match_score=score,
                )
            )
            if use_global_skip:
                global_used_snippets.add(sig)
            if len(hits_out) >= 3:
                break

        return hits_out, local_levels

    snp = ""  # placeholder for typo fix below
    del snp

    hits, levels = build_hits(True)
    if not hits and candidates:
        hits, levels = build_hits(False)

    aggregate = aggregate_skill_level(
        levels,
        has_any_hit=len(all_matches) > 0,
        required_by_jd=required_by_jd,
    )

    if not all_matches and required_by_jd:
        aggregate = "missing"
    elif not all_matches:
        aggregate = "weak"

    return hits, aggregate
