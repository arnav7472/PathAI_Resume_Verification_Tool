"""Typed pipeline interfaces for the V2 AI pipeline.

Stage sequence:
    Resume                              -> CandidateProfile
    Job Description                     -> JobProfile
    CandidateProfile + JobProfile       -> MatchAnalysis
    MatchAnalysis                       -> MatchScore
    MatchAnalysis + MatchScore          -> Explanation
    CandidateProfile + JobProfile       -> SkillGaps

Each stage is implemented with deterministic logic (no LLM/API call) that
satisfies the typed contract defined in .schemas.
"""

from __future__ import annotations

import re
from typing import Set

from .schemas import (
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

# ── Helper constants & patterns ──────────────────────────────────────────────

# A non-exhaustive list of common technical skills used to seed keyword
# extraction from free-form text.  The lists are deliberately kept small;
# production pipelines should use a dedicated skills taxonomy / NER model.
_COMMON_SKILLS: Set[str] = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "nosql",
    "react", "angular", "vue", "django", "flask", "fastapi", "spring",
    "node.js", "express", "graphql", "rest", "api", "docker", "kubernetes",
    "aws", "gcp", "azure", "terraform", "ci/cd", "git", "linux",
    "postgresql", "mysql", "mongodb", "redis", "kafka", "rabbitmq",
    "machine learning", "deep learning", "nlp", "computer vision",
    "pytorch", "tensorflow", "scikit-learn", "pandas", "spark",
    "agile", "scrum", "leadership", "mentoring", "project management",
    "communication", "teamwork", "problem solving", "critical thinking",
}

_COMMON_TECHNOLOGIES: Set[str] = {
    "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
    "ruby", "php", "swift", "kotlin", "scala", "r", "sql",
    "react", "angular", "vue", "django", "flask", "fastapi", "spring",
    "node.js", "express", "graphql", "docker", "kubernetes",
    "aws", "gcp", "azure", "terraform", "git", "linux",
    "postgresql", "mysql", "mongodb", "redis", "kafka", "rabbitmq",
    "pytorch", "tensorflow", "pandas", "spark", "hadoop",
}

_SENIORITY_KEYWORDS = {
    "intern": "Intern",
    "junior": "Junior",
    "mid": "Mid",
    "intermediate": "Mid",
    "senior": "Senior",
    "lead": "Lead",
    "principal": "Principal",
    "staff": "Staff",
    "manager": "Manager",
    "director": "Director",
    "head": "Head",
    "vp": "VP",
    "chief": "C-Level",
    "cto": "C-Level",
    "ceo": "C-Level",
}

_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
# ── Internal helpers ─────────────────────────────────────────────────────────


def _extract_degree_level(text: str) -> str | None:
    """Extract a normalised degree-level keyword from *text* (e.g. 'bachelor', 'master', 'phd')."""
    level_keywords = {
        "phd", "ph.d", "doctorate", "doctor",
        "master", "master's", "ms", "m.s.", "ma", "m.a.", "mba",
        "bachelor", "bachelor's", "bs", "b.s.", "ba", "b.a.", "btech", "b.tech",
        "associate", "diploma",
    }
    lower = text.lower()
    for kw in sorted(level_keywords, key=len, reverse=True):
        if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", lower):
            # Normalise common variants
            normalised = {"ph.d": "phd", "ph.d.": "phd", "doctorate": "phd", "doctor": "phd",
                          "master's": "master", "m.s.": "master", "m.s": "master",
                          "ms": "master",
                          "ma": "master", "m.a.": "master", "m.a": "master", "mba": "master",
                          "bachelor's": "bachelor", "b.s.": "bachelor", "b.s": "bachelor",
                          "bs": "bachelor",
                          "ba": "bachelor", "b.a.": "bachelor", "b.a": "bachelor",
                          "btech": "bachelor", "b.tech": "bachelor",
                          "associate": "associate", "diploma": "diploma"}.get(kw)
            return normalised or kw
    return None


