"""End-to-end resume verification: sections → evidence → scoring → API-shaped payload."""

from __future__ import annotations

import re
from typing import Any, Literal

from ..evidence.extractor import EvidenceHit, extract_skill_evidence
from ..evidence.text import contains_phrase, snippet_signature, split_sentences
from ..parsers.section_parser import parse_resume_sections, split_sentences_block
from ..scoring.confidence import confidence_for_claim
from ..timeline.analysis import analyze_employment_spans, extract_timeline_entries, skill_timeline_insights
from .jd_extract import extract_job_requirements
from .knowledge import ACTION_VERBS, BUZZWORDS, STRICTNESS
from .normalize import normalize_resume_text
from .skills_discovery import discover_skills
from .years import extract_years_experience

EvidenceLevel = Literal["demonstrated", "supported", "mentioned", "weak", "missing"]


def _legacy_claim_status(level: EvidenceLevel) -> str:
    if level in ("demonstrated", "supported"):
        return "verified"
    if level == "mentioned":
        return "likely"
    return "inflated"


def _evidence_warning(level: EvidenceLevel) -> str:
    if level in ("demonstrated", "supported"):
        return ""
    if level == "mentioned":
        return "Listed in skills without strong implementation context in experience or projects."
    if level == "weak":
        return "Weak or generic mention; add concrete implementation detail."
    if level == "missing":
        return "Required by the job description but not found in parsed resume sections."
    return ""


def _evidence_type(skill: str, snippets: list[str]) -> str:
    if skill != "SQL":
        return "direct"
    joined = " ".join(snippets).lower()
    if "sql" in joined:
        return "direct"
    if re.search(r"postgres|mysql|sqlite|relational", joined):
        return "indirect"
    return "direct"


def _positive_risk_note(skill: str, level: EvidenceLevel, hits: list[EvidenceHit]) -> str | None:
    if level != "demonstrated":
        return None
    sec_blob = " ".join(h.section for h in hits)
    if skill in ("Kubernetes", "Docker", "Terraform") and "experience" in sec_blob:
        return f"{skill} is tied to implementation or infrastructure wording in structured experience segments."
    if skill == "React" and "projects" in sec_blob:
        return f"{skill} appears in a project or product context, not only as a keyword list."
    return f"{skill} is reinforced by contextual sentences outside a bare skills list."


def _skill_order(required: set[str], discovered: list[str]) -> list[str]:
    req = [s for s in sorted(required) if s in discovered]
    rest = sorted(s for s in discovered if s not in required)
    return req + rest


