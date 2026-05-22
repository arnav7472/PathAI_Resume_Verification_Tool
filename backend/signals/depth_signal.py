"""Depth signals: action verbs, compatibility score, timeline, and section summary."""

from __future__ import annotations

from typing import Any

from ..evidence.text import split_sentences
from ..timeline.analysis import analyze_employment_spans, extract_timeline_entries, skill_timeline_insights
from ..verification.knowledge import ACTION_VERBS


def detect_action_verbs(text: str) -> list[str]:
    """Return action verbs found in the resume text, preserving original order."""
    from ..evidence.text import contains_phrase

    verbs: list[str] = []
    for verb in ACTION_VERBS:
        if any(contains_phrase(sentence, verb) for sentence in split_sentences(text)):
            verbs.append(verb)
    return verbs


def compute_compatibility(
    resume_skills: dict[str, int],
    required_skills: set[str],
    matched_skills: list[str],
) -> int:
    """Compute compatibility score favoring JD coverage but rewarding broad skill evidence."""
    resume_skill_count = max(1, len(resume_skills))
    match_ratio = len(matched_skills) / max(1, len(required_skills)) if required_skills else min(1.0, len(resume_skills) / 8)
    coverage_bonus = min(18, resume_skill_count * 2)
    return round(max(0, min(100, (match_ratio * 76) + coverage_bonus)))


def compute_timeline_signals(
    text: str,
    sections: dict[str, Any],
    resume_skills: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Extract timeline entries, analyze employment spans, and produce skill timeline insights."""
    timeline_entries = extract_timeline_entries(text)
    timeline_analysis = analyze_employment_spans(timeline_entries)
    skill_timeline = skill_timeline_insights(sections, sorted(resume_skills))
    return timeline_entries, timeline_analysis, skill_timeline


def compute_resume_sections_summary(sections: dict[str, Any]) -> dict[str, int]:
    """Count blocks per section for the API response."""
    return {
        "skills_blocks": len(sections.get("skills") or []),
        "experience_blocks": len(sections.get("experience") or []),
        "projects_blocks": len(sections.get("projects") or []),
        "education_blocks": len(sections.get("education") or []),
    }