def _extract_all_degree_levels(text: str) -> set[str]:
    """Extract ALL normalised degree-level keywords from *text* (e.g. 'bachelor' and 'master' from \"Bachelor's or Master's\")."""
    level_keywords = {
        "phd", "ph.d", "doctorate", "doctor",
        "master", "master's", "ms", "m.s.", "ma", "m.a.", "mba",
        "bachelor", "bachelor's", "bs", "b.s.", "ba", "b.a.", "btech", "b.tech",
        "associate", "diploma",
    }
    lower = text.lower()
    found: set[str] = set()
    normalised_map = {
        "ph.d": "phd", "ph.d.": "phd", "doctorate": "phd", "doctor": "phd",
        "master's": "master", "m.s.": "master", "m.s": "master",
        "ms": "master",
        "ma": "master", "m.a.": "master", "m.a": "master", "mba": "master",
        "bachelor's": "bachelor", "b.s.": "bachelor", "b.s": "bachelor",
        "bs": "bachelor",
        "ba": "bachelor", "b.a.": "bachelor", "b.a": "bachelor",
        "btech": "bachelor", "b.tech": "bachelor",
        "associate": "associate", "diploma": "diploma",
    }
    for kw in sorted(level_keywords, key=len, reverse=True):
        if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", lower):
            found.add(normalised_map.get(kw, kw))
    return found


def _extract_skills(text: str, skill_set: Set[str] | None = None) -> list[str]:
    """Return a sorted unique list of recognised skills found in *text*.

    Uses non-word-boundary lookarounds to avoid false positives such as
    "api" inside "FastAPI" or "r" inside "Senior", while still matching
    skills that end with non-word characters like ``c++`` or ``c#``.
    """
    if skill_set is None:
        skill_set = _COMMON_SKILLS
    lower = text.lower()
    found: set[str] = set()
    for skill in sorted(skill_set, key=len, reverse=True):
        # Use (?<!\w) / (?!\w) instead of \b so that skills ending with
        # non-word characters (e.g. "c++", "c#") still match.  \b requires
        # a word boundary which fails after non-word characters like '+' or '#'.
        if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", lower):
            found.add(skill)
    return sorted(found)


def _extract_years(text: str) -> list[int]:
    """Extract all 4-digit years from *text*."""
    return [int(m.group()) for m in _YEAR_PATTERN.finditer(text)]


def _detect_seniority(text: str) -> str | None:
    """Detect the most senior seniority level mentioned in *text*.

    When called from ``build_candidate_profile`` the caller should pass
    *only* the candidate's own job titles (extracted from experience
    entries) so that mentioning another person's seniority (e.g.
    "Worked with the VP of Engineering") does not inflate the
    candidate's seniority level.
    """
    lower = text.lower()
    matched = None
    priority = 0
    _levels = [
        "Intern", "Junior", "Mid", "Senior", "Lead", "Principal",
        "Staff", "Manager", "Director", "Head", "VP", "C-Level",
    ]
    for keyword, level in _SENIORITY_KEYWORDS.items():
        if keyword in lower:
            p = _levels.index(level)
            if p > priority:
                priority = p
                matched = level
    return matched


_PIPE_DELIM = re.compile(r"\s*\|\s*")
_PIPE_EXP_LINE = re.compile(
    r"^(?P<title>.+?)\s*\|\s*(?P<company>.+?)\s*\|\s*"
    r"(?P<start>(?:19|20)\d{2})\s*[-–—]\s*(?P<end>(?:19|20)\d{2}|present|current)$",
    re.IGNORECASE,
)
_PIPE_EDU_LINE = re.compile(
    r"^(?P<degree>.+?)\s*\|\s*(?P<institution>.+?)\s*"
    r"(?:\|\s*)?(?P<start>(?:19|20)\d{2})\s*[-–—]\s*(?P<end>(?:19|20)\d{2}|present|current)?$",
    re.IGNORECASE,
)


