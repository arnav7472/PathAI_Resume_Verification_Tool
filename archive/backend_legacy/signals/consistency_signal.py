from __future__ import annotations


def compute_consistency_signal(
    skills_count: int,
    years_experience: int | None,
    has_senior_title: bool,
    depth_score: float,
) -> dict:
    if years_experience is not None and skills_count > 8 and years_experience <= 1:
        return {
            "score": 0.2,
            "flags": [f"{skills_count} skill mentions with {years_experience} year experience -> suspicious"],
        }

    if has_senior_title and depth_score < 0.5:
        return {
            "score": 0.3,
            "flags": ["Senior title without depth evidence"],
        }

    return {
        "score": 0.8,
        "flags": [],
    }
