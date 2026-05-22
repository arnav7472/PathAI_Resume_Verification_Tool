from __future__ import annotations


def _classify_risk(confidence: int) -> str:
    if confidence <= 40:
        return "High"
    if confidence <= 70:
        return "Medium"
    return "Low"


def score_verification(
    skills: list[str],
    skill_signal: dict,
    depth_signal: dict,
    consistency_signal: dict,
) -> dict:
    raw_confidence = (
        (0.5 * skill_signal["score"])
        + (0.3 * depth_signal["score"])
        + (0.2 * consistency_signal["score"])
    )
    confidence = round(max(0.0, min(1.0, raw_confidence)) * 100)

    combined_flags: list[str] = []
    for signal in (skill_signal, depth_signal, consistency_signal):
        for flag in signal["flags"]:
            if flag not in combined_flags:
                combined_flags.append(flag)

    return {
        "skills": skills,
        "confidence": confidence,
        "risk": _classify_risk(confidence),
        "flags": combined_flags,
    }
