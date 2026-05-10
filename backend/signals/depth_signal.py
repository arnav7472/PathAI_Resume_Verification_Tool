from __future__ import annotations

import re


ACTION_VERBS = [
    "analyzed",
    "automated",
    "built",
    "collaborated",
    "configured",
    "created",
    "deployed",
    "designed",
    "developed",
    "engineered",
    "implemented",
    "improved",
    "maintained",
    "managed",
    "optimized",
    "secured",
]
CONTEXT_TERMS = ["project", "system", "pipeline", "application", "api"]


def _count_phrase_occurrences(text: str, phrase: str) -> int:
    escaped = re.escape(phrase)
    pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def compute_depth_signal(text: str, skill_counts: dict[str, int]) -> dict:
    detected_verbs = [verb for verb in ACTION_VERBS if _count_phrase_occurrences(text, verb) > 0]
    has_context = any(_count_phrase_occurrences(text, term) > 0 for term in CONTEXT_TERMS)
    total_skill_mentions = sum(skill_counts.values())

    score = 0.2
    flags: list[str] = []

    if detected_verbs:
        score += 0.4
    else:
        flags.append("No action verbs detected")

    if has_context:
        score += 0.4
    else:
        flags.append("No project context found")

    if total_skill_mentions >= 4 and not detected_verbs:
        score = min(score, 0.3)
        flags.append("High number of tools with low depth")

    return {
        "score": max(0.0, min(1.0, score)),
        "flags": flags,
    }
