"""Integration tests for the full resume verification pipeline — analyze_resume and response schema."""
from __future__ import annotations

from backend.verification.pipeline import analyze_resume


# ── Strong evidence resume (should produce low risk, high confidence) ──────

STRONG_RESUME = """Experience
Senior Backend Engineer | TechCorp | 2018-2024
• Architected and built scalable microservices using Python and FastAPI, serving 50k+ requests per second.
• Deployed Docker containers to Kubernetes clusters with automated CI/CD pipelines.
• Designed PostgreSQL schemas and optimized queries, reducing latency by 40%.
• Led a team of 5 engineers delivering 3 major platform releases annually.

Projects
• Built a real-time analytics dashboard using React and TypeScript.
• Implemented an event-driven data pipeline with Kafka and Redis.

Skills
Python, FastAPI, Docker, Kubernetes, PostgreSQL, React, TypeScript, Redis, Kafka, CI/CD

Education
MS Computer Science | University 2014-2016
"""

# ── Buzzword-heavy resume (should trigger buzzword detection) ──────────────

BUZZWORD_RESUME = """Summary
Passionate rockstar ninja engineer with cutting-edge expertise and world-class proficiency.

Experience
TechCo | 2020-present
• Expert engineer who built things.
• Ninja-level problem solver with passion for technology.
• Guru of full-stack development.
• Proficient in many cutting edge technologies.

Skills
Python, JavaScript, React, Node.js, AWS
"""

# ── Overlapping timeline (should flag overlaps) ────────────────────────────

OVERLAP_RESUME = """Experience
Company A | 2018-2021
• Built features using Python.
Company B | 2020-2022
• Also worked here while at Company A.
Company C | 2021-2023
• Sequential after overlap period.

Skills
Python, Docker
"""

# ── Resume missing required skills (should produce missing skills) ─────────

MISSING_SKILLS_RESUME = """Experience
DevOps Engineer | Corp | 2019-2022
• Maintained Linux servers and automated deployments.

Skills
Linux, Bash, Jenkins
"""

MISSING_SKILLS_JD = """Requirements:
Must have: Kubernetes, Docker, Terraform, Ansible, Python
"""


# ── Verify response schema ─────────────────────────────────────────────────

