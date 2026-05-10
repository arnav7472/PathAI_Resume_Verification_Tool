from __future__ import annotations

import re


def extract_years_experience(text: str) -> int | None:
    patterns = [
        r"\b(\d{1,2})\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)\b",
        r"\b(?:experience|exp)\s*:?\s*(\d{1,2})\s*\+?\s*years?\b",
    ]
    values: list[int] = []
    for pattern in patterns:
        values.extend(int(match) for match in re.findall(pattern, text, flags=re.IGNORECASE))
    return max(values) if values else None
