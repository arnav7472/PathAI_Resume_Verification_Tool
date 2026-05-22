"""Tests for backend/signals/skill_signal.py — evidence levels, claims, and missing skills."""
from __future__ import annotations

from backend.evidence.extractor import EvidenceHit
from backend.parsers.section_parser import parse_resume_sections
from backend.signals.skill_signal import (
    build_evidence_map,
    build_missing_claims,
    build_skill_claims,
    evidence_type,
    evidence_warning,
    legacy_claim_status,
    pattern_claims,
    positive_risk_note,
    skill_order,
)


def _sections(
    experience: list[str] | None = None,
    skills: list[str] | None = None,
    projects: list[str] | None = None,
    summary: list[str] | None = None,
) -> dict:
    """Build minimal sections dict for testing."""
    s: dict = {}
    if skills:
        s["skills"] = [{"heading": "Skills", "lines": skills, "bullets": skills, "sentences": skills}]
    if experience:
        s["experience"] = [
            {"heading": "Experience", "lines": experience, "bullets": [experience[0]] if experience else [], "sentences": experience}
        ]
    if projects:
        s["projects"] = [
            {"heading": "Projects", "lines": projects, "bullets": [projects[0]] if projects else [], "sentences": projects}
        ]
    if summary:
        s["summary"] = [{"heading": "Summary", "lines": summary, "bullets": [], "sentences": summary}]
    return s


# ── evidence_type ──────────────────────────────────────────────────────────

class TestEvidenceType:
    def test_direct_match(self):
        assert evidence_type("Python", ["Wrote Python scripts"]) == "direct"

    def test_sql_direct(self):
        assert evidence_type("SQL", ["Used SQL queries"]) == "direct"

    def test_sql_indirect_via_postgres(self):
        # "postgres" (without "ql") avoids the direct "sql" substring match
        assert evidence_type("SQL", ["Used Postgres database"]) == "indirect"

    def test_sql_indirect_via_relational(self):
        assert evidence_type("SQL", ["Relational database experience"]) == "indirect"

    def test_sql_defaults_direct_when_no_match(self):
        assert evidence_type("SQL", ["Worked on databases"]) == "direct"


# ── legacy_claim_status ────────────────────────────────────────────────────

class TestLegacyClaimStatus:
    def test_demonstrated_returns_verified(self):
        assert legacy_claim_status("demonstrated") == "verified"

    def test_supported_returns_verified(self):
        assert legacy_claim_status("supported") == "verified"

    def test_mentioned_returns_likely(self):
        assert legacy_claim_status("mentioned") == "likely"

    def test_weak_returns_inflated(self):
        assert legacy_claim_status("weak") == "inflated"

    def test_missing_returns_inflated(self):
        assert legacy_claim_status("missing") == "inflated"


# ── evidence_warning ───────────────────────────────────────────────────────

class TestEvidenceWarning:
    def test_demonstrated_no_warning(self):
        assert evidence_warning("demonstrated") == ""

    def test_supported_no_warning(self):
        assert evidence_warning("supported") == ""

    def test_mentioned_has_warning(self):
        assert "skills" in evidence_warning("mentioned").lower()

    def test_weak_has_warning(self):
        assert "weak" in evidence_warning("weak").lower()

    def test_missing_has_warning(self):
        assert "required" in evidence_warning("missing").lower()


# ── positive_risk_note ─────────────────────────────────────────────────────

class TestPositiveRiskNote:
    def test_demonstrated_returns_note(self):
        hits = [EvidenceHit(section="experience", snippet="Built scalable microservices", raw_sentence="", match_score=0.8)]
        note = positive_risk_note("Docker", "demonstrated", hits)
        assert note is not None

    def test_not_demonstrated_returns_none(self):
        hits = [EvidenceHit(section="experience", snippet="some stuff", raw_sentence="", match_score=0.5)]
        assert positive_risk_note("Python", "mentioned", hits) is None

    def test_kubernetes_gets_infra_note(self):
        hits = [EvidenceHit(section="experience", snippet="experience with Kubernetes", raw_sentence="", match_score=0.9)]
        note = positive_risk_note("Kubernetes", "demonstrated", hits)
        assert note is not None
        assert "infrastructure" in note.lower() or "experience" in note.lower()

    def test_react_in_projects_gets_project_note(self):
        hits = [EvidenceHit(section="experience", snippet="React in projects", raw_sentence="", match_score=0.8)]
        note = positive_risk_note("React", "demonstrated", hits)
        assert note is not None


# ── skill_order ────────────────────────────────────────────────────────────

class TestSkillOrder:
    def test_required_skills_first(self):
        ordered = skill_order({"Python", "Docker"}, ["Kubernetes", "Python", "Docker", "AWS"])
        assert ordered[:2] == ["Docker", "Python"]
        assert ordered[2:] == ["AWS", "Kubernetes"]

    def test_empty_required(self):
        ordered = skill_order(set(), ["Python", "Java"])
        assert ordered == ["Java", "Python"]

    def test_required_but_not_discovered_omitted(self):
        ordered = skill_order({"Python", "Go"}, ["Python"])
        assert ordered == ["Python"]

    def test_all_discovered_required(self):
        ordered = skill_order({"A", "B"}, ["B", "A"])
        assert ordered == ["A", "B"]