def _parse_experience_blocks(text: str) -> list[ExperienceEntry]:
    """Attempt to split *text* into employment blocks and return entries.

    Supports both the legacy "next-line company" layout and the common
    pipe-delimited "Job Title | Company | 2018-2024" layout.
    """
    entries: list[ExperienceEntry] = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    years = _extract_years(text)
    year_idx = 0

    for i, line in enumerate(lines):
        pipe_match = _PIPE_EXP_LINE.match(line)
        if pipe_match:
            title = pipe_match.group("title").strip()
            # Skip education entries misidentified as experience (degree keywords in the title)
            if any(kw in title.lower() for kw in
                   ["bachelor", "master", "phd", "associate", "diploma", "degree"]):
                continue
            if re.search(r"\b(?:b\.?s\.?|m\.?s\.?|ph\.?d\.?|ba|ma|mba|btech|mtech)\b",
                         title, re.IGNORECASE):
                continue
            end_raw = pipe_match.group("end")
            end = (
                None
                if end_raw and end_raw.lower() in ("present", "current")
                else int(end_raw)
            )
            entries.append(ExperienceEntry(
                job_title=pipe_match.group("title").strip(),
                company=pipe_match.group("company").strip(),
                start_year=int(pipe_match.group("start")),
                end_year=end,
                responsibilities=[],
            ))
            continue

        if year_idx >= len(years) - 1:
            # If the current line doesn't even have a year, skip it (section header).
            if not _YEAR_PATTERN.search(line):
                continue
            break
        if _YEAR_PATTERN.search(line):
            if "|" in line:
                # A pipe-delimited line that did not match _PIPE_EXP_LINE is
                # malformed (e.g. "Dev | Acme | 20-2024").  Interpreting it via
                # the loose fallback would invent experience from arbitrary year
                # tokens, so it is skipped.
                year_idx += 2  # consume the year tokens as a valid entry would
                continue
            start = years[year_idx]
            end = years[year_idx + 1] if year_idx + 1 < len(years) else None
            year_idx += 2

            job_title = line
            company = ""
            responsibilities: list[str] = []

            # Try to split "Job Title at Company" or "Job Title @ Company"
            # patterns that appear on the same line as the years.
            at_match = re.match(
                r"^(.+?)\s+at\s+(.+)$", job_title, re.IGNORECASE
            )
            if not at_match:
                at_match = re.match(
                    r"^(.+?)\s+@\s+(.+)$", job_title, re.IGNORECASE
                )
            if at_match:
                job_title = at_match.group(1).strip()
                company = at_match.group(2).strip()
                # Drop trailing "(2020-2024)", "(2020-present)" etc. that
                # sometimes ride along on the same line.
                company = re.sub(
                    r"\s*\(\s*(?:19|20)\d{2}\s*[-–—]\s*(?:(?:19|20)\d{2}|present|current)\s*\)$",
                    "", company, flags=re.IGNORECASE,
                ).strip()

            for j in range(i + 1, min(i + 6, len(lines))):
                if _YEAR_PATTERN.search(lines[j]):
                    break
                if not company:
                    company = lines[j]
                else:
                    responsibilities.append(lines[j])

            entries.append(ExperienceEntry(
                job_title=job_title,
                company=company or "Unknown",
                start_year=start,
                end_year=end,
                responsibilities=responsibilities,
            ))
    return entries


