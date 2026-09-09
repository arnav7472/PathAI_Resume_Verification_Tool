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
    """compute_match_score should handle empty analysis gracefully with neutral unknowns."""
    score = pipeline.compute_match_score(MatchAnalysis())
    # All components unknown: skill=100 (no required skills), exp=50 (neutral),
    # edu=50 (neutral), sen=50 (neutral), loc=50 (neutral).
    # weighted: 0.35*100 + 0.25*50 + 0.15*50 + 0.15*50 + 0.10*50 = 67.5 -> 68
    assert score.overall_score == 68
    assert score.experience_score == 50  # unknown -> neutral, not mismatch


# ── Deterministic scoring calibration: 6 minimal candidate/job scenarios ──────


_EXPECTED_WEIGHTS = (0.35, 0.25, 0.15, 0.15, 0.10)


def _expected_overall(skill, experience, education, seniority, location):
    """Recompute the weighted overall score exactly as compute_match_score does."""
    return round(
        _EXPECTED_WEIGHTS[0] * skill
        + _EXPECTED_WEIGHTS[1] * experience
        + _EXPECTED_WEIGHTS[2] * education
        + _EXPECTED_WEIGHTS[3] * seniority
        + _EXPECTED_WEIGHTS[4] * location
    )


def test_scoring_excellent_match():
    """Scenario 1: candidate hits every requirement -> near-perfect score, 'Yes'."""
    job = JobProfile(
        required_skills=["Python", "FastAPI", "Docker", "Go"],
        preferred_skills=["Redis"],
        min_experience_years=3,
        education_requirement="Bachelor's degree in Computer Science",
        seniority_level="Senior",
    )
    candidate = CandidateProfile(
        skills=["Python", "FastAPI", "Docker", "Go", "Redis"],
        seniority="Senior",
        experience=[ExperienceEntry(job_title="Sr Eng", company="C", start_year=2018, end_year=2024)],
        education=[EducationEntry(degree="BS in Computer Science", institution="Uni")],
    )

    analysis = pipeline.analyze_match(candidate, job)
    score = pipeline.compute_match_score(analysis)
    explanation = pipeline.generate_explanation(analysis, score)

    assert analysis.missing_skills == [] and analysis.education_match is True
    assert score.skill_score == 100
    assert score.experience_score == 100
    assert score.education_score == 100
    assert score.seniority_score == 100
    assert score.location_score == 50  # location unknown -> neutral
    assert score.overall_score == _expected_overall(100, 100, 100, 100, 50) == 95
    assert explanation.recommendation.startswith("Yes")
    assert explanation.concerns == []


def test_scoring_strong_match_with_minor_skill_gap():
    """Scenario 2: strong candidate missing only one skill -> high but not perfect skill score."""
    job = JobProfile(
        required_skills=["Python", "FastAPI", "Docker", "Go"],
        preferred_skills=["Redis"],
        min_experience_years=3,
        education_requirement="Bachelor's degree in Computer Science",
        seniority_level="Senior",
    )
    candidate = CandidateProfile(
        skills=["Python", "FastAPI", "Docker", "Go"],  # missing preferred: Redis
        seniority="Senior",
        experience=[ExperienceEntry(job_title="Sr Eng", company="C", start_year=2018, end_year=2023)],
        education=[EducationEntry(degree="BS in Computer Science", institution="Uni")],
    )

    analysis = pipeline.analyze_match(candidate, job)
    score = pipeline.compute_match_score(analysis)
    explanation = pipeline.generate_explanation(analysis, score)

    # 4 of 5 job skills matched -> 80, i.e. the missing skill pulls the score below 100.
    assert analysis.matched_skills == ["docker", "fastapi", "go", "python"]
    assert analysis.missing_skills == ["redis"]
    assert score.skill_score == 80
    assert score.experience_score == 100  # meets 3y minimum -> full credit
    assert score.education_score == 100
    assert score.seniority_score == 100
    assert score.overall_score == _expected_overall(80, 100, 100, 100, 50) == 88
    assert explanation.recommendation.startswith("Yes")
    assert "redis" in explanation.concerns[0]
