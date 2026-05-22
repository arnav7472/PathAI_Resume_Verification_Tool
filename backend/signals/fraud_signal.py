"""Fraud/risk signals: risk score, confidence score, weak areas, and findings aggregation."""

from __future__ import annotations

from typing import Any

from ..verification.knowledge import STRICTNESS


def categorize_claims(claims: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split claims into inflated and verified buckets based on evidence level."""
    inflated = [c for c in claims if c.get("evidence_level") in {"weak", "missing"} or c["status"] == "inflated"]
    verified = [c for c in claims if c.get("evidence_level") in {"demonstrated", "supported"}]
    return inflated, verified


def compute_weak_areas(
    missing_skills_raw: list[str],
    action_verbs_list: list[str],
    claims: list[dict[str, Any]],
) -> list[str]:
    """Generate human-readable weak area strings."""
    weak_areas: list[str] = []
    if missing_skills_raw:
        weak_areas.append(f"Missing JD skills: {', '.join(missing_skills_raw[:8])}")
    if not action_verbs_list:
        weak_areas.append("Resume lacks strong action verbs.")
    weak_claims = [c for c in claims if c.get("evidence_level") in {"weak", "mentioned"}]
    if weak_claims:
        weak_areas.append(f"{len(weak_claims)} claim(s) rely mainly on skills-list or light context.")
    # New: flag when claims are missing project/experience backing
    project_or_exp_claims = [c for c in claims if c.get("evidence_level") in ("demonstrated", "supported") and c.get("type") != "skill"]
    if not project_or_exp_claims:
        weak_areas.append("No project or experience achievements detected.")
    return weak_areas


def compute_initial_findings(
    missing_skills_raw: list[str],
    action_verbs_list: list[str],
) -> list[dict[str, str]]:
    """Generate initial findings around missing skills and action verbs."""
    findings: list[dict[str, str]] = []
    if missing_skills_raw:
        findings.append(
            {
                "message": f"Resume is missing {len(missing_skills_raw)} job description requirement(s).",
                "severity": "medium",
            }
        )
    if not action_verbs_list:
        findings.append({"message": "No strong action verbs were detected in the resume text.", "severity": "medium"})
    else:
        findings.append({"message": f"Detected action verbs: {', '.join(action_verbs_list[:12])}.", "severity": "low"})
    return findings


def compute_risk_score(
    compatibility: int,
    inflated_claims: list[dict[str, Any]],
    missing_skills_raw: list[str],
    action_verbs_list: list[str],
    consistency_findings: list[dict[str, Any]],
    strictness: str,
    cross_reference_sync: bool,
) -> int:
    """Compute risk score based on JD mismatch, weak/missing support, and consistency issues."""
    st = STRICTNESS[strictness]
    risk_score = 100 - compatibility
    risk_score += len([c for c in inflated_claims if c.get("type") == "skill"]) * (st["inflated_penalty"] // 2)
    risk_score += len(missing_skills_raw) * (st["missing_penalty"] // 10)
    if not action_verbs_list:
        risk_score += 16 if strictness == "high" else 10
    if cross_reference_sync:
        risk_score += min(24, len(consistency_findings) * (8 if strictness == "high" else 5))
    return round(max(0, min(100, risk_score)))


def compute_confidence(
    compatibility: int,
    verified_claims: list[dict[str, Any]],
    inflated_claims: list[dict[str, Any]],
    action_verbs_list: list[str],
) -> int:
    """Compute overall confidence score rewarding supported claims and discounting inflated ones."""
    return round(
        max(
            0,
            min(
                100,
                (compatibility * 0.78)
                + (len(verified_claims) * 2.8)
                + (len(action_verbs_list) * 1.2)
                - (len(inflated_claims) * 4.2),
            ),
        )
    )


def compute_confidence_reason(
    compatibility: int,
    verified_claims: list[dict[str, Any]],
    inflated_claims: list[dict[str, Any]],
    action_verbs_list: list[str],
    demonstrated_exp_proj: int,
) -> str:
    """Generate a human-readable reason for the computed confidence score."""
    reasons: list[str] = []
    if compatibility >= 80:
        reasons.append("strong JD alignment")
    elif compatibility >= 50:
        reasons.append("moderate JD alignment")
    else:
        reasons.append("weak JD alignment")
    if verified_claims:
        reasons.append(f"{len(verified_claims)} verified claim(s)")
    else:
        reasons.append("no verified claims")
    if demonstrated_exp_proj > 0:
        reasons.append(f"{demonstrated_exp_proj} experience/project achievement(s) confirmed")
    if inflated_claims:
        reasons.append(f"{len(inflated_claims)} inflated claim(s) lowering trust")
    if not action_verbs_list:
        reasons.append("no action verbs detected")
    return "; ".join(reasons)


def aggregate_findings(
    findings: list[dict[str, str]],
    consistency_findings: list[dict[str, Any]],
    needs_fallback_message: bool,
) -> list[dict[str, str]]:
    """Merge consistency findings into the main findings list and ensure minimum findings count."""
    if needs_fallback_message and len(findings) < 2:
        findings.insert(
            0,
            {"message": "Structured section parse completed; each claim uses sentence-level snippets.", "severity": "low"},
        )

    for item in consistency_findings[:8]:
        if item.get("status") == "buzzword":
            findings.append({"message": str(item["claim"]), "severity": "medium"})
        elif item.get("status") in ("mentioned", "weak", "missing"):
            findings.append(
                {"message": str(item["claim"]), "severity": "high" if item["status"] == "missing" else "medium"}
            )

    return findings