class TestVerifyResponseSchema:
    """Verify the endpoint response has all required keys and correct types."""

    def test_response_has_required_keys(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        required = {
            "risk_score", "confidence", "compatibility_score",
            "findings", "claims", "evidence",
            "timeline", "timeline_analysis",
            "skills", "action_verbs",
            "matched_skills", "missing_skills",
            "weak_areas", "strictness",
            "cross_reference_sync", "years_experience",
            "job_description", "job_requirements",
            "consistency_findings", "skill_timeline_insights",
            "resume_sections",
        }
        assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"

    def test_scores_are_integers(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert isinstance(result["risk_score"], int)
        assert isinstance(result["confidence"], int)
        assert isinstance(result["compatibility_score"], int)
        assert 0 <= result["risk_score"] <= 100
        assert 0 <= result["confidence"] <= 100
        assert 0 <= result["compatibility_score"] <= 100

    def test_skills_is_list_of_strings(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert isinstance(result["skills"], list)
        if result["skills"]:
            assert isinstance(result["skills"][0], str)

    def test_findings_have_message_and_severity(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        for f in result["findings"]:
            assert "message" in f
            assert "severity" in f
            assert f["severity"] in ("low", "medium", "high")

    def test_claims_have_required_fields(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        for c in result["claims"]:
            assert "claim" in c
            assert "type" in c
            assert "evidence_level" in c
            assert "status" in c
            assert "confidence" in c

    def test_evidence_map_has_warning_field(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        for e in result["evidence"]:
            assert "warning" in e

    def test_timeline_is_list(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert isinstance(result["timeline"], list)

    def test_timeline_analysis_has_overlaps_gaps(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        ta = result["timeline_analysis"]
        assert isinstance(ta, dict)
        assert "overlaps" in ta
        assert "gaps" in ta

    def test_strictness_default_is_medium(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert result["strictness"] == "medium"

    def test_cross_reference_sync_default_true(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert result["cross_reference_sync"] is True


# ── Score stability ────────────────────────────────────────────────────────

class TestScoreStability:
    """Deterministic results for identical inputs."""

    def test_identical_inputs_produce_identical_outputs(self):
        r1 = analyze_resume(STRONG_RESUME, "", "medium", True)
        r2 = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert r1["risk_score"] == r2["risk_score"]
        assert r1["confidence"] == r2["confidence"]
        assert r1["compatibility_score"] == r2["compatibility_score"]
        assert r1["findings"] == r2["findings"]

    def test_strictness_affects_risk_score(self):
        low = analyze_resume(STRONG_RESUME, "", "low", True)
        high = analyze_resume(STRONG_RESUME, "", "high", True)
        assert low["risk_score"] <= high["risk_score"]

    def test_cross_reference_off_reduces_findings(self):
        on = analyze_resume(STRONG_RESUME, "", "high", True)
        off = analyze_resume(STRONG_RESUME, "", "high", False)
        assert len(off["consistency_findings"]) == 0


# ── Strong evidence resume ─────────────────────────────────────────────────

class TestStrongResume:
    def test_high_compatibility(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert result["compatibility_score"] >= 50
        assert result["confidence"] >= 40

    def test_low_risk(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert result["risk_score"] <= 40

    def test_action_verbs_detected(self):
        result = analyze_resume(STRONG_RESUME, "", "medium", True)
        assert len(result["action_verbs"]) >= 5


# ── Buzzword-heavy resume ──────────────────────────────────────────────────

class TestBuzzwordResume:
    def test_buzzword_findings_included(self):
        result = analyze_resume(BUZZWORD_RESUME, "", "high", True)
        messages = " ".join(f["message"] for f in result["findings"])
        buzzwords_found = [w for w in ["rockstar", "ninja", "guru", "expert", "passionate"] if w in messages.lower()]
        assert len(buzzwords_found) >= 2, f"Expected buzzwords in findings, got: {messages[:200]}"

    def test_claims_are_weak_or_mentioned(self):
        result = analyze_resume(BUZZWORD_RESUME, "", "medium", True)
        skill_claims = [c for c in result["claims"] if c["type"] == "skill"]
        weak_or_below = [c for c in skill_claims if c["evidence_level"] in ("weak", "mentioned", "missing")]
        assert len(weak_or_below) >= len(skill_claims) * 0.5

    def test_consistency_findings_detect_buzzwords(self):
        result = analyze_resume(BUZZWORD_RESUME, "", "high", True)
        buzzword_findings = [f for f in result["consistency_findings"] if f.get("status") == "buzzword"]
        assert len(buzzword_findings) >= 1


# ── Overlapping timeline ───────────────────────────────────────────────────

class TestOverlappingTimeline:
    def test_overlaps_detected(self):
        result = analyze_resume(OVERLAP_RESUME, "", "medium", True)
        ta = result["timeline_analysis"]
        assert len(ta["overlaps"]) > 0

    def test_timeline_entries_extracted(self):
        result = analyze_resume(OVERLAP_RESUME, "", "medium", True)
        assert len(result["timeline"]) >= 2

    def test_gaps_not_reported_for_overlaps(self):
        result = analyze_resume(OVERLAP_RESUME, "", "medium", True)
        ta = result["timeline_analysis"]
        # Overlapping timeline may still have gaps between 2022 and 2023 start
        # but overlaps should be the main finding
        assert len(ta["overlaps"]) >= len(ta["gaps"])


# ── Missing required skills ────────────────────────────────────────────────

class TestMissingSkills:
    def test_missing_skills_populated(self):
        result = analyze_resume(MISSING_SKILLS_RESUME, MISSING_SKILLS_JD, "medium", True)
        assert len(result["missing_skills"]) >= 3
        assert "Docker" in result["missing_skills"] or "Kubernetes" in result["missing_skills"]

    def test_compatibility_lower_with_missing_skills(self):
        with_jd = analyze_resume(MISSING_SKILLS_RESUME, MISSING_SKILLS_JD, "medium", True)
        without_jd = analyze_resume(MISSING_SKILLS_RESUME, "", "medium", True)
        assert with_jd["compatibility_score"] < without_jd["compatibility_score"]

    def test_weak_areas_include_missing_skills(self):
        result = analyze_resume(MISSING_SKILLS_RESUME, MISSING_SKILLS_JD, "medium", True)
        weak = " ".join(result["weak_areas"]).lower()
        assert "missing" in weak

    def test_risk_score_higher_with_jd(self):
        with_jd = analyze_resume(MISSING_SKILLS_RESUME, MISSING_SKILLS_JD, "medium", True)
        without_jd = analyze_resume(MISSING_SKILLS_RESUME, "", "medium", True)
        assert with_jd["risk_score"] >= without_jd["risk_score"]