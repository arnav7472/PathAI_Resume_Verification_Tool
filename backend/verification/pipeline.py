"""End-to-end resume verification: sections → evidence → scoring → API-shaped payload.

Orchestrator only — all signal reasoning is delegated to backend/signals/.
"""

from __future__ import annotations

from typing import Any

from ..parsers.section_parser import parse_resume_sections
from ..signals.consistency_signal import compute_consistency_findings
from ..signals.depth_signal import (
    compute_compatibility,
    compute_resume_sections_summary,
    compute_timeline_signals,
    detect_action_verbs,
)
from ..signals.explainability import (
    generate_executive_summary,
    generate_risk_summary,
    positive_evidence_summary,
)
from ..signals.fraud_signal import (
    aggregate_findings,
    categorize_claims,
    compute_confidence,
    compute_confidence_reason,
    compute_initial_findings,
    compute_risk_score,
    compute_weak_areas,
    readable_confidence_explanation,
    readable_risk_breakdown,
)
from ..signals.skill_signal import (
    add_positive_findings,
    build_evidence_map,
    build_missing_claims,
    build_skill_claims,
    pattern_claims,
    skill_order,
)
from ..verification.jd_extract import extract_job_requirements
from ..verification.knowledge import STRICTNESS
from ..verification.normalize import normalize_resume_text
from ..verification.skills_discovery import discover_skills
from ..verification.years import extract_years_experience

try:
    from ..parser.extraction_quality import estimate_text_quality
except ImportError:
    estimate_text_quality = None


def analyze_resume(
    resume_text: str,
    job_description: str = "",
    strictness: str = "medium",
    cross_reference_sync: bool = True,
) -> dict[str, object]:
    strictness = strictness.lower() if strictness.lower() in STRICTNESS else "medium"
    text = normalize_resume_text(resume_text)
    jd = normalize_resume_text(job_description)

    sections = parse_resume_sections(text)
    resume_skills = discover_skills(sections)
    jd_requirements = extract_job_requirements(jd)
    action_verbs_list = detect_action_verbs(text)

    required_skills = set(jd_requirements["skills"]) if jd else set()
    matched_skills = sorted(required_skills & set(resume_skills.keys()))
    missing_skills_raw = sorted(required_skills - set(resume_skills.keys()))

    compatibility = compute_compatibility(resume_skills, required_skills, matched_skills)

    global_snippets: set[str] = set()
    ordered_skills = skill_order(required_skills, list(resume_skills.keys()))

    claims: list[dict[str, Any]] = []
    claims.extend(build_skill_claims(ordered_skills, required_skills, resume_skills, sections, strictness, global_snippets))
    claims.extend(build_missing_claims(missing_skills_raw, strictness))
    claims.extend(pattern_claims(sections, strictness))

    inflated_claims, verified_claims = categorize_claims(claims)
    weak_areas = compute_weak_areas(missing_skills_raw, action_verbs_list, claims)
    findings = compute_initial_findings(missing_skills_raw, action_verbs_list)

    consistency_findings = compute_consistency_findings(claims, text, cross_reference_sync=cross_reference_sync)

    add_positive_findings(claims, findings)

    risk_score = compute_risk_score(
        compatibility, inflated_claims, missing_skills_raw, action_verbs_list,
        consistency_findings, strictness, cross_reference_sync,
    )

    confidence = compute_confidence(compatibility, verified_claims, inflated_claims, action_verbs_list)

    outcomes_available = len(findings) < 2
    findings = aggregate_findings(findings, consistency_findings, needs_fallback_message=outcomes_available)

    evidence_map = build_evidence_map(claims)

    timeline_entries, timeline_analysis, skill_timeline = compute_timeline_signals(text, sections, sorted(resume_skills.keys()))

    # Gather timeline warnings for executive summary
    timeline_warnings: list[str] = []
    if timeline_analysis:
        timeline_warnings.extend(timeline_analysis.get("overlaps", []))
        timeline_warnings.extend(timeline_analysis.get("gaps", []))
        timeline_warnings.extend(timeline_analysis.get("suspicious_inflation", []))

    verified_count = len(verified_claims)
    inflated_count = len(inflated_claims)
    consistency_count = len(consistency_findings)

    # Extraction quality assessment
    quality_warnings: list[str] = []
    if estimate_text_quality is not None:
        quality = estimate_text_quality(text)
        if quality.get("is_low_quality"):
            detail = quality.get("detail", "")
            if detail:
                quality_warnings.append(detail)

    executive_summary = generate_executive_summary(
        compatibility, confidence, risk_score,
        matched_skills, missing_skills_raw,
        verified_count, inflated_count,
        timeline_warnings,
        extraction_warnings=quality_warnings,
    )
    risk_summary = generate_risk_summary(risk_score)
    confidence_explanation = readable_confidence_explanation(confidence)
    risk_breakdown = readable_risk_breakdown(
        compatibility, missing_skills_raw,
        inflated_count, consistency_count,
        bool(action_verbs_list),
    )
    positive_summary = positive_evidence_summary(claims)
    confidence_reason = compute_confidence_reason(
        compatibility, verified_claims, inflated_claims,
        action_verbs_list,
        sum(1 for c in claims
            if c.get("evidence_level") in ("demonstrated", "supported")
            and c.get("type") in ("experience", "project", "leadership")),
    )

    # Add quality findings to the findings list (low severity) — but only for non-trivial quality issues
    if quality_warnings:
        findings.append({
            "message": "; ".join(quality_warnings),
            "severity": "medium",
        })

    return {
        "skills": sorted(resume_skills.keys()),
        "skill_counts": dict(resume_skills),
        "action_verbs": action_verbs_list,
        "claims": claims,
        "evidence": evidence_map,
        "timeline": timeline_entries,
        "timeline_analysis": timeline_analysis,
        "skill_timeline_insights": skill_timeline,
        "job_description": jd,
        "job_requirements": jd_requirements,
        "compatibility_score": compatibility,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills_raw,
        "weak_areas": weak_areas,
        "risk_score": risk_score,
        "confidence": confidence,
        "findings": findings,
        "consistency_findings": consistency_findings,
        "strictness": strictness,
        "cross_reference_sync": cross_reference_sync,
        "years_experience": extract_years_experience(text),
        "text": text,
        "resume_sections": compute_resume_sections_summary(sections),
        # Explainability layer additions
        "executive_summary": executive_summary,
        "risk_summary": risk_summary,
        "confidence_explanation": confidence_explanation,
        "risk_breakdown": risk_breakdown,
        "positive_evidence_summary": positive_summary,
        "confidence_reason": confidence_reason,
    }