"""Deterministic PDF report generator for resume verification results.

Uses reportlab to produce recruiter-friendly PDFs with no randomness.
Sections: header, executive summary, key metrics, positive evidence,
missing skills, findings, timeline warnings, extraction warnings, manual review.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _to_risk_label(risk_score: int) -> str:
    if risk_score >= 70:
        return "High Risk"
    if risk_score >= 35:
        return "Medium Risk"
    return "Low Risk"


def _wrap(text: str, max_len: int = 900) -> str:
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _safe_str(val: Any) -> str:
    return str(val) if val is not None else ""


def build_pdf_report(analysis: dict[str, Any]) -> bytes:
    """Generate a deterministic PDF report from the analysis dict.

    The input matches the shape returned by verification/pipeline.py:analyze_resume.
    Returns bytes ready for HTTP response.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    # Custom styles — clean, minimal, professional
    styles.add(
        ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            spaceAfter=4,
            textColor=colors.HexColor("#1a1a1a"),
        )
    )
    styles.add(
        ParagraphStyle(
            "SubTitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#666666"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionHead",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=14,
            spaceAfter=6,
            textColor=colors.HexColor("#2b2b2b"),
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricValue",
            parent=styles["Normal"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1a1a1a"),
            spaceBefore=2,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            "MetricLabel",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#888888"),
            spaceBefore=0,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "BodyText2",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#333333"),
        )
    )
    styles.add(
        ParagraphStyle(
            "SmallNote",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#999999"),
        )
    )
    styles.add(
        ParagraphStyle(
            "WarningText",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#b8860b"),
        )
    )

    elements: list = []

    # ── Extract values (with safe defaults) ──────────────────────────────────
    compatibility = analysis.get("compatibility_score", 0) or 0
    confidence = analysis.get("confidence", 0) or 0
    risk_score = analysis.get("risk_score", 0) or 0
    executive_summary = _safe_str(analysis.get("executive_summary", ""))
    positive_evidence = analysis.get("positive_evidence_summary") or []
    matched_skills = analysis.get("matched_skills") or []
    missing_skills = analysis.get("missing_skills") or []
    findings = analysis.get("findings") or []
    timeline_analysis = analysis.get("timeline_analysis") or {}
    timeline_warnings = []
    timeline_warnings.extend(timeline_analysis.get("overlaps", []))
    timeline_warnings.extend(timeline_analysis.get("gaps", []))
    timeline_warnings.extend(timeline_analysis.get("suspicious_inflation", []))
    extraction_warnings = analysis.get("extraction_warnings", []) or []
    claims = analysis.get("claims") or []

    # ── Title Block ────────────────────────────────────────────────────────────
    elements.append(Paragraph("Resume Verification Report", styles["DocTitle"]))
    ts = datetime.now().strftime("%B %d, %Y at %H:%M")
    elements.append(Paragraph(f"Generated {ts}", styles["SubTitle"]))
    elements.append(Spacer(1, 4 * mm))

    # ── Executive Summary ──────────────────────────────────────────────────────
    if executive_summary:
        elements.append(Paragraph("Executive Summary", styles["SectionHead"]))
        elements.append(Paragraph(executive_summary, styles["BodyText2"]))
        elements.append(Spacer(1, 2 * mm))

    # ── Key Metrics Table ──────────────────────────────────────────────────────
    elements.append(Paragraph("Key Metrics", styles["SectionHead"]))
    risk_label = _to_risk_label(risk_score)
    metrics_data = [
        [
            Paragraph(
                f'<para alignment="CENTER">{compatibility}%<br/><font size="7" color="#888888">Compatibility</font></para>',
                styles["MetricValue"],
            ),
            Paragraph(
                f'<para alignment="CENTER">{confidence}%<br/><font size="7" color="#888888">Confidence</font></para>',
                styles["MetricValue"],
            ),
            Paragraph(
                f'<para alignment="CENTER">{risk_score}<br/><font size="7" color="#888888">Risk Score</font></para>',
                styles["MetricValue"],
            ),
            Paragraph(
                f'<para alignment="CENTER">{risk_label}<br/><font size="7" color="#888888">Risk Level</font></para>',
                styles["MetricValue"],
            ),
        ]
    ]
    mt = Table(metrics_data, colWidths=[42 * mm] * 4)
    mt.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(mt)
    elements.append(Spacer(1, 3 * mm))

    # ── Skills Overview ────────────────────────────────────────────────────────
    elements.append(Paragraph("Skills Overview", styles["SectionHead"]))
    skills_text = ""
    if matched_skills:
        skills_text += (
            f"<b>Matched Skills ({len(matched_skills)}):</b> "
            + ", ".join(matched_skills[:20])
            + "<br/>"
        )
    if missing_skills:
        skills_text += (
            f"<b>Missing Skills ({len(missing_skills)}):</b> "
            + ", ".join(missing_skills[:20])
        )
    if not skills_text:
        skills_text = "No job description provided — skills not evaluated against external requirements."
    elements.append(Paragraph(skills_text, styles["BodyText2"]))
    elements.append(Spacer(1, 2 * mm))

    # ── Positive Evidence ──────────────────────────────────────────────────────
    if positive_evidence:
        elements.append(Paragraph("Positive Evidence", styles["SectionHead"]))
        for note in positive_evidence[:8]:
            elements.append(
                Paragraph(f"• {_wrap(note, 600)}", styles["BodyText2"])
            )
        elements.append(Spacer(1, 2 * mm))

    # ── Findings ───────────────────────────────────────────────────────────────
    if findings:
        elements.append(Paragraph("Findings & Manual Review", styles["SectionHead"]))
        for f in findings[:12]:
            sev = _safe_str(f.get("severity", "info"))
            msg = _wrap(_safe_str(f.get("message", "")), 700)
            elements.append(Paragraph(
                f"<b>[{sev.upper()}]</b> {msg}",
                styles["WarningText"] if sev in ("high", "medium") else styles["BodyText2"],
            ))
        elements.append(Spacer(1, 2 * mm))
    else:
        elements.append(Paragraph("Findings & Manual Review", styles["SectionHead"]))
        elements.append(Paragraph(
            "No significant findings. All claims appear consistent with resume evidence.",
            styles["BodyText2"],
        ))
        elements.append(Spacer(1, 2 * mm))

    # ── Timeline Warnings ──────────────────────────────────────────────────────
    if timeline_warnings:
        elements.append(Paragraph("Timeline Analysis", styles["SectionHead"]))
        for tw in timeline_warnings[:8]:
            elements.append(
                Paragraph(f"• {_wrap(tw, 700)}", styles["WarningText"])
            )
        elements.append(Spacer(1, 2 * mm))

    # ── Extraction Warnings ────────────────────────────────────────────────────
    if extraction_warnings:
        elements.append(Paragraph("Extraction Quality Notice", styles["SectionHead"]))
        for ew in extraction_warnings[:4]:
            elements.append(
                Paragraph(f"• {_wrap(ew, 700)}", styles["WarningText"])
            )
        elements.append(
            Paragraph(
                "Low-quality text extraction may reduce verification accuracy. "
                "Consider reviewing the original document for confirmation.",
                styles["SmallNote"],
            )
        )
        elements.append(Spacer(1, 2 * mm))

    # ── Manual Review Note ─────────────────────────────────────────────────────
    elements.append(Paragraph("Recruiter Notes", styles["SectionHead"]))
    elements.append(
        Paragraph(
            "This report is an automated screening aid. "
            "All findings should be verified through manual review before making hiring decisions. "
            "Claims labeled as 'weak' or 'missing' may still be valid but lack strong evidence "
            "in the parsed resume text.",
            styles["SmallNote"],
        )
    )
    elements.append(Spacer(1, 2 * mm))

    # ── Footer ─────────────────────────────────────────────────────────────────
    elements.append(
        Paragraph(
            f"Generated by Path-ai Verify | {ts}",
            styles["SmallNote"],
        )
    )

    doc.build(elements)
    return buf.getvalue()