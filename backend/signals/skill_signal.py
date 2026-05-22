"""Skill evidence signals: evidence level mapping, claim building, and evidence map assembly."""

from __future__ import annotations

import re
from typing import Any, Literal

from ..evidence.extractor import EvidenceHit, extract_skill_evidence
from ..evidence.text import contains_phrase, snippet_signature, split_sentences
from ..parsers.section_parser import split_sentences_block
from ..scoring.confidence import confidence_for_claim
from ..verification.knowledge import BUZZWORDS

EvidenceLevel = Literal["demonstrated", "supported", "mentioned", "weak", "missing"]


def legacy_claim_status(level: EvidenceLevel) -> str:
    """Map evidence level to API status string."""
    if level in ("demonstrated", "supported"):
        return "verified"
    if level == "mentioned":
        return "likely"
    return "inflated"


def evidence_warning(level: EvidenceLevel) -> str:
    """Return warning string for a given evidence level."""
    if level in ("demonstrated", "supported"):
        return ""
    if level == "mentioned":
        return "Listed in skills without strong implementation context in experience or projects."
    if level == "weak":
        return "Weak or generic mention; add concrete implementation detail."
    if level == "missing":
        return "Required by the job description but not found in parsed resume sections."
    return ""


def evidence_type(skill: str, snippets: list[str]) -> str:
    """Classify evidence as direct or indirect (e.g. SQL inferred from PostgreSQL)."""
    if skill != "SQL":
        return "direct"
    joined = " ".join(snippets).lower()
    if "sql" in joined:
        return "direct"
    if re.search(r"postgres|mysql|sqlite|relational", joined):
        return "indirect"
    return "direct"


def positive_risk_note(skill: str, level: EvidenceLevel, hits: list[EvidenceHit]) -> str | None:
    """Generate a positive note for demonstrated skills with implementation context."""
    if level != "demonstrated":
        return None
    sec_blob = " ".join(h.section for h in hits)
    if skill in ("Kubernetes", "Docker", "Terraform") and "experience" in sec_blob:
        return f"{skill} is tied to implementation or infrastructure wording in structured experience segments."
    if skill == "React" and "projects" in sec_blob:
        return f"{skill} appears in a project or product context, not only as a keyword list."
    return f"{skill} is reinforced by contextual sentences outside a bare skills list."


def skill_order(required: set[str], discovered: list[str]) -> list[str]:
    """Order skills: required skills first (sorted), then the rest (sorted)."""
    req = [s for s in sorted(required) if s in discovered]
    rest = sorted(s for s in discovered if s not in required)
    return req + rest


def pattern_claims(sections: dict[str, Any], strictness: str) -> list[dict[str, Any]]:
    """Extract non-skill claims (experience, achievement, project, leadership, certification) from sections."""

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
                        "status": legacy_claim_status(lvl),
                        "confidence": conf,
                        "evidence": [{"section": section, "snippet": sentence[:240]}],
                        "evidence_type": "direct",
                        "evidence_count": 1,
                        "supporting_evidence": sentence[:240],
                    }
                )
                break

    return claims


def build_skill_claims(
    ordered_skills: list[str],
    required_skills: set[str],
    resume_skills: dict[str, int],
    sections: dict[str, Any],
    strictness: str,
    global_snippets: set[str],
) -> list[dict[str, Any]]:
    """Build claim dicts for each skill found in the resume."""

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
                "status": legacy_claim_status(level),
                "confidence": conf,
                "evidence": ev_objs,
                "evidence_type": evidence_type(skill, snippets),
                "evidence_count": resume_skills.get(skill, len(hits)),
                "supporting_evidence": snippets[0] if snippets else "",
            }
        )

    return claims


def build_missing_claims(
    missing_skills_raw: list[str],
    strictness: str,
) -> list[dict[str, Any]]:
    """Build claim dicts for skills required by JD but not found in resume."""
    claims: list[dict[str, Any]] = []
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
    return claims


def build_evidence_map(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert full claim dicts to the evidence_map API response format."""
    return [
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
            else evidence_warning(c.get("evidence_level", "weak")),
        }
        for c in claims
    ]


def add_positive_findings(
    claims: list[dict[str, Any]],
    findings: list[dict[str, str]],
    max_notes: int = 4,
) -> None:
    """Insert positive risk notes for demonstrated skills as low-severity findings."""
    positive_notes = 0
    for c in claims:
        if c.get("type") != "skill" or c.get("evidence_level") != "demonstrated":
            continue
        if positive_notes >= max_notes:
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
        note = positive_risk_note(sk, "demonstrated", hits_proxy)
        if note:
            findings.insert(0, {"message": note, "severity": "low"})
            positive_notes += 1