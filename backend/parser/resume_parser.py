from __future__ import annotations

import re


SKILL_KEYWORDS = [
    "python",
    "java",
    "machine learning",
    "sql",
    "aws",
    "docker",
    "kubernetes",
    "react",
    "typescript",
]
SENIOR_TITLES = ["senior", "lead", "principal"]


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


def _count_phrase_occurrences(text: str, phrase: str) -> int:
    escaped = re.escape(phrase)
    pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _extract_years_experience(text: str) -> int | None:
    matches = re.findall(r"\b(\d+)\s*\+?\s*years?\b", text, flags=re.IGNORECASE)
    if not matches:
        return None
    return max(int(match) for match in matches)


def _format_skill_label(skill: str) -> str:
    return " ".join(part.capitalize() for part in skill.split())


def _extract_timeline_ranges(text: str) -> list[dict[str, int]]:
    matches = re.findall(r"\b(19|20)\d{2}\s*[-–]\s*((?:19|20)\d{2}|present)\b", text, flags=re.IGNORECASE)
    timeline: list[dict[str, int]] = []

    for start_prefix, end_value in matches:
        full_match = re.search(
            rf"\b({start_prefix}\d{{2}})\s*[-–]\s*({re.escape(end_value)})\b",
            text,
            flags=re.IGNORECASE,
        )
        if not full_match:
            continue

        start_year = int(full_match.group(1))
        end_raw = full_match.group(2).lower()
        item: dict[str, int | str] = {
            "start_year": start_year,
            "end_year": end_raw if end_raw == "present" else int(end_raw),
        }
        timeline.append(item)  # type: ignore[arg-type]

    return timeline


def parse_resume_text(raw_text: str) -> dict:
    normalized_text = normalize_resume_text(raw_text)

    skill_counts: dict[str, int] = {}
    for skill in SKILL_KEYWORDS:
        count = _count_phrase_occurrences(normalized_text, skill)
        if count > 0:
            skill_counts[skill] = count

    has_senior_title = any(
        _count_phrase_occurrences(normalized_text, title) > 0 for title in SENIOR_TITLES
    )

    return {
        "skills": [_format_skill_label(skill) for skill in skill_counts.keys()],
        "skill_counts": skill_counts,
        "years_experience": _extract_years_experience(normalized_text),
        "has_senior_title": has_senior_title,
        "timeline": _extract_timeline_ranges(normalized_text),
        "text": normalized_text,
    }
