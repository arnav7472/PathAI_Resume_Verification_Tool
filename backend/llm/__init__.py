"""V2 AI pipeline foundation: typed schemas and pipeline interfaces.

No LLM/API integration lives here yet — see pipeline.py for stage stubs
and schemas.py for the CandidateProfile/JobProfile/MatchAnalysis/
MatchScore/Explanation/SkillGaps data contracts.
"""

from .schemas import (
    CandidateProfile,
    EducationEntry,
    Explanation,
    ExperienceEntry,
    JobProfile,
    MatchAnalysis,
    MatchScore,
    ProjectEntry,
    SkillGaps,
)

__all__ = [
    "CandidateProfile",
    "EducationEntry",
    "Explanation",
    "ExperienceEntry",
    "JobProfile",
    "MatchAnalysis",
    "MatchScore",
    "ProjectEntry",
    "SkillGaps",
]