def _parse_education_blocks(text: str) -> list[EducationEntry]:
    """Extract education entries from *text*."""
    entries: list[EducationEntry] = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    degree_keywords = {"bachelor", "master", "phd", "associate", "diploma",
                       "degree", "btech", "mtech", "b.e.", "m.e.",
                       "bachelor's", "master's"}
    # Also match short abbreviations with word boundaries
    degree_pattern = re.compile(
        r"\b(?:b\.?s\.?|m\.?s\.?|ph\.?d\.?|ba|ma|b\.?a\.?|m\.?a\.?|mba|"
        r"bachelor|master|phd|associate|diploma|degree|btech|mtech|"
        r"b\.?e\.?|m\.?e\.?)\b",
        re.IGNORECASE,
    )
    years = _extract_years(text)
    year_idx = 0

    for i, line in enumerate(lines):
        pipe_match = _PIPE_EDU_LINE.match(line)
        if pipe_match:
            degree_text = pipe_match.group("degree").strip()
            # Only accept pipe-delimited education if the degree field
            # contains an education keyword (prevents matching experience lines).
            if degree_keywords & set(degree_text.lower().split()) or degree_pattern.search(degree_text):
                end_raw = pipe_match.group("end")
                end = (
                    None
                    if end_raw and end_raw.lower() in ("present", "current")
                    else (int(end_raw) if end_raw else None)
                )
                entries.append(EducationEntry(
                    degree=degree_text,
                    institution=pipe_match.group("institution").strip(),
                    start_year=int(pipe_match.group("start")),
                    end_year=end,
                ))
                continue

        lower = line.lower()
        if any(kw in lower for kw in degree_keywords) or degree_pattern.search(line):
            start = None
            end = None
            if year_idx < len(years):
                start = years[year_idx]
                year_idx += 1
            if year_idx < len(years):
                end = years[year_idx]
                year_idx += 1
            institution = ""
            for j in range(i + 1, min(i + 3, len(lines))):
                if _YEAR_PATTERN.search(lines[j]) or any(
                    kw in lines[j].lower() for kw in degree_keywords
                ):
                    break
                institution = lines[j]
                break
            entries.append(EducationEntry(
                degree=line,
                institution=institution or "Unknown",
                start_year=start,
                end_year=end,
            ))
    return entries

# ── Year validation ────────────────────────────────────────────────────────────


def _validate_experience_years(entries: list[ExperienceEntry]) -> list[ExperienceEntry]:
    """Filter/clamp implausible year values that could inflate experience scores.

    Rules (applied per entry):
    * start_year < 1960               → entry skipped (clearly implausible for tech)
    * start_year > current_year       → entry skipped (future)
    * end_year is not None and < start_year → end_year clamped to start_year
    * end_year is not None and > current_year → end_year clamped to current_year
    * end_year is None and (current_year - start_year) > 40 → entry skipped
      (a single role spanning >40 years is implausible)
    """
    from datetime import date
    current_year = date.today().year
    validated: list[ExperienceEntry] = []
    for entry in entries:
        sy = entry.start_year
        ey = entry.end_year

        if sy < 1960 or sy > current_year:
            continue

        if ey is not None:
            if ey < sy:
                ey = sy
            if ey > current_year:
                ey = current_year

        if ey is None and (current_year - sy) > 40:
            continue

        validated.append(ExperienceEntry(
            job_title=entry.job_title,
            company=entry.company,
            start_year=sy,
            end_year=ey,
            responsibilities=entry.responsibilities,
        ))
    return validated


def _get_section_text(resume_text: str) -> str:
    """Return concatenated text of relevant resume sections (Skills, Experience,
    Education, Projects, Technical Skills).

    Only recognised section headers change the in/out state.  Unrecognised
    lines (e.g. job titles) do NOT close an active relevant section, so we
    avoid false negatives on structured resumes where a job-title line could
    otherwise be mistaken for an unrelated heading.

    If no recognised section header is found anywhere in the text, the
    full text is returned (fallback for unstructured resumes).
    """
    _RELEVANT_HEADERS = {
        "skills", "technical skills", "core competencies", "technologies",
        "experience", "work experience", "employment", "professional experience",
        "education", "academic background",
        "projects", "project",
    }
    _IRRELEVANT_HEADERS = {
        "interests", "hobbies", "references", "contact", "objective",
        "languages", "awards", "publications", "activities", "volunteering",
        "affiliations", "certifications",
    }
    _SECTION_HEADER = re.compile(r"^[a-z][a-z\s]{0,30}$", re.IGNORECASE)
    _INLINE_HEADER = re.compile(r"^([a-z][a-z\s]{0,40}?)\s*:", re.IGNORECASE)

    lines = resume_text.split("\n")
    sections: list[str] = []
    in_relevant_section = False
    found_any_section = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower().rstrip(":").strip()

        # Standalone section header, e.g. "Experience" or "Skills".
        if _SECTION_HEADER.match(stripped) and len(stripped) < 40:
            if lower in _RELEVANT_HEADERS:
                in_relevant_section = True
                found_any_section = True
            elif lower in _IRRELEVANT_HEADERS:
                in_relevant_section = False
            # Unrecognised short line (e.g. a job title) does **not** change state.
            continue

        # Inline section header with content on the same line,
        # e.g. "Skills: Python, Docker".
        inline = _INLINE_HEADER.match(stripped)
        if inline and len(stripped) < 300:
            header_name = inline.group(1).strip().lower()
            if header_name in _RELEVANT_HEADERS:
                in_relevant_section = True
                found_any_section = True
                sections.append(stripped)  # keep the content after the colon
                continue
            if header_name in _IRRELEVANT_HEADERS:
                in_relevant_section = False
                continue

        if in_relevant_section:
            sections.append(stripped)

    if not found_any_section:
        return resume_text

    return "\n".join(sections)

    if not found_any_section:
        return resume_text

    return "\n".join(sections)


