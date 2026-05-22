"""Human-readable explanations for resume verification findings.

Deterministic text generation for recruiter-facing summaries.
No LLMs, no randomness — all rules-based."""

from __future__ import annotations

from typing import Any


def generate_executive_summary(
    compatibility: int,
    confidence: int,
    risk_score: int,
    matched_skills: list[str],
    missing_skills_raw: list[str],
    verified_count: int,
    inflated_count: int,
    timeline_warnings: list[str],
    extraction_warnings: list[str] | None = None,
) -> str:
    """Short executive summary for recruiter review."""
    parts: list[str] = []

    # Alignment statement
    if compatibility >= 80:
        parts.append("Strong JD alignment")
    elif compatibility >= 50:
        parts.append("Moderate JD alignment")
    else:
        parts.append("Weak JD alignment")

    # Confidence statement
    if confidence >= 80:
        parts.append(f"high confidence ({confidence}%)")
    elif confidence >= 50:
        parts.append(f"moderate confidence ({confidence}%)")
    else:
        parts.append(f"low confidence ({confidence}%)")

    # Skill match
    if matched_skills:
        parts.append(f"{len(matched_skills)} skill(s) match JD")
    if missing_skills_raw:
        parts.append(f"{len(missing_skills_raw)} JD skill(s) missing")

    # Claim quality
    if verified_count > 0:
        parts.append(f"{verified_count} verified claim(s)")
    if inflated_count > 0:
        parts.append(f"{inflated_count} unsupported claim(s)")

    # Risk
    if risk_score >= 60:
        parts.append("high risk")
    elif risk_score >= 30:
        parts.append("moderate risk")
    else:
        parts.append("low risk")

    # Timeline
    if timeline_warnings:
        w = len(timeline_warnings)
        parts.append(f"{w} timeline warning(s)")

    # Extraction quality — adds operational caveat when OCR/parsing is unreliable
    if extraction_warnings:
        parts.append(
            "low-quality scan may reduce verification accuracy"
            if any("scan" in w.lower() or "ocr" in w.lower() for w in extraction_warnings)
            else "parsing warnings — review recommended"
        )

    return "; ".join(parts) + "."


def generate_risk_summary(risk_score: int) -> str:
    """Readable risk score explanation."""
    if risk_score >= 70:
        return "High risk — significant gaps or inconsistencies suggest the resume may overstate qualifications."
    if risk_score >= 40:
        return "Moderate risk — some claims lack supporting evidence or JD alignment is incomplete."
    if risk_score >= 20:
        return "Low risk — most claims are supported; minor gaps remain."
    return "Very low risk — claims are well-supported and JD-aligned."


def readable_missing_skill_reason(skill: str) -> str:
    """Human-readable explanation for a missing skill."""
    return f"{skill} is required by the job description but was not found in parsed resume sections."


def readable_timeline_warning(warning: dict[str, Any]) -> str | None:
    """Convert timeline analysis entry to readable text."""
    if warning.get("overlap_warning"):
        start = warning.get("start_year", "?")
        end = warning.get("end_year", "?")
        evidence = str(warning.get("evidence", ""))[:60]
        return f"Overlapping dates ({start}-{end}) in: {evidence}"
    if warning.get("gap_after_months_estimate") is not None:
        gap = warning["gap_after_months_estimate"]
        evidence = str(warning.get("evidence", ""))[:60]
        if gap > 12:
            return f"Employment gap of {gap} months in: {evidence}"
        return None  # short gaps are not notable
    return None


def readable_timeline_summary(
    overlaps: list[str],
    gaps: list[str],
    inflation: list[str],
) -> list[str]:
    """Convert timeline analysis output to recruiter-facing bullet points."""
    result: list[str] = []
    for o in overlaps[:4]:
        result.append(f"Timeline overlap: {o[:120]}")
    for g in gaps[:4]:
        result.append(f"Timeline gap: {g[:120]}")
    for i in inflation[:4]:
        result.append(f"Title concern: {i[:120]}")
    return result


def readable_fraud_reason(
    claim: dict[str, Any],
    consistency_findings: list[dict[str, Any]],
) -> str | None:
    """Generate readable explanation for fraud/consistency signals."""
    if not consistency_findings:
        return None
    claim_skill = claim.get("skill", "")
    claim_text = claim.get("claim", "")

    for f in consistency_findings:
        msg = str(f.get("claim", ""))
        if claim_skill and claim_skill.lower() in msg.lower():
            if f.get("status") == "buzzword":
                return f"{claim_skill} appears as a keyword without supporting implementation detail."
            if f.get("status") == "missing":
                return f"{claim_skill} is expected but not found in substantive sections."
    return None


def positive_evidence_summary(claims: list[dict[str, Any]], max_items: int = 5) -> list[str]:
    """Summarize what the resume does well — with safer wording for weak evidence."""
    notes: list[str] = []
    weak_found: int = 0
    for c in claims:
        if len(notes) >= max_items:
            break
        skill = c.get("skill", c.get("claim", ""))
        level = c.get("evidence_level", "")
        if level in ("demonstrated", "supported"):
            ev = c.get("evidence") or []
            sections = {e.get("section", "") for e in ev if isinstance(e, dict)}
            if sections:
                notes.append(f"{skill} claims are strongly supported by {', '.join(sorted(sections))} evidence.")
            else:
                notes.append(f"{skill} claims are supported by resume evidence.")
        elif level == "missing":
            notes.append(f"{skill} appears in skills but lacks implementation evidence.")
        elif level == "weak" and weak_found < 2:
            notes.append(f"{skill} has weak supporting evidence — consider manual review.")
            weak_found += 1
    return notes