def test_scoring_moderate_match():
    """Scenario 3: partial skills, experience shortfall, seniority mismatch -> mid score."""
    job = JobProfile(
        required_skills=["Python", "FastAPI", "Docker", "Kubernetes", "Go"],
        preferred_skills=["Redis"],
        min_experience_years=5,
        education_requirement="Bachelor's degree in Computer Science",
        seniority_level="Senior",
    )
    candidate = CandidateProfile(
        skills=["Python", "FastAPI", "Docker"],
        seniority="Mid",  # mismatch vs Senior
        experience=[ExperienceEntry(job_title="Eng", company="C", start_year=2020, end_year=2023)],
        education=[EducationEntry(degree="BS in Computer Science", institution="Uni")],
    )

    analysis = pipeline.analyze_match(candidate, job)
    score = pipeline.compute_match_score(analysis)
    explanation = pipeline.generate_explanation(analysis, score)

    assert score.skill_score == 50          # 3 of 6 skills
    assert score.experience_score == 60     # 3y vs required 5y -> shortfall 2y -> 100-40
    assert analysis.experience_gap_years == 2.0
    assert score.education_score == 100
    assert score.seniority_score == 0
    assert score.overall_score == _expected_overall(50, 60, 100, 0, 50) == 52
    assert explanation.recommendation.startswith("Cautious")


def test_scoring_weak_match():
    """Scenario 4: no skills, huge experience shortfall, failed education/seniority -> very low."""
    job = JobProfile(
        required_skills=["Python", "FastAPI", "Go"],
        min_experience_years=5,
        education_requirement="Bachelor's degree in Computer Science",
        seniority_level="Senior",
    )
    candidate = CandidateProfile(
        skills=[],
        seniority="Junior",
        experience=[ExperienceEntry(job_title="Jnr", company="C", start_year=2022, end_year=2023)],
        education=[EducationEntry(degree="High School Diploma", institution="HS")],
    )

    analysis = pipeline.analyze_match(candidate, job)
    score = pipeline.compute_match_score(analysis)
    explanation = pipeline.generate_explanation(analysis, score)

    assert score.skill_score == 0
    assert score.experience_score == 20  # 1y vs 5y -> shortfall 4y -> 100-80
    assert score.education_score == 0
    assert score.seniority_score == 0
    assert score.overall_score == _expected_overall(0, 20, 0, 0, 50) == 10
    assert explanation.recommendation.startswith("No")
def test_scoring_missing_required_education_and_experience():
    """Scenario 5: required education/experience are missing -> component scores drop hard."""
    job = JobProfile(
        required_skills=["Python"],
        min_experience_years=3,
        education_requirement="Bachelor's degree in Computer Science",
        seniority_level="Senior",
    )
    candidate = CandidateProfile(
        skills=["Python"],
        seniority="Senior",
        experience=[ExperienceEntry(job_title="Eng", company="C", start_year=2022, end_year=2023)],
        education=[EducationEntry(degree="High School Diploma", institution="HS")],
    )

    analysis = pipeline.analyze_match(candidate, job)
    score = pipeline.compute_match_score(analysis)
    explanation = pipeline.generate_explanation(analysis, score)

    assert score.skill_score == 100
    assert score.experience_score == 60     # 1y vs 3y -> shortfall 2y -> 100-40
    assert score.education_score == 0       # missing required education
    assert score.seniority_score == 100
    assert score.overall_score == _expected_overall(100, 60, 0, 100, 50) == 70
    assert explanation.recommendation.startswith("Maybe")
    assert any("education requirement" in c for c in explanation.concerns)
    assert any("Below minimum experience requirement" in c for c in explanation.concerns)


def test_scoring_unknown_optional_information_is_neutral():
    """Scenario 6: unknown optionals (location/education/seniority) must be neutral, not mismatches."""
    job = JobProfile(required_skills=["Python"], location="Berlin")
    candidate = CandidateProfile(
        skills=["Python"],  # no education, no seniority, no experience — all unknown
    )

    analysis = pipeline.analyze_match(candidate, job)
    score = pipeline.compute_match_score(analysis)
    explanation = pipeline.generate_explanation(analysis, score)

    # Candidate has no location field -> match is unknown, NOT a mismatch.
    assert analysis.location_match is None
    assert score.location_score == 50
    # Unknown education / seniority are also neutral, never 0.
    assert analysis.education_match is None and score.education_score == 50
    assert analysis.seniority_match is None and score.seniority_score == 50
    assert score.skill_score == 100
    assert score.overall_score == _expected_overall(100, 100, 50, 50, 50) == 80
    assert explanation.recommendation.startswith("Yes")
    assert not any("location" in c.lower() for c in explanation.concerns)
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
# ── Regression tests for V2 deterministic extraction fixes ──────────────────


def test_pipe_delimited_experience() -> None:
    """Fix 1: Pipe-delimited 'Job Title | Company | 2018-2024' -> correct title, company, dates."""
    text = "Experience\nSenior Backend Engineer | TechCorp | 2018-2024\nSkills\nPython, Docker\n"
    profile = pipeline.build_candidate_profile(text)
    assert len(profile.experience) == 1
    exp = profile.experience[0]
    assert exp.job_title == "Senior Backend Engineer"
    assert exp.company == "TechCorp"
    assert exp.start_year == 2018
    assert exp.end_year == 2024


