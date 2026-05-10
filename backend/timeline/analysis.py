"""Timeline parsing for employment continuity, overlaps, and skill first-seen years."""

from __future__ import annotations

import re
from typing import Any, Literal

from ..evidence.text import contains_phrase, split_sentences
from ..verification.knowledge import SKILL_ALIASES

EndKind = int | Literal["present"]


def extract_timeline_entries(full_text: str) -> list[dict[str, Any]]:
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


def analyze_employment_spans(entries: list[dict[str, Any]]) -> dict[str, Any]:
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
            if sy2 <= ey and sy <= ey2:
                overlaps.append(f"Overlapping ranges {sy}-{ey} vs {sy2}-{ey2}: {ev[:80]}…")

    for i in range(len(normalized) - 1):
        _, ey, _ = normalized[i]
        sy2, _, _ = normalized[i + 1]
        if sy2 > ey + 1:
            gaps.append(f"Gap between {ey} and {sy2} (possible employment gap).")

    for sy, ey, ev in normalized:
        span = ey - sy
        if span > 25:
            suspicious_inflation.append(f"Unusually long single span ({span} years): {ev[:90]}…")

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
