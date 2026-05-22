"""Tests for backend/timeline/analysis.py — timeline entries, overlaps, gaps, and skill insights."""
from __future__ import annotations

from backend.parsers.section_parser import parse_resume_sections
from backend.timeline.analysis import (
    analyze_employment_spans,
    extract_timeline_entries,
    skill_timeline_insights,
)


# ── extract_timeline_entries ───────────────────────────────────────────────

class TestExtractTimelineEntries:
    def test_simple_range(self):
        entries = extract_timeline_entries("Worked at Acme 2018-2021 as engineer")
        assert len(entries) == 1
        assert entries[0]["start_year"] == 2018
        assert entries[0]["end_year"] == 2021

    def test_present_end(self):
        entries = extract_timeline_entries("Acme Corp 2020-present")
        assert len(entries) == 1
        assert entries[0]["start_year"] == 2020
        assert entries[0]["end_year"] == "present"

    def test_em_dash_range(self):
        entries = extract_timeline_entries("Acme 2017–2020")
        assert len(entries) == 1
        assert entries[0]["start_year"] == 2017
        assert entries[0]["end_year"] == 2020

    def test_multiple_entries(self):
        entries = extract_timeline_entries(
            "Job1 2015-2018. Job2 2019-present."
        )
        assert len(entries) == 2

    def test_no_dates_returns_empty(self):
        entries = extract_timeline_entries("Worked on various projects.")
        assert len(entries) == 0

    def test_present_alias_current(self):
        entries = extract_timeline_entries("Acme 2021-current")
        assert len(entries) == 1
        assert entries[0]["end_year"] == "present"


# ── analyze_employment_spans ───────────────────────────────────────────────

class TestAnalyzeEmploymentSpans:
    def test_sequential_roles_no_overlap(self):
        entries = [
            {"start_year": 2015, "end_year": 2018, "evidence": "Job A"},
            {"start_year": 2019, "end_year": 2021, "evidence": "Job B"},
        ]
        result = analyze_employment_spans(entries)
        assert len(result["overlaps"]) == 0
        assert len(result["gaps"]) == 0  # 2019 == 2018+1 so no gap

    def test_gap_detected_when_more_than_one_year(self):
        entries = [
            {"start_year": 2015, "end_year": 2017, "evidence": "Job A"},
            {"start_year": 2019, "end_year": 2021, "evidence": "Job B"},
        ]
        result = analyze_employment_spans(entries)
        assert len(result["gaps"]) == 1  # 2019 > 2017+1

    def test_overlapping_roles_detected(self):
        entries = [
            {"start_year": 2015, "end_year": 2020, "evidence": "Job A"},
            {"start_year": 2018, "end_year": 2022, "evidence": "Job B"},
        ]
        result = analyze_employment_spans(entries)
        assert len(result["overlaps"]) > 0

    def test_present_counted_as_2026(self):
        entries = [
            {"start_year": 2020, "end_year": "present", "evidence": "Current job"},
            {"start_year": 2018, "end_year": 2020, "evidence": "Previous job"},
        ]
        result = analyze_employment_spans(entries)
        # 2020 start and 2020 end should have no gap; "present" is 2026
        assert len(result["gaps"]) == 0

    def test_suspicious_long_span_detected(self):
        entries = [
            {"start_year": 1990, "end_year": 2022, "evidence": "Very long tenure"},
        ]
        result = analyze_employment_spans(entries)
        assert len(result["suspicious_inflation"]) > 0

    def test_empty_entries_returns_empty_lists(self):
        result = analyze_employment_spans([])
        assert result["overlaps"] == []
        assert result["gaps"] == []
        assert result["suspicious_inflation"] == []


# ── overlapping timeline (integration) ─────────────────────────────────────

class TestOverlappingTimelineResume:
    def test_overlapping_dates_flagged(self):
        text = """Experience
        Company A 2018-2021
        Company B 2020-2022
        """
        entries = extract_timeline_entries(text)
        result = analyze_employment_spans(entries)
        assert len(result["overlaps"]) > 0

    def test_no_overlap_when_sequential(self):
        text = """Experience
        Company A 2018-2020
        Company B 2021-2023
        """
        entries = extract_timeline_entries(text)
        result = analyze_employment_spans(entries)
        assert len(result["overlaps"]) == 0


# ── skill_timeline_insights ────────────────────────────────────────────────

class TestSkillTimelineInsights:
    def test_skill_with_year_found(self):
        text = """Experience
        Built apps with Python in 2019 and 2020.
        Skills
        Python
        """
        sections = parse_resume_sections(text)
        insights = skill_timeline_insights(sections, ["Python"])
        py = next(i for i in insights if i["skill"] == "Python")
        assert py["first_seen"] is not None
        assert py["experience_years_estimate"] is not None

    def test_skill_with_no_year_found(self):
        text = """Skills
        Python
        """
        sections = parse_resume_sections(text)
        insights = skill_timeline_insights(sections, ["Python"])
        py = next(i for i in insights if i["skill"] == "Python")
        assert py["first_seen"] is None
        assert py["experience_years_estimate"] is None

    def test_multiple_skills(self):
        text = """Experience
        Used Python in 2019 and Docker in 2020.
        Skills
        Python, Docker
        """
        sections = parse_resume_sections(text)
        insights = skill_timeline_insights(sections, ["Python", "Docker"])
        assert len(insights) == 2
        skills_found = {i["skill"] for i in insights}
        assert skills_found == {"Python", "Docker"}

    def test_first_seen_is_min_year(self):
        text = """Experience
        Python in 2018, then more Python in 2022.
        Skills
        Python
        """
        sections = parse_resume_sections(text)
        insights = skill_timeline_insights(sections, ["Python"])
        py = next(i for i in insights if i["skill"] == "Python")
        assert py["first_seen"] == "2018"