def test_pipe_delimited_experience_current() -> None:
    """Pipe-delimited with 'present' as end -> end_year=None."""
    text = "Experience\nBackend Engineer | StartupCo | 2021-present\nSkills\nPython\n"
    profile = pipeline.build_candidate_profile(text)
    assert len(profile.experience) == 1
    exp = profile.experience[0]
    assert exp.job_title == "Backend Engineer"
    assert exp.company == "StartupCo"
    assert exp.start_year == 2021
    assert exp.end_year is None


def test_pipe_delimited_education() -> None:
    """Fix 2: Pipe-delimited 'Degree | Institution | 2014-2016' -> correct degree, institution, dates."""
    text = "Education\nMS Computer Science | University | 2014-2016\n"
    profile = pipeline.build_candidate_profile(text)
    assert len(profile.education) == 1
    edu = profile.education[0]
    assert edu.degree == "MS Computer Science"
    assert edu.institution == "University"
    assert edu.start_year == 2014
    assert edu.end_year == 2016
def test_pipe_delimited_education_no_pipe_before_years() -> None:
    """Fix 2 variant: 'Degree | Institution 2014-2016' (no pipe before years) must parse."""
    text = "Education\nMS Computer Science | University 2014-2016\n"
    profile = pipeline.build_candidate_profile(text)
    assert len(profile.education) == 1
    edu = profile.education[0]
    assert edu.degree == "MS Computer Science"
    assert edu.institution == "University"
    assert edu.start_year == 2014
    assert edu.end_year == 2016


def test_extract_projects_from_section() -> None:
    """Fix 3: Bullet points under a 'Projects' section header become project entries."""
    text = (
        "Experience\nSenior Engineer | Corp | 2020-2023\n\n"
        "Projects\n- Built a real-time analytics dashboard using React and TypeScript.\n"
        "- Implemented an event-driven pipeline with Kafka.\n\n"
        "Skills\nPython, FastAPI\n"
    )
    profile = pipeline.build_candidate_profile(text)
    assert len(profile.projects) >= 2
    names = [p.name for p in profile.projects]
    assert any("analytics dashboard" in n for n in names)
    assert any("event-driven pipeline" in n for n in names)


def test_skill_extraction_word_boundary_filters_false_positives() -> None:
    """Fix 4: 'R', 'Scala', 'SQL', 'API' must not match as substrings of other words."""
    text = (
        "Experience\nSenior Backend Engineer | TechCorp | 2018-2024\n"
        "- Architected scalable microservices with PostgreSQL and FastAPI.\n"
        "- Coordinated cross-team integration of the new platform.\n\n"
        "Skills\nPython, TypeScript, Docker\n"
    )
    profile = pipeline.build_candidate_profile(text)
    skills: list[str] = [s.lower() for s in profile.skills]
    # False positives the word-boundary fix must eliminate:
    assert "r" not in skills, "R should not match inside words like 'Senior'"
    assert "scala" not in skills, "scala should not match inside 'scalable'"
    assert "sql" not in skills, "sql should not match inside 'PostgreSQL'"
    assert "api" not in skills, "api should not match inside 'FastAPI'"
    # Legitimate skills that must still be found:
    assert "python" in skills
    assert "typescript" in skills
    assert "docker" in skills
    assert "fastapi" in skills
def test_extract_preferred_skills_from_jd() -> None:
    """Fix 5: 'Nice to have' / 'Preferred' sections in JD should populate preferred_skills."""
    jd = (
        "Requirements:\nMust have Python, Docker, Kubernetes.\n\n"
        "Nice to have:\nExperience with Redis, Kafka, and PostgreSQL.\n\n"
        "Preferred qualifications:\nFamiliarity with AWS and CI/CD pipelines.\n"
    )
    profile = pipeline.build_job_profile(jd)
    assert len(profile.preferred_skills) > 0
    pref: list[str] = [s.lower() for s in profile.preferred_skills]
    assert "redis" in pref
    assert "kafka" in pref
    assert "postgresql" in pref
    assert "aws" in pref


def test_candidate_location_null_when_unknown() -> None:
    """Fix 6: Unknown candidate location -> location_match is None, not False/mismatch."""
    candidate = CandidateProfile(
        skills=["Python"],
        experience=[ExperienceEntry(job_title="Dev", company="Co", start_year=2020, end_year=2023)],
    )
    job = JobProfile(required_skills=["Python"], location="New York, NY")
    analysis = pipeline.analyze_match(candidate, job)
    assert analysis.location_match is None, "Must be None when candidate location is unknown"
    assert analysis.location_match is not False