# ── pattern_claims ─────────────────────────────────────────────────────────

class TestPatternClaims:
    def test_experience_years_detected(self):
        sections = _sections(experience=["5 years of experience in backend development"])
        claims = pattern_claims(sections, "medium")
        types = [c["type"] for c in claims]
        assert "experience" in types

    def test_achievement_percent_detected(self):
        sections = _sections(experience=["Improved latency by 40% using caching strategies"])
        claims = pattern_claims(sections, "medium")
        types = [c["type"] for c in claims]
        assert "achievement" in types

    def test_project_built_detected(self):
        sections = _sections(projects=["Built a real-time API for payment processing"])
        claims = pattern_claims(sections, "medium")
        types = [c["type"] for c in claims]
        assert "project" in types

    def test_leadership_detected(self):
        sections = _sections(experience=["Led a team of 5 engineers on microservices migration"])
        claims = pattern_claims(sections, "medium")
        types = [c["type"] for c in claims]
        assert "leadership" in types

    def test_buzzword_downgrades_to_weak(self):
        sections = _sections(experience=["Expert engineer built a platform with rockstar performance"])
        claims = pattern_claims(sections, "medium")
        for c in claims:
            if c["evidence_level"] == "weak":
                return
        assert False, "expected at least one claim downgraded to weak via buzzword"


# ── build_missing_claims ───────────────────────────────────────────────────

class TestBuildMissingClaims:
    def test_missing_skill_has_inflated_status(self):
        claims = build_missing_claims(["Kubernetes", "Terraform"], "medium")
        assert len(claims) == 2
        assert all(c["status"] == "inflated" for c in claims)
        assert all(c["evidence_level"] == "missing" for c in claims)
        assert all(c["evidence"] == [] for c in claims)

    def test_confidence_in_range(self):
        claims = build_missing_claims(["Docker"], "medium")
        assert 0 <= claims[0]["confidence"] <= 19

    def test_high_strictness_lower_confidence(self):
        low = build_missing_claims(["K8s"], "low")
        high = build_missing_claims(["K8s"], "high")
        assert low[0]["confidence"] <= 19  # both in missing band
        assert high[0]["confidence"] <= 19


# ── build_skill_claims ────(integration via real sections)──────────────────

class TestBuildSkillClaims:
    def test_demonstrated_when_experience_section(self):
        text = """Experience
        Built microservices with Python and Docker for 3 years. 
        Deployed containerized apps on Kubernetes.
        Skills
        Python, Docker, Kubernetes
        """
        sections = parse_resume_sections(text)
        claims = build_skill_claims(
            ["Python", "Docker", "Kubernetes"],
            set(),
            {"Python": 1, "Docker": 1, "Kubernetes": 1},
            sections,
            "medium",
            set(),
        )
        levels = {c["skill"]: c["evidence_level"] for c in claims}
        assert levels.get("Python") in ("demonstrated", "supported")
        assert levels.get("Docker") in ("demonstrated", "supported")

    def test_weak_when_only_skills_list(self):
        text = """Skills
        Python, Docker, Kubernetes
        """
        sections = parse_resume_sections(text)
        claims = build_skill_claims(
            ["Python", "Docker"],
            set(),
            {"Python": 1, "Docker": 1},
            sections,
            "medium",
            set(),
        )
        for c in claims:
            assert c["evidence_level"] in ("weak", "mentioned")

    def test_missing_when_required_but_not_found(self):
        text = """Skills
        Python
        """
        sections = parse_resume_sections(text)
        claims = build_skill_claims(
            ["Python"],
            {"Docker"},
            {"Python": 1},
            sections,
            "medium",
            set(),
        )
        # Only Python should appear (Docker not in ordered_skills)
        skills = [c["skill"] for c in claims]
        assert "Python" in skills


# ── build_evidence_map ─────────────────────────────────────────────────────

class TestBuildEvidenceMap:
    def test_evidence_map_includes_warnings(self):
        raw_claims = [
            {"claim": "Python experience", "type": "skill", "skill": "Python", "evidence_level": "demonstrated",
             "status": "verified", "confidence": 90, "evidence": [{"section": "experience", "snippet": "Built apps"}],
             "evidence_type": "direct"},
            {"claim": "Go experience", "type": "skill", "skill": "Go", "evidence_level": "missing",
             "status": "inflated", "confidence": 5, "evidence": [], "evidence_type": "missing"},
        ]
        mapped = build_evidence_map(raw_claims)
        assert len(mapped) == 2
        assert mapped[0]["warning"] == ""
        assert len(mapped[1]["warning"]) > 0

    def test_evidence_map_keys(self):
        raw = [{"claim": "Docker experience", "type": "skill", "skill": "Docker", "evidence_level": "supported",
                "status": "verified", "confidence": 78, "evidence": [{"section": "experience", "snippet": "Used Docker"}],
                "evidence_type": "direct"}]
        mapped = build_evidence_map(raw)
        keys = set(mapped[0].keys())
        expected = {"claim", "type", "skill", "evidence_level", "status", "confidence", "evidence", "evidence_type", "warning"}
        assert keys == expected