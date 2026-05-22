"""Tests for backend/signals/fraud_signal.py — risk score, confidence, findings, weak areas."""
from __future__ import annotations

from backend.signals.fraud_signal import (
    aggregate_findings,
    categorize_claims,
    compute_confidence,
    compute_initial_findings,
    compute_risk_score,
    compute_weak_areas,
)


# ── categorize_claims ──────────────────────────────────────────────────────

class TestCategorizeClaims:
    def test_inflated_contains_weak_and_missing(self):
        claims = [
            {"evidence_level": "demonstrated", "status": "verified"},
            {"evidence_level": "weak", "status": "inflated"},
            {"evidence_level": "missing", "status": "inflated"},
            {"evidence_level": "supported", "status": "verified"},
        ]
        inflated, verified = categorize_claims(claims)
        assert len(inflated) == 2
        assert len(verified) == 2

    def test_all_verified(self):
        claims = [
            {"evidence_level": "demonstrated", "status": "verified"},
            {"evidence_level": "supported", "status": "verified"},
        ]
        inflated, verified = categorize_claims(claims)
        assert len(inflated) == 0
        assert len(verified) == 2

    def test_all_inflated(self):
        claims = [
            {"evidence_level": "weak", "status": "inflated"},
            {"evidence_level": "missing", "status": "inflated"},
        ]
        inflated, verified = categorize_claims(claims)
        assert len(inflated) == 2
        assert len(verified) == 0

    def test_claim_can_appear_in_both_lists(self):
        """evidence_level=supported + status=inflated hits both filters."""
        claims = [
            {"evidence_level": "supported", "status": "inflated"},
        ]
        inflated, verified = categorize_claims(claims)
        assert len(inflated) == 1
        assert len(verified) == 1


# ── compute_weak_areas ─────────────────────────────────────────────────────

class TestComputeWeakAreas:
    def test_missing_skills_included(self):
        areas = compute_weak_areas(["Kubernetes", "Docker"], ["built"], [])
        assert any("Missing JD skills" in a for a in areas)

    def test_no_action_verbs_included(self):
        areas = compute_weak_areas([], [], [])
        assert any("action verbs" in a.lower() for a in areas)

    def test_weak_claims_counted(self):
        claims = [{"evidence_level": "weak"}, {"evidence_level": "mentioned"}]
        areas = compute_weak_areas([], ["built"], claims)
        assert any("claim(s)" in a and "light" in a for a in areas)

    def test_no_issues_empty_list(self):
        claims = [{"evidence_level": "demonstrated"}]
        areas = compute_weak_areas([], ["built"], claims)
        assert len(areas) == 0


# ── compute_initial_findings ───────────────────────────────────────────────

class TestComputeInitialFindings:
    def test_missing_skills_finding_medium(self):
        findings = compute_initial_findings(["Docker"], ["built"])
        assert any(f["severity"] == "medium" for f in findings)

    def test_no_action_verbs_medium_severity(self):
        findings = compute_initial_findings([], [])
        assert any("action verbs" in f["message"].lower() for f in findings)

    def test_action_verbs_finding_low_severity(self):
        findings = compute_initial_findings([], ["architected", "deployed"])
        low = [f for f in findings if f["severity"] == "low"]
        assert any("action verbs" in f["message"].lower() for f in low)

    def test_empty_inputs_minimal_findings(self):
        findings = compute_initial_findings([], ["built"])
        # only low severity verb finding, no missing skills
        assert len(findings) >= 1


# ── compute_risk_score ─────────────────────────────────────────────────────

