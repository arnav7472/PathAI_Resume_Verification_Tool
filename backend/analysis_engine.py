"""Public API adapter over verification/pipeline.py.

This module re-exports pipeline functions and convenience helpers
used by main.py endpoints. The single source of truth for resume
analysis is verification/pipeline:analyze_resume.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import OrderedDict

from .evidence.text import contains_phrase, split_sentences
from .parsers.section_parser import all_indexed_sentences, parse_resume_sections
from .timeline.analysis import extract_timeline_entries as extract_timeline
from .verification.jd_extract import extract_job_requirements
from .verification.knowledge import ACTION_VERBS, BUZZWORDS, DOMAIN_TERMS, SKILL_ALIASES, STRICTNESS
from .verification.normalize import normalize_resume_text as normalize_text
from .verification.pipeline import analyze_resume as run_resume_analysis
from .verification.years import extract_years_experience as extract_years

__all__ = [
    "ACTION_VERBS",
    "BUZZWORDS",
    "DOMAIN_TERMS",
    "SKILL_ALIASES",
    "STRICTNESS",
    "SkillHit",
    "analyze_resume",
    "extract_action_verbs",
    "extract_job_requirements",
    "extract_skills",
    "extract_timeline",
    "extract_years",
    "normalize_text",
]


@dataclass
class SkillHit:
    skill: str
    count: int
    evidence: list[str]


def extract_action_verbs(text: str) -> list[str]:
    found: OrderedDict[str, None] = OrderedDict()
    for verb in ACTION_VERBS:
        if contains_phrase(text, verb):
            found[verb] = None
    return list(found.keys())


def extract_skills(text: str) -> dict[str, SkillHit]:
    sections = parse_resume_sections(normalize_text(text))
    indexed = all_indexed_sentences(sections)
    hits_map: dict[str, SkillHit] = {}
    for skill, aliases in SKILL_ALIASES.items():
        evidence: list[str] = []
        count = 0
        for _, sentence in indexed:
            if not any(contains_phrase(sentence, alias) for alias in aliases):
                continue
            count += 1
            if len(evidence) < 4:
                s = sentence.strip()
                if len(s) > 260:
                    s = s[:257].rstrip() + "…"
                evidence.append(s)
        if count:
            hits_map[skill] = SkillHit(skill=skill, count=count, evidence=evidence)
    return hits_map


def analyze_resume(
    resume_text: str,
    job_description: str = "",
    strictness: str = "medium",
    cross_reference_sync: bool = True,
) -> dict[str, object]:
    return run_resume_analysis(resume_text, job_description, strictness, cross_reference_sync)
