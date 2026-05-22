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
from ..signals.fraud_signal import (
    aggregate_findings,
    categorize_claims,
    compute_confidence,
    compute_initial_findings,
    compute_risk_score,
    compute_weak_areas,
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
    }