class TestComputeRiskScore:
    def test_low_risk_at_high_compatibility(self):
        score = compute_risk_score(
            compatibility=95,
            inflated_claims=[],
            missing_skills_raw=[],
            action_verbs_list=["built"],
            consistency_findings=[],
            strictness="medium",
            cross_reference_sync=False,
        )
        assert 0 <= score <= 20

    def test_high_risk_with_many_missing_skills(self):
        score = compute_risk_score(
            compatibility=30,
            inflated_claims=[{"type": "skill"}, {"type": "skill"}],
            missing_skills_raw=["K8s", "Docker", "Terraform", "AWS"],
            action_verbs_list=[],
            consistency_findings=[{"status": "missing"}],
            strictness="high",
            cross_reference_sync=True,
        )
        assert score >= 50

    def test_score_clamped_to_100(self):
        score = compute_risk_score(
            compatibility=0,
            inflated_claims=[{"type": "skill"}] * 50,
            missing_skills_raw=["A"] * 50,
            action_verbs_list=[],
            consistency_findings=[{"status": "missing"}] * 10,
            strictness="high",
            cross_reference_sync=True,
        )
        assert score == 100

    def test_score_at_least_zero(self):
        score = compute_risk_score(
            compatibility=100,
            inflated_claims=[],
            missing_skills_raw=[],
            action_verbs_list=["built", "deployed", "tested"],
            consistency_findings=[],
            strictness="low",
            cross_reference_sync=False,
        )
        assert score >= 0


# ── compute_confidence ─────────────────────────────────────────────────────

class TestComputeConfidence:
    def test_high_confidence_with_many_verified_claims(self):
        conf = compute_confidence(
            compatibility=90,
            verified_claims=[{"skill": "A"}, {"skill": "B"}, {"skill": "C"}, {"skill": "D"}],
            inflated_claims=[],
            action_verbs_list=["built", "tested"],
        )
        assert 80 <= conf <= 100

    def test_low_confidence_with_few_verified(self):
        conf = compute_confidence(
            compatibility=20,
            verified_claims=[],
            inflated_claims=[{"skill": "X"}, {"skill": "Y"}, {"skill": "Z"}],
            action_verbs_list=[],
        )
        assert conf <= 40

    def test_confidence_in_0_100_range(self):
        conf = compute_confidence(
            compatibility=50,
            verified_claims=[{"skill": "A"}],
            inflated_claims=[{"skill": "B"}],
            action_verbs_list=["built"],
        )
        assert 0 <= conf <= 100

    def test_confidence_clamped_bottom(self):
        conf = compute_confidence(
            compatibility=0,
            verified_claims=[],
            inflated_claims=[{"skill": "X"}] * 10,
            action_verbs_list=[],
        )
        # Should not go below 0
        assert conf >= 0


# ── aggregate_findings ─────────────────────────────────────────────────────

class TestAggregateFindings:
    def test_fallback_message_added_when_few_findings(self):
        findings = [{"message": "A", "severity": "low"}]
        merged = aggregate_findings(findings, [], needs_fallback_message=True)
        assert len(merged) > 1

    def test_fallback_skipped_when_enough_findings(self):
        findings = [
            {"message": "A", "severity": "low"},
            {"message": "B", "severity": "medium"},
        ]
        merged = aggregate_findings(findings, [], needs_fallback_message=True)
        assert len(merged) == 2  # no new insertion

    def test_buzzword_findings_included(self):
        findings = []
        consistency = [{"status": "buzzword", "claim": "used 'ninja' in resume"}]
        merged = aggregate_findings(findings, consistency, needs_fallback_message=False)
        assert any("ninja" in f["message"] for f in merged)

    def test_missing_consistency_high_severity(self):
        findings = []
        consistency = [{"status": "missing", "claim": "Kubernetes missing"}]
        merged = aggregate_findings(findings, consistency, needs_fallback_message=False)
        high = [f for f in merged if f["severity"] == "high"]
        assert len(high) >= 1

    def test_at_most_8_consistency_findings(self):
        consistency = [{"status": "buzzword", "claim": f"buzzword {i}"} for i in range(20)]
        merged = aggregate_findings([], consistency, needs_fallback_message=False)
        # count buzzword claims added
        buzz_in_merged = sum(1 for f in merged if "buzzword" in f["message"])
        assert buzz_in_merged <= 8