# ── Public pipeline stages ────────────────────────────────────────────────────


def build_candidate_profile(resume_text: str) -> CandidateProfile:
    """Derive a CandidateProfile from normalized resume text."""
    if not resume_text or not resume_text.strip():
        return CandidateProfile()

    # Security: extract skills from relevant sections only to prevent
    # arbitrary skill-dumping in unrelated prose from inflating scores.
    section_text = _get_section_text(resume_text)
    skills = _extract_skills(section_text)
    technologies = _extract_skills(section_text, _COMMON_TECHNOLOGIES)

    experience = _validate_experience_years(_parse_experience_blocks(resume_text))
    education = _parse_education_blocks(resume_text)

    # Security: determine seniority from the candidate's own job titles
    # only, not from arbitrary mentions in the resume prose.
    job_titles = [e.job_title for e in experience]
    seniority_text = " ".join(job_titles)
    seniority = _detect_seniority(seniority_text) if seniority_text else None

    projects: list[ProjectEntry] = []
    in_projects_section = False
    for line in resume_text.split("\n"):
        stripped = line.strip()
        lower = stripped.lower()
        # Detect "Projects" section header
        if re.match(r"^projects?\s*$", lower, re.IGNORECASE):
            in_projects_section = True
            continue
        # Detect another section header (end of projects section)
        if in_projects_section and re.match(r"^[a-z][a-z\s]+$", lower, re.IGNORECASE) and len(stripped) < 30:
            if lower.strip() not in ("projects",) and any(
                kw in lower for kw in ["skills", "education", "experience", "summary", "certification"]
            ):
                in_projects_section = False
                continue
        if in_projects_section and stripped:
            # Remove bullet markers
            project_text = re.sub(r"^[•\-*]\s*", "", stripped).strip()
            if project_text:
                projects.append(ProjectEntry(name=project_text))
        # Legacy explicit project markers
        if any(kw in lower for kw in ["project:", "project -", "project --"]):
            projects.append(ProjectEntry(name=stripped))

    return CandidateProfile(
        skills=skills,
        technologies=technologies,
        experience=experience,
        education=education,
        job_titles=job_titles,
        seniority=seniority,
        industries=[],
        certifications=[],
        languages=[],
        projects=projects,
    )


