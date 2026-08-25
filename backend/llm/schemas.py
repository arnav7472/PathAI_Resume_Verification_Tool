"""Typed schemas for the V2 AI pipeline (CandidateProfile, JobProfile, MatchAnalysis,
MatchScore, Explanation, SkillGaps).

These models define the data contract for a future LLM-backed pipeline
(Resume -> CandidateProfile -> ... -> SkillGaps). No LLM/API call is made
from this module. Shapes are validated against sample outputs produced
during offline pipeline validation (candidate profile + job match score
fixtures), split so that MatchScore holds only numeric sub-scores and
Explanation holds the narrative recommendation/reason.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExperienceEntry(BaseModel):
    """A single employment entry extracted from a resume."""

    job_title: str
    company: str
    start_year: int
    end_year: int | None = None  # None = present/current
    responsibilities: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    """A single education entry extracted from a resume."""

    degree: str
    institution: str
    start_year: int | None = None
    end_year: int | None = None


class ProjectEntry(BaseModel):
    """A single project entry extracted from a resume."""

    name: str
    description: str = ""
    technologies_used: list[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    """Structured candidate profile derived from resume text."""

    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    job_titles: list[str] = Field(default_factory=list)
    seniority: str | None = None
    industries: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)


class JobProfile(BaseModel):
    """Structured job requirements derived from a job description."""

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_technologies: list[str] = Field(default_factory=list)
    min_experience_years: float | None = None
    max_experience_years: float | None = None
    education_requirement: str | None = None
    seniority_level: str | None = None
    job_titles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    certifications_required: list[str] = Field(default_factory=list)
    languages_required: list[str] = Field(default_factory=list)
    location: str | None = None
    remote_allowed: bool | None = None
    responsibilities: list[str] = Field(default_factory=list)


class MatchAnalysis(BaseModel):
    """Intermediate comparison of a CandidateProfile against a JobProfile."""

    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    additional_skills: list[str] = Field(default_factory=list)
    matched_technologies: list[str] = Field(default_factory=list)
    missing_technologies: list[str] = Field(default_factory=list)
    candidate_experience_years: float | None = None
    experience_gap_years: float | None = None
    education_match: bool | None = None
    seniority_match: bool | None = None
    location_match: bool | None = None
    notes: list[str] = Field(default_factory=list)


class MatchScore(BaseModel):
    """Numeric sub-scores derived from a MatchAnalysis. 0-100 each."""

    overall_score: int = Field(..., ge=0, le=100)
    skill_score: int = Field(..., ge=0, le=100)
    experience_score: int = Field(..., ge=0, le=100)
    education_score: int = Field(..., ge=0, le=100)
    seniority_score: int = Field(..., ge=0, le=100)
    location_score: int = Field(..., ge=0, le=100)


class Explanation(BaseModel):
    """Narrative explanation derived from a MatchAnalysis + MatchScore."""

    recommendation: str
    reason: str
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


class SkillGaps(BaseModel):
    """Skill gap breakdown derived from a CandidateProfile + JobProfile."""

    missing_required_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    additional_skills: list[str] = Field(default_factory=list)
    coverage_percentage: float = Field(..., ge=0, le=100)
    recommendations: list[str] = Field(default_factory=list)


__all__ = [
    "ExperienceEntry",
    "EducationEntry",
    "ProjectEntry",
    "CandidateProfile",
    "JobProfile",
    "MatchAnalysis",
    "MatchScore",
    "Explanation",
    "SkillGaps",
]
