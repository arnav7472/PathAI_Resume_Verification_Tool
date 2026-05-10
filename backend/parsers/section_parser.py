"""Structured resume section parser: headings, bullets, and sentence lists."""

from __future__ import annotations

import re
from typing import Any, Literal

SectionKey = Literal[
    "skills",
    "experience",
    "projects",
    "education",
    "certifications",
    "achievements",
    "summary",
    "other",
]

_HEADING_MAP: list[tuple[re.Pattern[str], SectionKey]] = [
    (re.compile(r"^(technical\s+)?skills$|core\s+competencies|key\s+skills|technologies", re.I), "skills"),
    (re.compile(r"^work\s+experience|professional\s+experience|employment|experience$|career\s+history", re.I), "experience"),
    (re.compile(r"^projects?|selected\s+projects|personal\s+projects|portfolio", re.I), "projects"),
    (re.compile(r"^education|academic|university|qualifications", re.I), "education"),
    (
        re.compile(r"^certifications?|licenses|licences|professional\s+certifications", re.I),
        "certifications",
    ),
    (re.compile(r"^achievements?|awards|honou?rs|accomplishments", re.I), "achievements"),
    (re.compile(r"^summary|profile|objective|about\s+me", re.I), "summary"),
]


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", (line or "").strip())


def split_sentences_block(text: str) -> list[str]:
    """Split a block into sentences; keep bullets as separate units when long."""
    if not (text or "").strip():
        return []
    compact = re.sub(r"\s+", " ", text.strip())
    pieces = re.split(r"(?<=[.!?])\s+|(?=\s*[•*·▪-]\s)|\n+", compact)
    out: list[str] = []
    for piece in pieces:
        s = piece.strip(" \t•*·▪-–—")
        if len(s) > 2:
            out.append(s)
    return out


def _detect_heading(line: str) -> SectionKey | None:
    stripped = line.strip().lower()
    stripped = re.sub(r"[:#]+$", "", stripped).strip()
    for pattern, key in _HEADING_MAP:
        if pattern.search(stripped):
            return key
    return None


def parse_resume_sections(normalized_text: str) -> dict[str, Any]:
    """
    Split resume text into section buckets with blocks that preserve structure.

    Returns:
      {
        "skills": [ { "heading", "lines", "bullets", "sentences" }, ... ],
        "experience": [ ... ],
        ...
      }
    """
    lines = [ln for ln in (normalized_text or "").split("\n") if ln.strip()]

    buckets: dict[SectionKey, list[dict[str, Any]]] = {
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "achievements": [],
        "summary": [],
        "other": [],
    }

    current_key: SectionKey = "other"
    current_heading = ""
    buf_lines: list[str] = []

    def flush() -> None:
        nonlocal buf_lines, current_heading, current_key
        if not buf_lines and not current_heading:
            return
        block_text = "\n".join(buf_lines)
        bullets = [ln for ln in buf_lines if re.match(r"^\s*[•*·▪-]", ln) or len(ln) > 160]
        sentences = split_sentences_block(block_text)
        buckets[current_key].append(
            {
                "heading": current_heading or current_key,
                "lines": list(buf_lines),
                "bullets": bullets,
                "sentences": sentences,
            }
        )
        buf_lines = []

    for raw in lines:
        line = _normalize_line(raw)
        heading_key = _detect_heading(line)
        if heading_key and len(line) < 120:
            flush()
            current_key = heading_key
            current_heading = line
            continue
        buf_lines.append(raw.strip())

    flush()

    if not any(buckets[k] for k in buckets):
        sentences = split_sentences_block(normalized_text)
        buckets["other"].append(
            {
                "heading": "document",
                "lines": lines,
                "bullets": [],
                "sentences": sentences,
            }
        )

    return {
        "skills": buckets["skills"],
        "experience": buckets["experience"],
        "projects": buckets["projects"],
        "education": buckets["education"],
        "certifications": buckets["certifications"],
        "achievements": buckets["achievements"],
        "summary": buckets["summary"],
        "other": buckets["other"],
    }


def iter_section_sentences(
    sections: dict[str, Any], category: SectionKey
) -> list[tuple[str, str]]:
    """Yield (section_category, sentence) for all blocks in a section."""
    out: list[tuple[str, str]] = []
    for block in sections.get(category) or []:
        for s in block.get("sentences") or []:
            out.append((category, s))
    return out


def all_indexed_sentences(sections: dict[str, Any]) -> list[tuple[SectionKey, str]]:
    keys: list[SectionKey] = [
        "summary",
        "skills",
        "experience",
        "projects",
        "education",
        "certifications",
        "achievements",
        "other",
    ]
    out: list[tuple[SectionKey, str]] = []
    for k in keys:
        out.extend(iter_section_sentences(sections, k))
    return out
