from __future__ import annotations

from typing import Any

from ..evidence.text import contains_phrase
from ..parsers.section_parser import all_indexed_sentences
from .knowledge import SKILL_ALIASES


def discover_skills(sections: dict[str, Any]) -> dict[str, int]:
    """Count skill-associated sentence hits across structured sections."""
    counts: dict[str, int] = {}
    indexed = all_indexed_sentences(sections)
    for skill, aliases in SKILL_ALIASES.items():
        n = 0
        for _, sentence in indexed:
            if any(contains_phrase(sentence, a) for a in aliases):
                n += 1
        if n:
            counts[skill] = n
    return counts