def _pattern_claims(sections: dict[str, Any], strictness: str) -> list[dict[str, Any]]:
    blocks: list[tuple[str, str]] = []
    for name in ("experience", "projects", "achievements", "education", "certifications", "summary", "other"):
        for block in sections.get(name) or []:
            for line in block.get("lines") or []:
                blocks.append((name, line))

    patterns = [
        ("experience", r"\b\d{1,2}\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)\b"),
        ("achievement", r"\b(?:improved|increased|reduced|decreased|optimized|cut)\b[^.?!]*\b\d+%"),
        ("project", r"\b(?:built|developed|created|designed|implemented|deployed|managed)\b[^.?!]*(?:api|application|platform|pipeline|cluster|model|project|system)s?\b"),
        ("leadership", r"\b(?:led|managed|mentored|collaborated|coordinated)\b[^.?!]*(?:team|engineers|developers|stakeholders|project)s?\b"),
        ("certification", r"\b(?:certified|certification|aws certified|azure certified|security\+|cissp)\b"),
    ]

    claims: list[dict[str, Any]] = []
    seen: set[str] = set()

    for section, raw_line in blocks:
        for sentence in split_sentences_block(raw_line):
            for claim_type, pattern in patterns:
                if not re.search(pattern, sentence, flags=re.IGNORECASE):
                    continue
                value = sentence[:200]
                key = f"{claim_type}:{value.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                sec_weight = "experience" if section == "experience" else section
                if sec_weight in ("experience", "projects"):
                    lvl: EvidenceLevel = "demonstrated"
                elif sec_weight in ("certifications", "education"):
                    lvl = "supported"
                else:
                    lvl = "mentioned" if len(sentence) < 90 else "supported"

                has_buzz = any(contains_phrase(sentence, w) for w in BUZZWORDS)
                if has_buzz:
                    lvl = "weak"

                hits = [
                    EvidenceHit(section=section, snippet=sentence[:240], raw_sentence=sentence, match_score=0.75)
                ]
                conf = confidence_for_claim(value[:40], lvl, hits, strictness=strictness, claim_type=claim_type)
                claims.append(
                    {
                        "type": claim_type,
                        "skill": value[:80],
                        "value": value,
                        "claim": value,
                        "evidence_level": lvl,
                        "status": _legacy_claim_status(lvl),
                        "confidence": conf,
                        "evidence": [{"section": section, "snippet": sentence[:240]}],
                        "evidence_type": "direct",
                        "evidence_count": 1,
                        "supporting_evidence": sentence[:240],
                    }
                )
                break

    return claims


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
    action_verbs_list: list[str] = []

    for verb in ACTION_VERBS:
        if any(contains_phrase(sentence, verb) for sentence in split_sentences(text)):
            action_verbs_list.append(verb)

    required_skills = set(jd_requirements["skills"]) if jd else set()
    matched_skills = sorted(required_skills & set(resume_skills.keys()))
    missing_skills_raw = sorted(required_skills - set(resume_skills.keys()))

    resume_skill_count = max(1, len(resume_skills))
    match_ratio = len(matched_skills) / max(1, len(required_skills)) if required_skills else min(1.0, len(resume_skills) / 8)
    coverage_bonus = min(18, resume_skill_count * 2)
    compatibility = round(max(0, min(100, (match_ratio * 76) + coverage_bonus)))

    global_snippets: set[str] = set()
    ordered_skills = _skill_order(required_skills, list(resume_skills.keys()))

    claims: list[dict[str, Any]] = []

    for skill in ordered_skills:
        hits, level = extract_skill_evidence(
            skill,
            sections,
            required_by_jd=skill in required_skills,
            global_used_snippets=global_snippets,
        )
        for h in hits:
            global_snippets.add(snippet_signature(h.snippet))

        conf = confidence_for_claim(skill, level, hits, strictness=strictness)
        snippets = [h.snippet for h in hits]
        ev_objs = [{"section": h.section, "snippet": h.snippet} for h in hits]

        claims.append(
            {
                "type": "skill",
                "skill": skill,
                "value": skill,
                "claim": f"{skill} experience",
                "evidence_level": level,
                "status": _legacy_claim_status(level),
                "confidence": conf,
                "evidence": ev_objs,
                "evidence_type": _evidence_type(skill, snippets),
                "evidence_count": resume_skills.get(skill, len(hits)),
                "supporting_evidence": snippets[0] if snippets else "",
            }
        )

    for skill in missing_skills_raw:
        claims.append(
            {
                "type": "skill",
                "skill": skill,
                "value": skill,
                "claim": f"{skill} (required by job description)",
                "evidence_level": "missing",
                "status": "inflated",
                "confidence": confidence_for_claim(skill, "missing", [], strictness=strictness),
                "evidence": [],
                "evidence_type": "missing",
                "evidence_count": 0,
                "supporting_evidence": "",
            }
        )

    claims.extend(_pattern_claims(sections, strictness))

    inflated_claims = [c for c in claims if c.get("evidence_level") in {"weak", "missing"} or c["status"] == "inflated"]
    verified_claims = [c for c in claims if c.get("evidence_level") in {"demonstrated", "supported"}]

    weak_areas: list[str] = []
    if missing_skills_raw:
        weak_areas.append(f"Missing JD skills: {', '.join(missing_skills_raw[:8])}")
    if not action_verbs_list:
        weak_areas.append("Resume lacks strong action verbs.")
    weak_claims = [c for c in claims if c.get("evidence_level") in {"weak", "mentioned"}]
    if weak_claims:
        weak_areas.append(f"{len(weak_claims)} claim(s) rely mainly on skills-list or light context.")

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

    consistency_findings: list[dict[str, Any]] = []
    if cross_reference_sync:
        for c in claims:
            if c.get("type") != "skill":
                continue
            lvl = c.get("evidence_level")
            sk = str(c.get("skill", ""))
            if lvl in ("demonstrated", "supported", None):
                continue
            if lvl == "mentioned":
                consistency_findings.append(
                    {
                        "claim": f"{sk} appears primarily as a keyword or in the skills section without implementation bullets.",
                        "status": lvl,
                        "evidence": [e.get("snippet", "") for e in (c.get("evidence") or [])][:2],
                    }
                )
            elif lvl == "weak":
                consistency_findings.append(
                    {
                        "claim": f"{sk} is only loosely described; strengthen with outcomes or system context.",
                        "status": lvl,
                        "evidence": [e.get("snippet", "") for e in (c.get("evidence") or [])][:2],
                    }
                )
            elif lvl == "missing":
                consistency_findings.append(
                    {
                        "claim": f"{sk} is expected from the job description but was not located in parsed resume sections.",
                        "status": lvl,
                        "evidence": [],
                    }
                )

        for sentence in split_sentences(text):
            if any(contains_phrase(sentence, w) for w in BUZZWORDS):
                hit_verb = any(contains_phrase(sentence, v) for v in ACTION_VERBS)
                if not hit_verb:
                    consistency_findings.append({"claim": sentence[:120], "status": "buzzword", "evidence": [sentence[:240]]})

    positive_notes = 0
    for c in claims:
        if c.get("type") != "skill" or c.get("evidence_level") != "demonstrated":
            continue
        if positive_notes >= 4:
            break
        sk = str(c.get("skill", ""))
        evlist = c.get("evidence") or []
        hits_proxy = [
            EvidenceHit(
                section=str(e.get("section", "")),
                snippet=str(e.get("snippet", "")),
                raw_sentence="",
                match_score=0.5,
            )
            for e in evlist
        ]
        note = _positive_risk_note(sk, "demonstrated", hits_proxy)
        if note:
            findings.insert(0, {"message": note, "severity": "low"})
            positive_notes += 1

    st = STRICTNESS[strictness]
    risk_score = 100 - compatibility
    risk_score += len([c for c in inflated_claims if c.get("type") == "skill"]) * (st["inflated_penalty"] // 2)
    risk_score += len(missing_skills_raw) * (st["missing_penalty"] // 10)
    if not action_verbs_list:
        risk_score += 16 if strictness == "high" else 10
    if cross_reference_sync:
        risk_score += min(24, len(consistency_findings) * (8 if strictness == "high" else 5))
    risk_score = round(max(0, min(100, risk_score)))

    confidence = round(
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

    if len(findings) < 2:
        findings.insert(0, {"message": "Structured section parse completed; each claim uses sentence-level snippets.", "severity": "low"})

    for item in consistency_findings[:8]:
        if item.get("status") == "buzzword":
            findings.append({"message": str(item["claim"]), "severity": "medium"})
        elif item.get("status") in ("mentioned", "weak", "missing"):
            findings.append({"message": str(item["claim"]), "severity": "high" if item["status"] == "missing" else "medium"})

    evidence_map = [
        {
            "claim": c["claim"],
            "type": c["type"],
            "skill": c.get("skill", c["claim"]),
            "evidence_level": c.get("evidence_level"),
            "status": c["status"],
            "confidence": c["confidence"],
            "evidence": c.get("evidence", []),
            "evidence_type": c.get("evidence_type", "direct"),
            "warning": ""
            if c.get("evidence_level") in ("demonstrated", "supported")
            else _evidence_warning(c.get("evidence_level", "weak")),  # type: ignore[arg-type]
        }
        for c in claims
    ]

    timeline_entries = extract_timeline_entries(text)
    timeline_analysis = analyze_employment_spans(timeline_entries)
    skill_timeline = skill_timeline_insights(sections, sorted(resume_skills.keys()))

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
        "resume_sections": {
            "skills_blocks": len(sections.get("skills") or []),
            "experience_blocks": len(sections.get("experience") or []),
            "projects_blocks": len(sections.get("projects") or []),
            "education_blocks": len(sections.get("education") or []),
        },
    }
