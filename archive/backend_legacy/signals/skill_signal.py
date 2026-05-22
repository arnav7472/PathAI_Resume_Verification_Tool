from __future__ import annotations


def _mention_score(count: int) -> float:
    if count <= 0:
        return 0.0
    if count == 1:
        return 0.3
    if 2 <= count <= 3:
        return 0.6
    return 1.0


def compute_skill_signal(skill_counts: dict[str, int]) -> dict:
    if not skill_counts:
        return {
            "score": 0.0,
            "flags": ["No supported skills detected"],
        }

    per_skill_scores = []
    flags: list[str] = []

    for skill, count in skill_counts.items():
        per_skill_scores.append(_mention_score(count))
        if count == 1:
            flags.append(f"Low evidence for {skill.title()} (mentioned once)")

    score = sum(per_skill_scores) / len(per_skill_scores)
    return {
        "score": max(0.0, min(1.0, score)),
        "flags": flags,
    }
