"""
SQLAlchemy ORM models for the persistence MVP.

Tables:
  - users:            authentication users
  - jobs:             job descriptions used in ranking sessions
  - candidates:       candidate names and resume texts
  - rankings:         ranking sessions (one per /rank or /rank-files call)
  - ranking_candidates: individual candidate results within a ranking session
  - reports:          persisted verification reports owned by users
  - password_reset_tokens: single-use 15-minute password reset tokens
  - v2_analyses:       persisted backend/llm six-stage pipeline results (POST /v2/analyze)
"""

from __future__ import annotations

import datetime

from sqlalchemy import Column, Integer, Float, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from backend.db.config import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="candidate")  # "manager" | "candidate"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text, nullable=False)
    strictness = Column(String(16), nullable=False, default="medium")
    cross_reference_sync = Column(Integer, nullable=False, default=1)  # boolean as int
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    rankings = relationship("Ranking", back_populates="job")

    def __repr__(self) -> str:
        return f"<Job id={self.id}>"


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    ranking_entries = relationship("RankingCandidate", back_populates="candidate")

    def __repr__(self) -> str:
        return f"<Candidate id={self.id} name={self.name!r}>"


class Ranking(Base):
    __tablename__ = "rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    job = relationship("Job", back_populates="rankings")
    candidate_results = relationship(
        "RankingCandidate",
        back_populates="ranking",
        order_by="RankingCandidate.rank_score.desc()",
    )

    def __repr__(self) -> str:
        return f"<Ranking id={self.id}>"


class RankingCandidate(Base):
    __tablename__ = "ranking_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ranking_id = Column(Integer, ForeignKey("rankings.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    rank_score = Column(Float, nullable=False)
    compatibility = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    risk = Column(Float, nullable=False)
    # Full analysis payload stored as JSON (from analyze_resume pipeline)
    analysis_data = Column(Text, nullable=True)

    ranking = relationship("Ranking", back_populates="candidate_results")
    candidate = relationship("Candidate", back_populates="ranking_entries")

    def __repr__(self) -> str:
        return f"<RankingCandidate ranking_id={self.ranking_id} candidate_id={self.candidate_id} score={self.rank_score}>"


class Report(Base):
    """Persisted verification report owned by a user."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    candidate_name = Column(String(500), nullable=False, default="Unknown Candidate")
    job_description = Column(Text, nullable=False, default="")
    risk_score = Column(Integer, nullable=False, default=0)
    confidence = Column(Integer, nullable=False, default=0)
    compatibility_score = Column(Integer, nullable=False, default=0)
    verdict = Column(String(50), nullable=False, default="unknown")
    strictness = Column(String(16), nullable=False, default="medium")
    cross_reference_sync = Column(Integer, nullable=False, default=1)  # boolean as int
    # Full analysis payload stored as JSON
    analysis_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} user_id={self.user_id} candidate={self.candidate_name!r}>"


class PasswordResetToken(Base):
    """Single-use, time-limited password reset token (hashed stored)."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hashed_token = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<PasswordResetToken id={self.id} user_id={self.user_id} used={self.used}>"


class V2Analysis(Base):
    """Persisted result of the V2 six-stage AI pipeline (backend/llm), owned by a user.

    Each stage output (CandidateProfile, JobProfile, MatchAnalysis, MatchScore,
    Explanation, SkillGaps) is stored as its own JSON text column, following the
    same Text-column-holds-JSON convention used by Report.analysis_data.
    """

    __tablename__ = "v2_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    candidate_name = Column(String(500), nullable=False, default="Unknown Candidate")
    job_description = Column(Text, nullable=False, default="")
    overall_score = Column(Integer, nullable=False, default=0)
    candidate_profile = Column(Text, nullable=False)
    job_profile = Column(Text, nullable=False)
    match_analysis = Column(Text, nullable=False)
    match_score = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    skill_gaps = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<V2Analysis id={self.id} user_id={self.user_id} candidate={self.candidate_name!r} overall_score={self.overall_score}>"