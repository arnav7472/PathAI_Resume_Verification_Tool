"""Integration test for the PDF generation endpoint — validates response shape and PDF integrity."""
from __future__ import annotations

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestPdfEndpoint:
    """Validate the /report/pdf endpoint responds with a valid PDF."""

    def test_pdf_endpoint_returns_pdf(self):
        payload = {
            "text": "Experienced Python developer with 5 years in FastAPI and Docker.",
            "job_description": "Looking for Python, FastAPI, Docker engineers.",
            "strictness": "medium",
            "cross_reference_sync": True,
        }
        resp = client.post("/report/pdf", json=payload)
        assert resp.status_code == 200, f"Expected 200 got {resp.status_code}"
        assert resp.headers.get("content-type") == "application/pdf"
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert resp.content.startswith(b"%PDF"), "Not a valid PDF header"
        assert len(resp.content) > 1000, f"PDF too small: {len(resp.content)}"

    def test_pdf_endpoint_empty_text_returns_422(self):
        resp = client.post("/report/pdf", json={"text": ""})
        assert resp.status_code == 422

    def test_pdf_endpoint_missing_text_returns_422(self):
        resp = client.post("/report/pdf", json={})
        assert resp.status_code == 422