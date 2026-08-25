"""Validation tests for the V2 AI pipeline foundation (backend/llm/).

Covers schema construction/validation against the shapes validated during
offline pipeline work, and confirms the pipeline stage stubs are typed but
unimplemented (no LLM/API integration exists yet).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.llm import pipeline
from backend.llm.schemas import (
    CandidateProfile,
    EducationEntry,
    ExperienceEntry,
    Explanation,
    JobProfile,
    MatchAnalysis,
    MatchScore,
    ProjectEntry,
    SkillGaps,
)

# Mirrors the shape of the validated candidate-profile fixture produced
# during offline DeepSeek pipeline validation.
SAMPLE_CANDIDATE_PROFILE = {
    "skills": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL"],
    "technologies": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL"],
    "experience": [
        {
            "job_title": "Senior Backend Engineer",
            "company": "TechCorp",
            "start_year": 2018,
            "end_year": 2024,
            "responsibilities": [
                "Architected and built scalable microservices using Python and FastAPI.",
            ],
        }
    ],
    "education": [
        {
            "degree": "MS Computer Science",
            "institution": "University",
            "start_year": 2014,
            "end_year": 2016,
        }
    ],
    "job_titles": ["Senior Backend Engineer"],
    "seniority": "Senior",
    "industries": [],
    "certifications": [],
    "languages": [],
    "projects": [
        {
            "name": "Real-time analytics dashboard",
            "description": "Built a real-time analytics dashboard using React and TypeScript.",
            "technologies_used": ["React", "TypeScript"],
        }
    ],
}

# Mirrors the shape of the validated job-match-score fixture, split into its
# numeric MatchScore half; the recommendation/reason half is Explanation's.
SAMPLE_MATCH_SCORE = {
    "overall_score": 53,
    "skill_score": 83,
    "experience_score": 25,
    "education_score": 100,
    "seniority_score": 10,
    "location_score": 50,
}

SAMPLE_EXPLANATION = {
    "recommendation": "No — the candidate is significantly overqualified for this Junior-level role.",
    "reason": "Candidate is strong on skills and education, but experience/seniority are mismatched.",
    "strengths": ["Skills match all but one required skill"],
    "concerns": ["Seniority and experience far exceed the target range"],
}


def test_candidate_profile_accepts_validated_shape():
    profile = CandidateProfile.model_validate(SAMPLE_CANDIDATE_PROFILE)
    assert profile.seniority == "Senior"
    assert profile.experience[0].job_title == "Senior Backend Engineer"
    assert profile.projects[0].technologies_used == ["React", "TypeScript"]


def test_candidate_profile_defaults_are_empty_lists():
    profile = CandidateProfile()
    assert profile.skills == []
    assert profile.experience == []
    assert profile.seniority is None


def test_job_profile_defaults_and_construction():
    job = JobProfile(
        required_skills=["Python", "FastAPI"],
        min_experience_years=0,
        max_experience_years=2,
        seniority_level="Junior",
    )
    assert job.required_skills == ["Python", "FastAPI"]
    assert job.preferred_skills == []
    assert job.max_experience_years == 2


def test_match_analysis_optional_fields_default_none():
    analysis = MatchAnalysis(matched_skills=["Python"], missing_skills=["Go"])
    assert analysis.matched_skills == ["Python"]
    assert analysis.candidate_experience_years is None
    assert analysis.education_match is None


def test_match_score_accepts_validated_shape():
    score = MatchScore.model_validate(SAMPLE_MATCH_SCORE)
    assert score.overall_score == 53
    assert score.skill_score == 83


@pytest.mark.parametrize("field", ["overall_score", "skill_score", "location_score"])
def test_match_score_rejects_out_of_range(field):
    bad = dict(SAMPLE_MATCH_SCORE)
    bad[field] = 150
    with pytest.raises(ValidationError):
        MatchScore.model_validate(bad)


def test_explanation_accepts_validated_shape():
    explanation = Explanation.model_validate(SAMPLE_EXPLANATION)
    assert explanation.recommendation.startswith("No")
    assert explanation.strengths


def test_explanation_requires_recommendation_and_reason():
    with pytest.raises(ValidationError):
        Explanation()


def test_skill_gaps_construction_and_bounds():
    gaps = SkillGaps(
        missing_required_skills=["Go"],
        coverage_percentage=83.0,
        recommendations=["Highlight Go experience if any."],
    )
    assert gaps.coverage_percentage == 83.0
    with pytest.raises(ValidationError):
        SkillGaps(coverage_percentage=101.0)


# ── Functional pipeline tests ────────────────────────────────────────────────


def test_build_candidate_profile_parses_resume_text():
    """build_candidate_profile should derive skills, experience, education from raw text."""
    resume = (
        "Senior Backend Engineer at TechCorp (2018-2024)\n"
        "- Architected microservices using Python and FastAPI\n"
        "- Managed Docker and Kubernetes deployments\n\n"
        "MS Computer Science, University (2014-2016)\n\n"
        "Skills: Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS"
    )
    profile = pipeline.build_candidate_profile(resume)

    assert profile.seniority == "Senior"
    assert len(profile.skills) > 0
    assert "python" in profile.skills
    assert "docker" in profile.skills
    assert len(profile.experience) >= 1
    assert "Senior" in profile.experience[0].job_title
    assert len(profile.education) >= 1
    assert "ms" in profile.education[0].degree.lower()


def test_build_candidate_profile_empty_text():
    """build_candidate_profile should return an empty profile for empty input."""
    profile = pipeline.build_candidate_profile("")
    assert profile.skills == []
    assert profile.experience == []
    assert profile.seniority is None


def test_build_job_profile_parses_description():
    """build_job_profile should extract requirements from job description text."""
    jd = (
        "Job Title: Junior Python Developer\n"
        "Location: New York, NY\n"
        "Requirements: 2+ years experience with Python and FastAPI.\n"
        "Bachelor degree required.\n"
        "Remote allowed."
    )
    profile = pipeline.build_job_profile(jd)

    assert len(profile.required_skills) > 0
    assert "python" in profile.required_skills
    assert profile.min_experience_years == 2.0
    assert profile.education_requirement is not None
    assert "bachelor" in profile.education_requirement.lower()
    assert profile.location == "New York, NY"
    assert profile.remote_allowed is True


def test_build_job_profile_empty_text():
    """build_job_profile should return an empty profile for empty input."""
    profile = pipeline.build_job_profile("")
    assert profile.required_skills == []
    assert profile.min_experience_years is None
def test_analyze_match_identifies_skill_gaps():
    """analyze_match should correctly identify matched and missing skills."""
    candidate = CandidateProfile(
        skills=["Python", "FastAPI", "Docker"],
        technologies=["Python", "FastAPI", "Docker"],
        experience=[],
    )
    job = JobProfile(
        required_skills=["Python", "Go", "Kubernetes"],
        required_technologies=["Python", "Go"],
    )
    analysis = pipeline.analyze_match(candidate, job)

    assert "python" in analysis.matched_skills
    assert "go" in analysis.missing_skills
    assert "kubernetes" in analysis.missing_skills
    assert "docker" in analysis.additional_skills
    assert analysis.candidate_experience_years == 0


def test_analyze_match_experience_calculation():
    """analyze_match should calculate total experience years from entries."""
    candidate = CandidateProfile(
        skills=[],
        experience=[
            ExperienceEntry(
                job_title="Engineer", company="A",
                start_year=2018, end_year=2020,
            ),
            ExperienceEntry(
                job_title="Senior Engineer", company="B",
                start_year=2020, end_year=2024,
            ),
        ],
    )
    job = JobProfile(
        required_skills=[],
        min_experience_years=5.0,
    )
    analysis = pipeline.analyze_match(candidate, job)

    assert analysis.candidate_experience_years == 6
    assert analysis.experience_gap_years is None


def test_compute_match_score_from_analysis():
    """compute_match_score should produce scores in 0-100 range."""
    analysis = MatchAnalysis(
        matched_skills=["python", "fastapi"],
        missing_skills=["go"],
        candidate_experience_years=3.0,
        education_match=True,
        seniority_match=True,
        location_match=False,
    )
    score = pipeline.compute_match_score(analysis)

    assert 0 <= score.overall_score <= 100
    assert 0 <= score.skill_score <= 100
    assert 0 <= score.experience_score <= 100
    assert 0 <= score.education_score <= 100
    assert 0 <= score.seniority_score <= 100
    assert 0 <= score.location_score <= 100
    assert score.skill_score == 67
    assert score.education_score == 100
    assert score.location_score == 0


def test_compute_match_score_empty_analysis():
    """compute_match_score should handle empty analysis gracefully."""
    score = pipeline.compute_match_score(MatchAnalysis())
    # weighted: 0.35*100 + 0.25*0 + 0.15*50 + 0.15*50 + 0.10*50 = 55
    assert score.overall_score == 55


def test_generate_explanation_produces_narrative():
    """generate_explanation should produce a plausible Explanation."""
    analysis = MatchAnalysis(
        matched_skills=["Python"],
        missing_skills=["Go"],
        candidate_experience_years=5.0,
        education_match=True,
        seniority_match=True,
    )
    score = MatchScore(
        overall_score=75,
        skill_score=50,
        experience_score=100,
        education_score=100,
        seniority_score=100,
        location_score=50,
    )
    explanation = pipeline.generate_explanation(analysis, score)

    assert explanation.recommendation
    assert explanation.reason
    assert isinstance(explanation.strengths, list)
    assert isinstance(explanation.concerns, list)
    assert "Maybe" in explanation.recommendation


def test_generate_explanation_low_score():
    """generate_explanation should recommend 'No' for very low scores."""
    analysis = MatchAnalysis(
        missing_skills=["Python", "Go", "Kubernetes"],
        candidate_experience_years=0.0,
        education_match=False,
        seniority_match=False,
    )
    score = MatchScore(
        overall_score=15,
        skill_score=0,
        experience_score=0,
        education_score=0,
        seniority_score=0,
        location_score=50,
    )
    explanation = pipeline.generate_explanation(analysis, score)

    assert explanation.recommendation.startswith("No")


def test_compute_skill_gaps_identifies_missing():
    """compute_skill_gaps should find missing and additional skills."""
    candidate = CandidateProfile(
        skills=["Python", "FastAPI", "Docker", "AWS"],
    )
    job = JobProfile(
        required_skills=["Python", "Go", "Kubernetes"],
        preferred_skills=["Redis"],
    )
    gaps = pipeline.compute_skill_gaps(candidate, job)

    assert "go" in gaps.missing_required_skills
    assert "kubernetes" in gaps.missing_required_skills
    assert "redis" in gaps.missing_preferred_skills
    assert "docker" in gaps.additional_skills
    assert "aws" in gaps.additional_skills
    assert gaps.coverage_percentage == 25.0
    assert len(gaps.recommendations) > 0


def test_compute_skill_gaps_full_coverage():
    """compute_skill_gaps should report 100% coverage when all skills match."""
    candidate = CandidateProfile(
        skills=["Python", "Go"],
    )
    job = JobProfile(
        required_skills=["Python", "Go"],
    )
    gaps = pipeline.compute_skill_gaps(candidate, job)

    assert gaps.missing_required_skills == []
    assert gaps.coverage_percentage == 100.0
    assert any("no gaps" in rec.lower() for rec in gaps.recommendations)
