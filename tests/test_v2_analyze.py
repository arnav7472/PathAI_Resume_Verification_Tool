"""Focused tests for POST /v2/analyze and its persistence layer (backend/llm/).

Covers: auth/role gating, request validation, error handling, successful
end-to-end persistence of the six typed pipeline artifacts, and ownership
isolation of stored V2Analysis rows.

Run:  python -m pytest tests/test_v2_analyze.py -v
"""

from __future__ import annotations

import os

# Use a file-based SQLite database so tables are shared across connections/threads.
os.environ["DATABASE_URL"] = "sqlite:///test_v2_analyze.db"

from fastapi.testclient import TestClient

from backend.main import app
from backend.db.config import engine, Base, get_db, init_db
from backend.db.models import V2Analysis

init_db()

client = TestClient(app)

ANALYZE_URL = "/v2/analyze"
REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"

SAMPLE_RESUME = (
    "Senior Backend Engineer at TechCorp (2018-2024)\n"
    "- Architected microservices using Python and FastAPI\n"
    "- Managed Docker and Kubernetes deployments\n\n"
    "MS Computer Science, University (2014-2016)\n\n"
    "Skills: Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS"
)

SAMPLE_JD = (
    "Job Title: Junior Python Developer\n"
    "Location: New York, NY\n"
    "Requirements: 2+ years experience with Python and FastAPI.\n"
    "Bachelor degree required.\n"
    "Remote allowed."
)


class TestV2Analyze:
    def setup_method(self):
        Base.metadata.drop_all(bind=engine)
        init_db()

    def teardown_method(self):
        Base.metadata.drop_all(bind=engine)
        try:
            if os.path.exists("test_v2_analyze.db"):
                os.remove("test_v2_analyze.db")
        except Exception:
            pass

    def _register_and_login(self, email: str, username: str, role: str) -> str:
        reg = client.post(
            REGISTER_URL,
            json={"email": email, "username": username, "password": "password123", "role": role},
        )
        assert reg.status_code == 201, reg.text
        login = client.post(LOGIN_URL, json={"username": username, "password": "password123"})
        assert login.status_code == 200, login.text
        return login.json()["access_token"]

    def _manager_headers(self, suffix: str = "a") -> dict[str, str]:
        token = self._register_and_login(f"mgr{suffix}@test.com", f"mgr{suffix}", "manager")
        return {"Authorization": f"Bearer {token}"}

    # ── Auth / role gating ────────────────────────────────────────────────

    def test_requires_authentication(self):
        resp = client.post(
            ANALYZE_URL,
            json={"candidate_name": "A", "resume_text": SAMPLE_RESUME, "job_description": SAMPLE_JD},
        )
        assert resp.status_code == 401

    def test_requires_manager_role(self):
        token = self._register_and_login("cand@test.com", "cand", "candidate")
        resp = client.post(
            ANALYZE_URL,
            json={"candidate_name": "A", "resume_text": SAMPLE_RESUME, "job_description": SAMPLE_JD},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    # ── Validation ────────────────────────────────────────────────────────

    def test_rejects_missing_fields(self):
        headers = self._manager_headers()
        resp = client.post(ANALYZE_URL, json={"candidate_name": "A"}, headers=headers)
        assert resp.status_code == 422

    def test_rejects_whitespace_only_resume_text(self):
        headers = self._manager_headers()
        resp = client.post(
            ANALYZE_URL,
            json={"candidate_name": "A", "resume_text": "   ", "job_description": SAMPLE_JD},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "resume_text" in resp.json()["detail"]

    def test_rejects_whitespace_only_job_description(self):
        headers = self._manager_headers()
        resp = client.post(
            ANALYZE_URL,
            json={"candidate_name": "A", "resume_text": SAMPLE_RESUME, "job_description": "  \n "},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "job_description" in resp.json()["detail"]

    def test_rejects_whitespace_only_candidate_name(self):
        headers = self._manager_headers()
        resp = client.post(
            ANALYZE_URL,
            json={"candidate_name": "  ", "resume_text": SAMPLE_RESUME, "job_description": SAMPLE_JD},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "candidate_name" in resp.json()["detail"]

    # ── Successful end-to-end persistence ────────────────────────────────

    def test_analyze_returns_all_six_artifacts_and_persists(self):
        headers = self._manager_headers()
        resp = client.post(
            ANALYZE_URL,
            json={
                "candidate_name": "Jane Doe",
                "resume_text": SAMPLE_RESUME,
                "job_description": SAMPLE_JD,
            },
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        # Response shape: all six typed artifacts present.
        assert body["candidate_name"] == "Jane Doe"
        assert isinstance(body["id"], int)
        for key in (
            "candidate_profile", "job_profile", "match_analysis",
            "match_score", "explanation", "skill_gaps",
        ):
            assert key in body

        assert "python" in body["candidate_profile"]["skills"]
        assert 0 <= body["match_score"]["overall_score"] <= 100
        assert body["explanation"]["recommendation"]
        assert isinstance(body["skill_gaps"]["coverage_percentage"], (int, float))

        # Persistence: row exists, owned by the requesting user, JSON round-trips.
        db = next(get_db())
        try:
            record = db.query(V2Analysis).filter(V2Analysis.id == body["id"]).first()
            assert record is not None
            assert record.candidate_name == "Jane Doe"
            assert record.overall_score == body["match_score"]["overall_score"]
            import json
            assert json.loads(record.candidate_profile) == body["candidate_profile"]
            assert json.loads(record.match_score) == body["match_score"]
        finally:
            db.close()

    def test_analyses_are_owned_per_user(self):
        headers_a = self._manager_headers("a")
        headers_b = self._manager_headers("b")

        resp_a = client.post(
            ANALYZE_URL,
            json={"candidate_name": "A", "resume_text": SAMPLE_RESUME, "job_description": SAMPLE_JD},
            headers=headers_a,
        )
        assert resp_a.status_code == 200, resp_a.text
        analysis_id = resp_a.json()["id"]

        db = next(get_db())
        try:
            from backend.db.models import User
            from backend.llm.service import get_analysis_by_id

            user_a = db.query(User).filter(User.username == "mgra").first()
            user_b = db.query(User).filter(User.username == "mgrb").first()

            assert get_analysis_by_id(db, analysis_id, user_a.id) is not None
            assert get_analysis_by_id(db, analysis_id, user_b.id) is None
        finally:
            db.close()