def test_experience_years_calculated_from_parsed_dates() -> None:
    """Fix 7: Experience-year calculation must use actual parsed employment dates."""
    text = (
        "Experience\nSenior Backend Engineer | TechCorp | 2018-2024\n- First role.\n\n"
        "Junior Dev | OtherCo | 2016-2018\n- Second role.\n"
    )
    profile = pipeline.build_candidate_profile(text)
    assert len(profile.experience) == 2
    total = 0
    for exp in profile.experience:
        end = exp.end_year if exp.end_year else 2025
        total += end - exp.start_year
    assert total == 8, f"Expected 8 total years of experience, got {total}"

    job = JobProfile(required_skills=["Python"])
    analysis = pipeline.analyze_match(profile, job)
    assert analysis.candidate_experience_years == 8.0


def test_explanation_no_spacing_artefacts() -> None:
    """Fix 8: Explanation reason must not have malformed spacing like '8 yearsof'."""
    analysis = MatchAnalysis(
        matched_skills=["Python"],
        missing_skills=["Go"],
        candidate_experience_years=8.0,
        education_match=True,
        seniority_match=True,
        location_match=True,
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
    reason = explanation.reason
    assert "years of experience" in reason, f"Expected proper spacing, got: {reason}"
    assert "yearsof" not in reason, f"Found 'yearsof' without space: {reason}"
    assert "year  of" not in reason, f"Found double space: {reason}"
    assert "\u2014" in explanation.recommendation or "the candidate" in explanation.recommendation
# ── Edge-case regression tests (V2 deterministic audit) ──────────────────────


def test_skill_extraction_matches_special_char_skills() -> None:
    """Edge 1: c++ / c# must be detected despite non-word chars after the name."""
    text = (
        "Experience\nSoftware Engineer | Corp | 2020-2023\n"
        "- Built a trading engine in C++ with real-time C# tooling and Python glue.\n"
    )
    profile = pipeline.build_candidate_profile(text)
    skills: list[str] = [s.lower() for s in profile.skills]
    assert "c++" in skills, f"c++ must be extracted, got: {skills}"
    assert "c#" in skills, f"c# must be extracted, got: {skills}"
    # Word-boundary behaviour for ordinary words must still hold:
    assert "api" not in skills, "api should still not match inside FastAPI"


def test_education_match_phd_and_multiword_requirements() -> None:
    """Edge 2: PhD / 'A bachelor's degree' requirements must match candidate levels."""
    candidate = CandidateProfile(
        skills=["Python"],
        education=[
            EducationEntry(degree="PhD in Computer Science", institution="Uni",
                           start_year=2014, end_year=2018),
        ],
    )
    job = JobProfile(required_skills=["Python"], education_requirement="PhD degree")
    analysis = pipeline.analyze_match(candidate, job)
    assert analysis.education_match is True, "PhD requirement should match PhD candidate"

    bachelor = CandidateProfile(
        skills=["Python"],
        education=[
            EducationEntry(degree="Bachelor of Science in Maths", institution="Uni"),
        ],
    )
    jd_job = JobProfile(
        required_skills=["Python"],
        education_requirement="A bachelor's degree or equivalent experience",
    )
    analysis2 = pipeline.analyze_match(bachelor, jd_job)
    assert analysis2.education_match is True, "'A bachelor's degree' must match a BSc"


def test_experience_parses_title_at_company_line() -> None:
    """Edge 3: 'Job Title at Company (years)' splits title and company, not next line."""
    text = "Experience\nSenior Backend Engineer at TechCorp (2020-2024)\n- Built APIs.\n"
    profile = pipeline.build_candidate_profile(text)
    assert len(profile.experience) == 1
    exp = profile.experience[0]
    assert exp.job_title == "Senior Backend Engineer", f"got: {exp.job_title!r}"
    assert exp.company == "TechCorp", f"got: {exp.company!r}"
    assert exp.start_year == 2020
    assert exp.end_year == 2024
    assert exp.responsibilities == ["- Built APIs."]


def test_job_location_parses_based_in_phrase() -> None:
    """Edge 4: 'based in <city>' / 'based out of <city>' must populate location."""
    jd = "Remote-first team, but candidate must be based in New York, NY.\nPython required.\n"
    profile = pipeline.build_job_profile(jd)
    assert profile.location == "New York, NY", f"got: {profile.location!r}"

    jd2 = "Must be based out of Munich.\nJava required.\n"
    profile2 = pipeline.build_job_profile(jd2)
    assert profile2.location == "Munich", f"got: {profile2.location!r}"


def test_job_preferred_skills_accumulate_across_sections() -> None:
    """Edge 5: skills from both 'Nice to have' and 'Preferred' sections must all appear."""
    job = JobProfile(
        required_skills=["Python", "Go"],
        seniority_level="Mid",
        min_experience_years=2.0,
        max_experience_years=2.0,
    )
    jd = (
        "Requirements:\nMust have Python and Go.\n\n"
        "Nice to have:\nExperience with Redis and Kafka.\n\n"
        "Preferred qualifications:\nFamiliarity with AWS and Terraform.\n"
    )
    profile = pipeline.build_job_profile(jd)
    pref: set[str] = {s.lower() for s in profile.preferred_skills}
    assert "redis" in pref, "Redis from 'Nice to have' must be kept"
    assert "kafka" in pref, "Kafka from 'Nice to have' must be kept"
    assert "aws" in pref, "AWS from 'Preferred qualifications' must be kept"
    assert "terraform" in pref, "Terraform from 'Preferred qualifications' must be kept"
# ── Compact fixture-based tests (V2 deterministic pipeline) ──────────────────


def test_resume_standard_sections() -> None:
    """Resume 1: Standard resume with clear sections -> all structured fields populated."""
    resume = """Summary
Passionate software engineer with 5 years of experience.

Skills
Python, FastAPI, Docker, PostgreSQL, AWS

Experience
Senior Backend Engineer at TechCorp (2020-2024)
- Architected microservices using Python and FastAPI.
- Managed Docker and Kubernetes deployments.
- Designed PostgreSQL database schemas.

Education
MS Computer Science, University of Technology (2016-2018)
BS Computer Science, State University (2012-2016)

Projects
Real-time Analytics Dashboard: Built with React and TypeScript.
CI/CD Pipeline Automation using GitHub Actions and Terraform.
"""
    profile = pipeline.build_candidate_profile(resume)
    skills = [s.lower() for s in profile.skills]
    assert "python" in skills
    assert "fastapi" in skills
    assert "docker" in skills
    assert "postgresql" in skills
    assert "aws" in skills
    assert len(profile.experience) >= 1
    titles = [e.job_title for e in profile.experience]
    assert any("senior" in t.lower() for t in titles)
    assert len(profile.education) >= 2
    degrees = [e.degree.lower() for e in profile.education]
    assert any("ms" in d or "master" in d for d in degrees)
    assert any("bs" in d or "bachelor" in d for d in degrees)
    assert profile.seniority == "Senior"
    assert len(profile.projects) > 0
    assert any("dashboard" in p.name.lower() for p in profile.projects)


def test_resume_pipe_delimited_full() -> None:
    """Resume 2: Full pipe-delimited resume (experience + education)."""
    resume = """Skills: Python, Go, Rust, Docker

Experience
Senior Backend Engineer | TechCorp | 2018-2024
Junior Dev | OtherCo | 2016-2018

Education
MS Computer Science | University of Technology | 2014-2016
BS Computer Science | State University | 2010-2014
"""
    profile = pipeline.build_candidate_profile(resume)
    assert len(profile.experience) == 2
    e0 = profile.experience[0]
    assert e0.job_title == "Senior Backend Engineer"
    assert e0.company == "TechCorp"
    assert e0.start_year == 2018
    assert e0.end_year == 2024
    e1 = profile.experience[1]
    assert e1.job_title == "Junior Dev"
    assert e1.company == "OtherCo"
    assert e1.start_year == 2016
    assert e1.end_year == 2018
    assert len(profile.education) == 2
    assert any("ms" in e.degree.lower() for e in profile.education)
    assert any("bs" in e.degree.lower() for e in profile.education)
    assert profile.seniority == "Senior"
    skills = [s.lower() for s in profile.skills]
    assert "python" in skills
    assert "go" in skills
    assert "rust" in skills
    assert "docker" in skills
def test_resume_bullets_and_multiline_projects() -> None:
    """Resume 3: Bullet items and multi-line project entries."""
    resume = """Skills: Python, TypeScript, React, Node.js

Experience
Software Engineer | StartupCo | 2021-present
- Built REST APIs with Node.js and Express.
- Developed React frontend components.

Projects
- Task Management App: Full-stack app with React and Node.js.
- CLI Tool for Data Processing: Python script for ETL pipelines.
- Portfolio Website: Personal site built with TypeScript.
"""
    profile = pipeline.build_candidate_profile(resume)
    skills = [s.lower() for s in profile.skills]
    assert "python" in skills
    assert "typescript" in skills
    assert "react" in skills
    assert "node.js" in skills
    assert len(profile.experience) == 1
    assert profile.experience[0].job_title == "Software Engineer"
    assert profile.experience[0].company == "StartupCo"
    assert profile.experience[0].start_year == 2021
    assert profile.experience[0].end_year is None
    assert len(profile.projects) >= 2
    project_names = [p.name.lower() for p in profile.projects]
    assert any("task management" in n for n in project_names)


def test_resume_no_location() -> None:
    """Resume 4: No location in resume -> location_match is None when matched."""
    resume = """Skills: Python, Docker

Experience
Developer | Company | 2020-2023

Education
BS Computer Science | University | 2016-2020
"""
    profile = pipeline.build_candidate_profile(resume)
    assert len(profile.skills) > 0
    assert len(profile.experience) == 1
    assert len(profile.education) == 1
    job = JobProfile(
        required_skills=["Python"],
        location="New York, NY",
    )
    analysis = pipeline.analyze_match(profile, job)
    assert analysis.location_match is None, "candidate has no location -> None"


def test_resume_short_ambiguous_skills() -> None:
    """Resume 5: c++, c#, R, Go, and other short/ambiguous skills must be extracted."""
    resume = """Skills: C++, C#, R, Go, Rust, SQL

Experience
Software Engineer | Corp | 2020-2023
- Built trading engine in C++ with real-time C# tooling.
- Used R for statistical analysis and Go for backend services.
"""
    profile = pipeline.build_candidate_profile(resume)
    skills = [s.lower() for s in profile.skills]
    assert "c++" in skills, f"c++ missing from {skills}"
    assert "c#" in skills, f"c# missing from {skills}"
    assert "r" in skills, f"R (language) missing from {skills}"
    assert "go" in skills, f"Go missing from {skills}"
    assert "rust" in skills, f"Rust missing from {skills}"
    assert "sql" in skills, f"SQL missing from {skills}"


def test_resume_overlapping_dates() -> None:
    """Resume 6: Multiple jobs with overlapping dates -> years calculated correctly."""
    resume = """Skills: Python, AWS

Experience
Senior Engineer | Company A | 2020-2024
Tech Lead | Company B | 2022-2025
Consultant | Company C | 2023-present

Education
BS CS | University | 2016-2020
"""
    profile = pipeline.build_candidate_profile(resume)
    assert len(profile.experience) >= 2
    total = 0
    for exp in profile.experience:
        end = exp.end_year if exp.end_year else 2025
        total += end - exp.start_year
    assert total >= 6
    job = JobProfile(required_skills=["Python"], min_experience_years=5.0)
    analysis = pipeline.analyze_match(profile, job)
    assert analysis.candidate_experience_years is not None
    assert analysis.candidate_experience_years >= 5.0


def test_jd_required_and_preferred_skills() -> None:
    """JD 7: JD with required + preferred skills from different sections."""
    jd = """Job Title: Senior Python Developer

Requirements:
- 5+ years experience with Python and FastAPI.
- Must have Docker, Kubernetes, and PostgreSQL.

Nice to have:
- Experience with Redis, Kafka, and MongoDB.

Preferred qualifications:
- Familiarity with AWS, Terraform, and CI/CD pipelines.

Location: San Francisco, CA
"""
    profile = pipeline.build_job_profile(jd)
    req = [s.lower() for s in profile.required_skills]
    assert "python" in req
    assert "fastapi" in req
    assert "docker" in req
    assert "kubernetes" in req
    assert "postgresql" in req
    pref = [s.lower() for s in profile.preferred_skills]
    assert "redis" in pref
    assert "kafka" in pref
    assert "mongodb" in pref
    assert "aws" in pref
    assert "terraform" in pref
    assert "ci/cd" in pref
    assert profile.location == "San Francisco, CA"
    assert profile.min_experience_years == 5.0


def test_jd_bachelor_or_master_education() -> None:
    """JD 8: 'Bachelor's or Master's' education requirement matches either level."""
    jd = "Requirements: Bachelor's or Master's degree in Computer Science. 3+ years of Python."
    job = pipeline.build_job_profile(jd)
    assert job.education_requirement is not None
    assert "bachelor" in job.education_requirement.lower()
    assert "master" in job.education_requirement.lower()

    bachelor = CandidateProfile(
        skills=["Python"],
        education=[EducationEntry(degree="Bachelor of Science in CS", institution="Uni")],
        experience=[ExperienceEntry(job_title="Dev", company="Co", start_year=2020, end_year=2023)],
    )
    analysis_b = pipeline.analyze_match(bachelor, job)
    assert analysis_b.education_match is True, "Bachelor's must match"

    master = CandidateProfile(
        skills=["Python"],
        education=[EducationEntry(degree="Master of Science in CS", institution="Uni")],
        experience=[ExperienceEntry(job_title="Dev", company="Co", start_year=2020, end_year=2023)],
    )
    analysis_m = pipeline.analyze_match(master, job)
    assert analysis_m.education_match is True, "Master's must match 'Bachelor's or Master's' requirement"


def test_jd_based_in_location() -> None:
    """JD 9: 'based in <city>' / 'based out of <city>' location wording."""
    jd = """Senior Data Scientist

We're a remote-first team, but you must be based in Berlin.
Requirements: 3+ years Python, machine learning, and PyTorch.
"""
    profile = pipeline.build_job_profile(jd)
    assert profile.location == "Berlin", f"got: {profile.location!r}"
    assert "python" in [s.lower() for s in profile.required_skills]
    assert "machine learning" in [s.lower() for s in profile.required_skills]
    assert "pytorch" in [s.lower() for s in profile.required_skills]
    assert profile.min_experience_years == 3.0
    assert profile.remote_allowed is True


def test_jd_missing_optional_requirements() -> None:
    """JD 10: JD with no preferred skills, no location, no education -> empty/null optionals."""
    jd = """Junior Python Developer

Requirements:
- 1+ years experience with Python.
- Familiarity with Flask or Django.
"""
    profile = pipeline.build_job_profile(jd)
    assert "python" in [s.lower() for s in profile.required_skills]
    assert any(s in [s.lower() for s in profile.required_skills] for s in ["flask", "django"])
    assert profile.min_experience_years == 1.0
    assert profile.preferred_skills == [], f"got: {profile.preferred_skills}"
    assert profile.location is None, f"got: {profile.location!r}"
    assert profile.education_requirement is None
    assert profile.certifications_required == []
    assert profile.languages_required == []
# ── Security regression tests (Claude security audit) ─────────────────────────


def test_regression_skill_in_skills_section_matched() -> None:
    """Skill listed under a Skills section must be extracted at full strength."""
    resume = """Skills
Python, Docker

Experience
Software Engineer | Corp | 2020-2023
"""
    profile = pipeline.build_candidate_profile(resume)
    skills = [s.lower() for s in profile.skills]
    assert "python" in skills, f"python missing: {skills}"
    assert "docker" in skills, f"docker missing: {skills}"


def test_regression_skill_in_experience_matched() -> None:
    """Skill used legitimately inside an Experience entry must be extracted."""
    resume = """Experience
Software Engineer | Corp | 2020-2023
- Built async services in Python and deployed them with Docker.
"""
    profile = pipeline.build_candidate_profile(resume)
    skills = [s.lower() for s in profile.skills]
    assert "python" in skills, f"python missing: {skills}"
    assert "docker" in skills, f"docker missing: {skills}"


def test_regression_skill_dump_in_unrelated_prose_not_full_strength() -> None:
    """A keyword dump in an unrelated section must not count as evidence.

    The legitimate skill context (Experience) is kept; the unrelated dump
    (Interests) is not treated as equivalent evidence for the skill score.
    """
    resume = """Experience
Junior Developer | Acme | 2021-2024
- Built internal tooling with Python and Git.

Interests
Docker, Kubernetes, AWS, Terraform, SQL, PostgreSQL, React, TypeScript
"""
    profile = pipeline.build_candidate_profile(resume)
    skills = [s.lower() for s in profile.skills]
    assert "python" in skills, "legitimate Experience skill must be kept"
    assert "git" in skills, "legitimate Experience skill must be kept"
    for dumped in ("docker", "kubernetes", "aws", "terraform", "sql",
                   "postgresql", "react", "typescript"):
        assert dumped not in skills, f"dumped skill {dumped!r} must not count: {skills}"


def test_regression_seniority_not_from_other_peoples_titles() -> None:
    """Regression: another person's seniority in prose must not promote the candidate."""
    resume = """Experience
Junior Software Engineer | Acme | 2021-2024
- Worked closely with the VP of Engineering and the Chief Technology Officer.
- Reported directly to the Director of Platform.
"""
    profile = pipeline.build_candidate_profile(resume)
    assert profile.seniority == "Junior", f"got: {profile.seniority!r}"


def test_regression_seniority_from_own_vp_title() -> None:
    """An actual 'VP of Engineering' job title must map to VP."""
    resume = """Experience
VP of Engineering | Acme | 2019-2024
"""
    profile = pipeline.build_candidate_profile(resume)
    assert profile.seniority == "VP", f"got: {profile.seniority!r}"


def test_regression_seniority_from_own_senior_title() -> None:
    """An actual 'Senior Software Engineer' job title must map to Senior."""
    resume = """Experience
Senior Software Engineer | Acme | 2020-2024
"""
    profile = pipeline.build_candidate_profile(resume)
    assert profile.seniority == "Senior", f"got: {profile.seniority!r}"


# ── Dedicated regression tests for fixes ──────────────────────────────────────


def test_regression_pipe_education_not_parsed_as_experience() -> None:
    """Regression: pipe-delimited education lines must not leak into experience."""
    resume = """Experience
Senior Dev | Acme | 2019-2023

Education
MS Computer Science | Tech University | 2015-2017
BS Computer Science | State University | 2011-2015
"""
    profile = pipeline.build_candidate_profile(resume)
    # Experience must contain only the real job, not the education rows
    assert len(profile.experience) == 1, f"got: {profile.experience}"
    assert profile.experience[0].job_title == "Senior Dev"
    assert profile.experience[0].company == "Acme"
    # Education must still be parsed correctly
    assert len(profile.education) == 2
    degrees = [e.degree.lower() for e in profile.education]
    assert any("ms" in d for d in degrees)
    assert any("bs" in d for d in degrees)


def test_regression_bachelor_or_master_matches_both_levels() -> None:
    """Regression: 'Bachelor's or Master's' education requirement must match either level."""
    job = JobProfile(
        required_skills=["Python"],
        education_requirement="Bachelor's or Master's degree in Computer Science",
    )
    for degree in ("Bachelor of Science", "Master of Science", "Bachelor of Engineering"):
        candidate = CandidateProfile(
            skills=["Python"],
            education=[EducationEntry(degree=degree, institution="Uni")],
        )
        analysis = pipeline.analyze_match(candidate, job)
        assert analysis.education_match is True, f"{degree!r} failed for or-requirement"

    non_deg = CandidateProfile(
        skills=["Python"],
        education=[EducationEntry(degree="Some College Courses", institution="Uni")],
    )
    analysis = pipeline.analyze_match(non_deg, job)
    assert analysis.education_match is False, "non-degree candidate must not match"
def test_regression_normal_dates_remain_valid() -> None:
    """Normal employment dates must pass through the year validation untouched."""
    resume = """Experience
Software Engineer | Company | 2018-2024
Dev | Older Co | 2014-2018
"""
    profile = pipeline.build_candidate_profile(resume)
    assert len(profile.experience) == 2
    assert profile.experience[0].start_year == 2018
    assert profile.experience[0].end_year == 2024
    assert profile.experience[1].start_year == 2014
    assert profile.experience[1].end_year == 2018


def test_regression_1970_present_does_not_inflate_experience() -> None:
    """'1970-present' (an absurd single-role span) must not inflate experience."""
    resume = """Experience
Software Engineer | Company | 1970-present
"""
    profile = pipeline.build_candidate_profile(resume)
    assert profile.experience == [], f"implausible entry must be dropped: {profile.experience}"
    job = JobProfile(required_skills=["Python"], min_experience_years=5.0)
    analysis = pipeline.analyze_match(profile, job)
    assert analysis.candidate_experience_years == 0


def test_regression_future_and_reversed_dates_handled() -> None:
    """Future start years and end-before-start years must not inflate experience."""
    from datetime import date
    current_year = date.today().year
    future_start = current_year + 5
    future_end = current_year + 7
    resume = f"""Experience
Junior Dev | Acme | {future_start}-{future_end}
Dev | Beta | 2022-2020
Real Dev | Gamma | 2019-2023
"""
    profile = pipeline.build_candidate_profile(resume)
    total = 0
    for exp in profile.experience:
        end = exp.end_year if exp.end_year is not None else current_year
        total += max(0, end - exp.start_year)
    # Future entry is dropped; reversed entry is clamped to 0 years;
    # only the genuine 2019-2023 role counts.
    assert total == 4, f"expected 4 years, got {total}: {profile.experience}"


def test_regression_malformed_dates_do_not_inflate_experience() -> None:
    """Malformed date tokens must not invent experience entries."""
    resume = """Experience
Dev | Acme | 20-2024
"""
    profile = pipeline.build_candidate_profile(resume)
    assert profile.experience == [], f"malformed entry must be dropped: {profile.experience}"
    job = JobProfile(required_skills=["Python"], min_experience_years=10.0)
    analysis = pipeline.analyze_match(profile, job)
    assert analysis.candidate_experience_years == 0
