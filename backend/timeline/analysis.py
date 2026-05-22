"""Timeline parsing for employment continuity, overlaps, skill density, and title inflation."""

from __future__ import annotations

import re
from typing import Any, Literal

from ..evidence.text import contains_phrase, split_sentences
from ..verification.knowledge import SKILL_ALIASES

EndKind = int | Literal["present"]

# Title keywords that can indicate inflation when combined with junior experience
_SENIOR_TITLES = re.compile(
    r"\b(senior|lead|principal|staff|chief|head|director|vp|vice president|c-level|cto|ceo|founder|architect)\b",
    re.I,
)
_JUNIOR_CONTEXT = re.compile(r"\b(junior|entry.level|intern|fresher|less.than.\d+.years?)\b", re.I)
# Known fancy title patterns that often inflate
_INFLATED_TITLE_PATTERNS = re.compile(
    r"\b(rockstar|guru|ninja|wizard|evangelist|visionary|unicorn|10x)\b", re.I,
)


def extract_timeline_entries(full_text: str) -> list[dict[str, Any]]:
    """Extract year ranges with the source sentence kept for recruiter review."""

    entries: list[dict[str, Any]] = []
    for sentence in split_sentences(full_text):
        for match in re.finditer(
            r"\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2}|present|current)\b",
            sentence,
            flags=re.IGNORECASE,
        ):
            end_raw = match.group(2).lower()
            end_year: EndKind = "present" if end_raw in {"present", "current"} else int(end_raw)
            entries.append(
                {
                    "start_year": int(match.group(1)),
                    "end_year": end_year,
                    "evidence": sentence.strip(),
                    "overlap_warning": False,
                    "gap_after_months_estimate": None,
                }
            )
    return entries


def _to_year_end(end: EndKind) -> int:
    if end == "present":
        return 2026  # analysis-time default; resume review context
    return int(end)


def _detect_title_inflation(sentence: str) -> str | None:
    """Check for suspicious title patterns that suggest exaggeration."""
    if _INFLATED_TITLE_PATTERNS.search(sentence):
        return f"Fancy title detected: '{sentence[:100]}'"
    # Senior title with junior context = inflation risk
    if _SENIOR_TITLES.search(sentence) and _JUNIOR_CONTEXT.search(sentence):
        return f"Senior title with junior context: '{sentence[:100]}'"
    return None


def analyze_employment_spans(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Flag coarse year-level continuity issues; month-level accuracy is not inferred."""

    normalized: list[tuple[int, int, str]] = []
    for e in entries:
        try:
            sy = int(e["start_year"])
            ey_raw = e["end_year"]
            ey = _to_year_end(ey_raw)  # type: ignore[arg-type]
            ev = str(e.get("evidence", ""))
            normalized.append((sy, ey, ev))
        except (KeyError, TypeError, ValueError):
            continue

    normalized.sort(key=lambda x: x[0])

    overlaps: list[str] = []
    gaps: list[str] = []
    suspicious_inflation: list[str] = []

    for i, (sy, ey, ev) in enumerate(normalized):
        for j, (sy2, ey2, ev2) in enumerate(normalized):
            if i >= j:
                continue
            # Overlaps are warnings only; concurrent roles and education can be legitimate.
            if sy2 <= ey and sy <= ey2:
                # Degree of overlap: stronger signal if >1 year overlap
                overlap_years = min(ey, ey2) - max(sy, sy2)
                overlap_severity = ", significant" if overlap_years > 1 else ""
                overlaps.append(
                    f"Overlapping ranges {sy}-{ey} vs {sy2}-{ey2}{overlap_severity}: {ev[:80]}…"
                )

    for i in range(len(normalized) - 1):
        _, ey, ev = normalized[i]
        sy2, _, ev2 = normalized[i + 1]
        gap = sy2 - ey - 1
        if gap > 1:
            gaps.append(f"Gap of {gap} years between {ey} and {sy2}: {ev[:60]}… | {ev2[:60]}…")
        elif gap == 1:
            gaps.append(f"Small gap ({gap} year) between {ey} and {sy2}: {ev[:60]}…")

    for sy, ey, ev in normalized:
        span = ey - sy
        if span > 25:
            suspicious_inflation.append(f"Unusually long single span ({span} years): {ev[:90]}…")
        # Check for inflation signals per entry
        title_flag = _detect_title_inflation(ev)
        if title_flag:
            suspicious_inflation.append(title_flag)

    return {
        "overlaps": overlaps[:12],
        "gaps": gaps[:8],
        "suspicious_inflation": suspicious_inflation[:6],
    }


def skill_timeline_insights(
    sections: dict[str, Any],
    resume_skills: list[str],
) -> list[dict[str, Any]]:
    """Earliest calendar year a skill appears in implementation-heavy sections."""
    from ..parsers.section_parser import iter_section_sentences

    impl: list[tuple[str, str]] = []
    for key in ("experience", "projects", "achievements"):
        impl.extend(iter_section_sentences(sections, key))  # type: ignore[arg-type]

    out: list[dict[str, Any]] = []
    for skill in resume_skills[:40]:
        aliases = SKILL_ALIASES.get(skill, [skill.lower()])
        years_found: list[int] = []
        for _, sentence in impl:
            if not any(contains_phrase(sentence, a) for a in aliases):
                continue
            for m in re.finditer(r"\b(20\d{2}|19\d{2})\b", sentence):
                years_found.append(int(m.group(1)))
        if not years_found:
            out.append(
                {
                    "skill": skill,
                    "first_seen": None,
                    "experience_years_estimate": None,
                }
            )
            continue
        first = min(years_found)
        last = max(years_found)
        est = max(1, last - first + 1)
        out.append(
            {
                "skill": skill,
                "first_seen": str(first),
                "experience_years_estimate": est,
            }
        )
    return out