def build_job_profile(job_description: str) -> JobProfile:
    """Derive a JobProfile from normalized job description text."""
    if not job_description or not job_description.strip():
        return JobProfile()

    required_skills = _extract_skills(job_description)
    technologies = _extract_skills(job_description, _COMMON_TECHNOLOGIES)
    seniority = _detect_seniority(job_description)

    min_exp = None
    max_exp = None
    exp_pattern = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE)
    range_pattern = re.compile(
        r"(\d+)\s*[-to]+\s*(\d+)\s*(?:years?|yrs?)", re.IGNORECASE
    )

    range_match = range_pattern.search(job_description)
    if range_match:
        min_exp = float(range_match.group(1))
        max_exp = float(range_match.group(2))
    else:
        single_match = exp_pattern.search(job_description)
        if single_match:
            min_exp = float(single_match.group(1))

    edu_req = None
    edu_patterns = [
        r"(bachelor[^.]*degree)",
        r"(master[^.]*degree)",
        r"(phd[^.]*degree)",
        r"(ph\.d[^.]*degree)",
        r"(associate[^.]*degree)",
]
    for pat in edu_patterns:
        m = re.search(pat, job_description, re.IGNORECASE)
        if m:
            edu_req = m.group(1).strip()
            break

    remote_allowed = None
    if re.search(r"\bremote\b", job_description, re.IGNORECASE):
        remote_allowed = True

    location = None
    m = re.search(
        r"(?:location|located|based)\s*[:-]\s*([A-Za-z\s,]+?)(?:\.|$|\n)",
        job_description, re.IGNORECASE,
    )
    if m:
        loc_candidate = m.group(1).strip()
        if len(loc_candidate) < 100:
            location = loc_candidate
    if not location:
        # Also try "based in <city>" or "based out of <city>" (no colon).
        m = re.search(
            r"based\s+(?:in|out\s+of)\s+([A-Za-z\s,]+?)(?:\.|$|\n)",
            job_description, re.IGNORECASE,
        )
        if m:
            loc_candidate = m.group(1).strip()
            if len(loc_candidate) < 100:
                location = loc_candidate

    # --- Extract preferred skills from "Nice to have" / "Preferred" sections ---
    preferred_skills: list[str] = []
    preferred_section_pattern = re.compile(
        r"(?:nice\s*to\s*have|preferred)\s*(?:qualifications?|skills?)?\s*[::\-]?\s*(.*?)(?=\n\s*(?:requirements|qualifications|responsibilities|about|$))",
        re.IGNORECASE | re.DOTALL,
    )
    for sec_match in preferred_section_pattern.finditer(job_description):
        sec_text = sec_match.group(1)
        for skill in _extract_skills(sec_text):
            if skill.lower() not in {s.lower() for s in preferred_skills}:
                preferred_skills.append(skill)

    return JobProfile(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        required_technologies=technologies,
        min_experience_years=min_exp,
        max_experience_years=max_exp,
        education_requirement=edu_req,
        seniority_level=seniority,
        job_titles=[],
        industries=[],
        certifications_required=[],
        languages_required=[],
        location=location,
        remote_allowed=remote_allowed,
        responsibilities=[],
    )
def analyze_match(candidate: CandidateProfile, job: JobProfile) -> MatchAnalysis:
    """Compare a CandidateProfile against a JobProfile."""
    candidate_skills = set(s.lower() for s in candidate.skills)
    candidate_techs = set(t.lower() for t in candidate.technologies)
    job_skills = set(s.lower() for s in job.required_skills)
    job_preferred = set(s.lower() for s in job.preferred_skills)
    job_techs = set(t.lower() for t in job.required_technologies)

    all_job_skills = job_skills | job_preferred

    matched_skills = sorted(candidate_skills & all_job_skills)
    missing_skills = sorted(all_job_skills - candidate_skills)
    additional_skills = sorted(candidate_skills - all_job_skills)

    matched_technologies = sorted(candidate_techs & job_techs)
    missing_technologies = sorted(job_techs - candidate_techs)

    from datetime import date
    _current_year = date.today().year
    total_years = 0
    for exp in candidate.experience:
        if exp.start_year:
            end = exp.end_year if exp.end_year else _current_year
            total_years += end - exp.start_year

    gap_years = None
    if job.min_experience_years is not None and total_years < job.min_experience_years:
        gap_years = job.min_experience_years - total_years

    education_match = None
    if candidate.education and job.education_requirement:
        job_levels = _extract_all_degree_levels(job.education_requirement)
        if job_levels:
            cand_levels = {
                _extract_degree_level(e.degree) for e in candidate.education
                if _extract_degree_level(e.degree)
            }
            education_match = bool(job_levels & cand_levels)
        else:
            # Fallback: match first-5-chars only when no degree keyword was
            # recognised in the requirement (keeps the historical behaviour).
            edu_text = " ".join(e.degree.lower() for e in candidate.education)
            education_match = job.education_requirement.lower()[:5] in edu_text

    seniority_match = None
    if candidate.seniority and job.seniority_level:
        seniority_match = candidate.seniority.lower() == job.seniority_level.lower()

    location_match = None
    if job.location:
        # Candidate has no location field in CandidateProfile, so we
        # cannot determine match — set to None (unknown) rather than False.
        location_match = None

    return MatchAnalysis(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        additional_skills=additional_skills,
        matched_technologies=matched_technologies,
        missing_technologies=missing_technologies,
        candidate_experience_years=total_years,
        experience_gap_years=gap_years,
        education_match=education_match,
        seniority_match=seniority_match,
        location_match=location_match,
        notes=[],
    )


