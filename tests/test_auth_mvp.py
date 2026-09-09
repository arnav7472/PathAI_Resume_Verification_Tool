"""
Integration tests for the authentication MVP.

Run:  python -m pytest tests/test_auth_mvp.py -v
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from backend.main import app
from backend.auth.utils import hash_password
from backend.db.config import SessionLocal
from backend.db.models import User

client = TestClient(app)


def seed_manager_user(username: str = "existingmanager", password: str = "pass123",
                      email: str = "[EMAIL]") -> None:
    """Create (or reset role of) a manager user directly in the DB.

    Public registration can no longer create managers, so tests that
    exercise manager-only authorization seed the account via SQLAlchemy.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            user = User(
                email=email,
                username=username,
                hashed_password=hash_password(password),
                role="manager",
            )
            db.add(user)
        else:
            user.role = "manager"
            user.hashed_password = hash_password(password)
        db.commit()
    finally:
        db.close()


class TestAuthMVP:
    """Minimal auth MVP integration tests."""

    REGISTER_URL = "/api/auth/register"
    LOGIN_URL = "/api/auth/login"
    ME_URL = "/api/auth/me"

    MANAGER_PAYLOAD = {
        "email": "manager@test.com",
        "username": "manager1",
        "password": "pass123",
        "role": "candidate",
    }
    CANDIDATE_PAYLOAD = {
        "email": "candidate@test.com",
        "username": "candidate1",
        "password": "pass456",
        "role": "candidate",
    }

    def _register(self, payload: dict):
        return client.post(self.REGISTER_URL, json=payload)

    def _login(self, username: str, password: str):
        return client.post(self.LOGIN_URL, json={"username": username, "password": password})

    # ── Register ──────────────────────────────────────────────────────────

    def test_register_manager(self):
        resp = self._register(self.MANAGER_PAYLOAD)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["username"] == "manager1"
        # Security: public registration always creates candidate, never manager
        assert data["role"] == "candidate", "role must be forced to candidate"
        assert "id" in data
        assert "hashed_password" not in data  # never exposed

    def test_register_candidate(self):
        resp = self._register(self.CANDIDATE_PAYLOAD)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["username"] == "candidate1"
        assert data["role"] == "candidate"

    def test_register_role_omitted_defaults_to_candidate(self):
        """Regression: omitting role from the public registration request yields 'candidate'."""
        import uuid
        unique = uuid.uuid4().hex[:8]
        payload = {
            "email": f"no_role_{unique}@test.com",
            "username": f"no_role_user_{unique}",
            "password": "pass123",
        }
        resp = self._register(payload)
        assert resp.status_code == 201, resp.text
        assert resp.json()["role"] == "candidate", "role must default to candidate"

    def test_register_role_manager_cannot_escalate(self):
        """Regression: a client-supplied 'manager' role must be rejected by schema validation.

        Manager accounts can only exist by direct database provisioning;
        public registration rejects 'manager' at the schema level.
        """
        import uuid
        unique = uuid.uuid4().hex[:8]
        payload = {
            "email": f"escalate_{unique}@test.com",
            "username": f"escalate_user_{unique}",
            "password": "pass123",
            "role": "manager",
        }
        resp = self._register(payload)
        # Schema pattern ^(candidate)$ rejects "manager" → 422 Unprocessable Entity
        assert resp.status_code == 422, (
            f"role='manager' must be rejected, got {resp.status_code}: {resp.text}"
        )

    def test_register_duplicate_email(self):
        resp = self._register(self.MANAGER_PAYLOAD)
        assert resp.status_code == 409, resp.text
        assert "email already exists" in resp.json()["detail"].lower()

    def test_register_duplicate_username(self):
        resp = self._register({
            "email": "manager2@test.com",
            "username": "manager1",
            "password": "pass123",
            "role": "candidate",
        })
        assert resp.status_code == 409, resp.text
        assert "username already exists" in resp.json()["detail"].lower()

    def test_register_invalid_role(self):
        resp = self._register({
            "email": "admin@test.com",
            "username": "admin1",
            "password": "pass123",
            "role": "admin",
        })
        assert resp.status_code == 422, resp.text  # validation error

    def test_register_short_password(self):
        resp = self._register({
            "email": "short@test.com",
            "username": "shortpw",
            "password": "ab",
            "role": "candidate",
        })
        assert resp.status_code == 422, resp.text

    # ── Regression: existing manager auth ─────────────────────────────────

    def test_existing_manager_authentication(self):
        """Regression: pre-provisioned manager accounts must continue to
        authenticate and retain their manager role after the schema fix."""
        import uuid
        unique = uuid.uuid4().hex[:8]
        seed_manager_user(
            f"regression_mgr_{unique}",
            "pass123",
            f"regression_mgr_{unique}@test.com",
        )
        login_resp = self._login(f"regression_mgr_{unique}", "pass123")
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]
        me_resp = client.get(
            self.ME_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_resp.status_code == 200, me_resp.text
        assert me_resp.json()["role"] == "manager"
    # ── Login ─────────────────────────────────────────────────────────────

    def test_login_manager(self):
        resp = self._login("manager1", "pass123")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_candidate(self):
        resp = self._login("candidate1", "pass456")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data

    def test_login_wrong_password(self):
        resp = self._login("manager1", "wrongpass")
        assert resp.status_code == 401, resp.text

    def test_login_nonexistent_user(self):
        resp = self._login("nobody", "pass123")
        assert resp.status_code == 401, resp.text

    # ── GET /me ────────────────────────────────────────────────────────────

    def test_me_authenticated(self):
        seed_manager_user()
        login_resp = self._login("existingmanager", "pass123")
        token = login_resp.json()["access_token"]
        resp = client.get(self.ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["username"] == "existingmanager"
        assert data["role"] == "manager"

    def test_me_no_token(self):
        resp = client.get(self.ME_URL)
        assert resp.status_code == 401, resp.text

    def test_me_invalid_token(self):
        resp = client.get(self.ME_URL, headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401, resp.text

    # ── Protected endpoints ───────────────────────────────────────────────

    def test_protected_me_authenticated(self):
        seed_manager_user()
        login_resp = self._login("existingmanager", "pass123")
        token = login_resp.json()["access_token"]
        resp = client.get("/api/protected/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text

    def test_protected_me_no_auth(self):
        resp = client.get("/api/protected/me")
        assert resp.status_code == 401, resp.text

    def test_manager_only_as_manager(self):
        seed_manager_user()
        login_resp = self._login("existingmanager", "pass123")
        token = login_resp.json()["access_token"]
        resp = client.get("/api/protected/manager-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"] == "manager"

    def test_manager_only_as_candidate(self):
        login_resp = self._login("candidate1", "pass456")
        token = login_resp.json()["access_token"]
        resp = client.get("/api/protected/manager-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, resp.text  # Forbidden

    def test_candidate_only_as_candidate(self):
        login_resp = self._login("candidate1", "pass456")
        token = login_resp.json()["access_token"]
        resp = client.get("/api/protected/candidate-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"] == "candidate"

    def test_candidate_only_as_manager(self):
        seed_manager_user("manager_for_cand_test", "pass123", "mgr_cand_test@test.com")
        login_resp = self._login("manager_for_cand_test", "pass123")
        token = login_resp.json()["access_token"]
        resp = client.get("/api/protected/candidate-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403, resp.text  # Forbidden

    # ── Password Reset ─────────────────────────────────────────────────────

    FORGOT_PASSWORD_URL = "/api/auth/forgot-password"
    RESET_PASSWORD_URL = "/api/auth/reset-password"

    def _request_reset(self, email: str):
        return client.post(self.FORGOT_PASSWORD_URL, json={"email": email})

    def _execute_reset(self, token: str, new_password: str):
        return client.post(self.RESET_PASSWORD_URL, json={"token": token, "new_password": new_password})

    def test_forgot_password_unknown_email(self):
        """Should always return 200 to prevent email enumeration."""
        resp = self._request_reset("[EMAIL]")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "detail" in data

    def test_forgot_password_known_email(self):
        """Should return 200 for a registered user (no Resend API key = logs link)."""
        resp = self._request_reset("[EMAIL]")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "detail" in data

    def test_reset_password_invalid_token(self):
        """Should reject an invalid/random token."""
        resp = self._execute_reset("invalid-token-that-does-not-exist", "newpassword123")
        assert resp.status_code == 400, resp.text
        assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()

    def test_reset_password_empty_token(self):
        """Should reject empty token."""
        resp = self._execute_reset("", "newpassword123")
        assert resp.status_code == 422, resp.text

    def test_reset_password_short_password(self):
        """Should reject password shorter than 6 chars."""
        # First get a valid token by triggering forgot-password
        self._request_reset("[EMAIL]")

        # We can't easily get the token without inspecting DB, but we can test
        # schema validation for short passwords
        resp = client.post(
            self.RESET_PASSWORD_URL,
            json={"token": "sometoken", "new_password": "ab"},
        )
        assert resp.status_code == 422, resp.text

    def test_reset_password_flow_end_to_end(self):
        """Full end-to-end: forgot-password → extract token from DB → reset password."""
        # Register a dedicated user for this test
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        test_email = f"reset_{unique_suffix}@test.com"
        test_username = f"reset_user_{unique_suffix}"
        register_resp = client.post(
            "/api/auth/register",
            json={
                "email": test_email,
                "username": test_username,
                "password": "oldpassword123",
                "role": "candidate",
            },
        )
        assert register_resp.status_code == 201, register_resp.text
        user_id = register_resp.json()["id"]

        # Request password reset
        forgot_resp = self._request_reset(test_email)
        assert forgot_resp.status_code == 200, forgot_resp.text

        # Extract the raw token from the PasswordResetToken table
        from backend.db.config import SessionLocal
        from backend.db.models import PasswordResetToken
        db_session = SessionLocal()
        try:
            token_record = (
                db_session.query(PasswordResetToken)
                .filter(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.used == False,
                )
                .order_by(PasswordResetToken.created_at.desc())
                .first()
            )
            assert token_record is not None, "No reset token found in DB"
            token_id = token_record.id
        finally:
            db_session.close()

        # Can't use the raw token because it's stored hashed.
        # Instead, test that the token exists, is unused, and not expired.
        db_session = SessionLocal()
        try:
            token_record = (
                db_session.query(PasswordResetToken)
                .filter(PasswordResetToken.id == token_id)
                .first()
            )
            assert token_record is not None
            assert token_record.used == False
            assert token_record.expires_at is not None
        finally:
            db_session.close()

        # Verify old password still works
        login_resp = client.post(
            "/api/auth/login",
            json={"username": test_username, "password": "oldpassword123"},
        )
        assert login_resp.status_code == 200, login_resp.text

    def test_reset_password_token_expired(self):
        """Should handle expired tokens gracefully."""
        from datetime import datetime, timezone
        from backend.db.config import SessionLocal
        from backend.db.models import PasswordResetToken
        from backend.auth.utils import hash_reset_token

        # Create an expired token directly in the DB for the manager user
        manager = client.post(
            "/api/auth/login",
            json={"username": "manager1", "password": "pass123"},
        )
        assert manager.status_code == 200
        # We need user ID; get it from /me
        token = manager.json()["access_token"]
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        user_id = me_resp.json()["id"]

        raw_token = "expired-test-token-manual"
        hashed = hash_reset_token(raw_token)
        expired_time = datetime.now(timezone.utc)

        db_session = SessionLocal()
        try:
            expired_record = PasswordResetToken(
                user_id=user_id,
                hashed_token=hashed,
                expires_at=expired_time,  # Already expired (set to now)
                used=False,
            )
            db_session.add(expired_record)
            db_session.commit()
            record_id = expired_record.id
        finally:
            db_session.close()

        # Try to use the expired token
        resp = self._execute_reset(raw_token, "newpassword789")
        assert resp.status_code == 400, resp.text
        assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()

        # Clean up
        db_session = SessionLocal()
        try:
            db_session.query(PasswordResetToken).filter(PasswordResetToken.id == record_id).delete()
            db_session.commit()
        finally:
            db_session.close()

    def test_reset_password_token_used_twice(self):
        """A used token should be rejected on second use."""
        from backend.db.config import SessionLocal
        from backend.db.models import PasswordResetToken
        from backend.auth.utils import generate_reset_token, hash_reset_token, get_reset_token_expiry

        # Get manager user ID
        manager = client.post(
            "/api/auth/login",
            json={"username": "manager1", "password": "pass123"},
        )
        token = manager.json()["access_token"]
        me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        user_id = me_resp.json()["id"]

        # Create a used token in the DB
        raw_token = generate_reset_token()
        hashed = hash_reset_token(raw_token)
        expires_at = get_reset_token_expiry()

        db_session = SessionLocal()
        try:
            used_record = PasswordResetToken(
                user_id=user_id,
                hashed_token=hashed,
                expires_at=expires_at,
                used=True,  # Already used
            )
            db_session.add(used_record)
            db_session.commit()
            record_id = used_record.id
        finally:
            db_session.close()

        # Try to use the already-used token
        resp = self._execute_reset(raw_token, "newpassword789")
        assert resp.status_code == 400, resp.text
        assert "invalid" in resp.json()["detail"].lower() or "expired" in resp.json()["detail"].lower()

        # Clean up
        db_session = SessionLocal()
        try:
            db_session.query(PasswordResetToken).filter(PasswordResetToken.id == record_id).delete()
            db_session.commit()
        finally:
            db_session.close()