def compute_match_score(analysis: MatchAnalysis) -> MatchScore:
    """Derive numeric MatchScore sub-scores from a MatchAnalysis. 0-100 each."""
    total_required = len(analysis.matched_skills) + len(analysis.missing_skills)
    if total_required > 0:
        skill_score = int(round(len(analysis.matched_skills) / total_required * 100))
    else:
        skill_score = 100

    if analysis.candidate_experience_years is not None:
        if analysis.experience_gap_years is not None and analysis.experience_gap_years > 0:
            # Below the stated minimum -> penalise by the shortfall.
            experience_score = max(0, 100 - int(analysis.experience_gap_years * 20))
        else:
            # Requirement met (or no requirement stated) -> full credit.
            experience_score = 100
    else:
        # Unknown experience -> neutral (must NOT act as a mismatch).
        experience_score = 50

    if analysis.education_match is True:
        education_score = 100
    elif analysis.education_match is False:
        education_score = 0
    else:
        education_score = 50

    if analysis.seniority_match is True:
        seniority_score = 100
    elif analysis.seniority_match is False:
        seniority_score = 0
    else:
        seniority_score = 50

    if analysis.location_match is True:
        location_score = 100
    elif analysis.location_match is False:
        location_score = 0
    else:
        location_score = 50

    overall_score = int(round(
        0.35 * skill_score +
        0.25 * experience_score +
        0.15 * education_score +
        0.15 * seniority_score +
        0.10 * location_score
    ))

    return MatchScore(
        overall_score=max(0, min(100, overall_score)),
        skill_score=max(0, min(100, skill_score)),
        experience_score=max(0, min(100, experience_score)),
        education_score=max(0, min(100, education_score)),
        seniority_score=max(0, min(100, seniority_score)),
        location_score=max(0, min(100, location_score)),
    )


def generate_explanation(analysis: MatchAnalysis, score: MatchScore) -> Explanation:
    """Derive a narrative Explanation from a MatchAnalysis + MatchScore."""
    if score.overall_score >= 80:
        recommendation = "Yes \u2014 the candidate is a strong match for this role."
    elif score.overall_score >= 60:
        recommendation = "Maybe \u2014 the candidate meets many requirements but has some gaps."
    elif score.overall_score >= 40:
        recommendation = "Cautious \u2014 the candidate has significant gaps that need review."
    else:
        recommendation = "No \u2014 the candidate does not meet the key requirements for this role."

    reason_parts = []
    skill_gap_count = len(analysis.missing_skills) + len(analysis.missing_technologies)
    if skill_gap_count == 0:
        reason_parts.append("No skill gaps identified.")
    elif skill_gap_count <= 2:
        reason_parts.append(f"Minor skill gaps ({skill_gap_count} missing).")
    else:
        reason_parts.append(f"Significant skill gaps ({skill_gap_count} missing).")

    if analysis.candidate_experience_years is not None:
        reason_parts.append(
            f"Candidate has {analysis.candidate_experience_years:.0f} years of experience."
        )
    if analysis.experience_gap_years is not None and analysis.experience_gap_years > 0:
        reason_parts.append(
            f"Experience shortfall of {analysis.experience_gap_years:.0f} years."
        )
    if analysis.education_match is True:
        reason_parts.append("Education requirement met.")
    elif analysis.education_match is False:
        reason_parts.append("Education requirement not met.")
    if analysis.seniority_match is True:
        reason_parts.append("Seniority level aligns.")
    elif analysis.seniority_match is False:
        reason_parts.append("Seniority level mismatch.")

    reason = " ".join(reason_parts)
    # Normalise whitespace to prevent encoding / spacing artefacts
    # such as missing spaces between words.
    reason = " ".join(reason.split())

    strengths: list[str] = []
    if analysis.matched_skills:
        strengths.append(
            f"Skills match: {', '.join(analysis.matched_skills[:5])}"
            f"{' and more' if len(analysis.matched_skills) > 5 else ''}."
        )
    if analysis.matched_technologies:
        strengths.append(
            f"Technology match: {', '.join(analysis.matched_technologies[:3])}."
        )
    if analysis.education_match is True:
        strengths.append("Education qualification satisfied.")
    if analysis.seniority_match is True:
        strengths.append("Seniority level appropriate.")

    concerns: list[str] = []
    if analysis.missing_skills:
        concerns.append(
            f"Missing required skills: {', '.join(analysis.missing_skills[:5])}"
            f"{' and more' if len(analysis.missing_skills) > 5 else ''}."
        )
    if analysis.missing_technologies:
        concerns.append(
            f"Missing technologies: {', '.join(analysis.missing_technologies[:3])}."
        )
    if analysis.experience_gap_years is not None and analysis.experience_gap_years > 0:
        concerns.append(
            f"Below minimum experience requirement by {analysis.experience_gap_years:.0f} years."
        )
    if analysis.education_match is False:
        concerns.append("Does not satisfy education requirement.")
    if analysis.seniority_match is False:
        concerns.append("Seniority level does not match the role expectation.")

    return Explanation(
        recommendation=recommendation,
        reason=reason,
        strengths=strengths,
        concerns=concerns,
    )


def compute_skill_gaps(candidate: CandidateProfile, job: JobProfile) -> SkillGaps:
    """Derive a SkillGaps breakdown from a CandidateProfile + JobProfile."""
    candidate_skills = set(s.lower() for s in candidate.skills)
    job_required = set(s.lower() for s in job.required_skills)
    job_preferred = set(s.lower() for s in job.preferred_skills)

    missing_required = sorted(job_required - candidate_skills)
    missing_preferred = sorted(job_preferred - candidate_skills)
    additional = sorted(candidate_skills - (job_required | job_preferred))

    all_job_skills = job_required | job_preferred
    if all_job_skills:
        covered = all_job_skills & candidate_skills
        coverage_percentage = round(len(covered) / len(all_job_skills) * 100, 1)
    else:
        coverage_percentage = 100.0

    recommendations: list[str] = []
    if missing_required:
        recommendations.append(
            f"Acquire or highlight experience in: {', '.join(missing_required)}."
        )
    if missing_preferred:
        recommendations.append(
            f"Consider developing preferred skills: {', '.join(missing_preferred)}."
        )
    if not missing_required and not missing_preferred:
        recommendations.append("Candidate covers all job skills \u2014 no gaps identified.")
    if additional:
        recommendations.append(
            f"Candidate brings additional relevant skills: {', '.join(additional[:5])}."
        )

    return SkillGaps(
        missing_required_skills=missing_required,
        missing_preferred_skills=missing_preferred,
        additional_skills=additional,
        coverage_percentage=max(0.0, min(100.0, coverage_percentage)),
        recommendations=recommendations,
    )

__all__ = [
    "build_candidate_profile",
    "build_job_profile",
    "analyze_match",
    "compute_match_score",
    "generate_explanation",
    "compute_skill_gaps",
]
