"""
Auth router — POST /api/auth/register, POST /api/auth/login,
POST /api/auth/forgot-password, POST /api/auth/reset-password.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import resend

from backend.db.config import get_db
from backend.db.models import User, PasswordResetToken
from backend.auth.schemas import (
    UserCreate,
    UserOut,
    Token,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordResponse,
)
from backend.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    generate_reset_token,
    hash_reset_token,
    verify_reset_token,
    get_reset_token_expiry,
    check_login_rate_limit,
    record_login_attempt,
    check_reset_rate_limit,
    record_reset_attempt,
)
from backend.auth.depends import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Resend configuration ──────────────────────────────────────────────────────

RESEND_API_KEY: str | None = os.getenv("RESEND_API_KEY")
FROM_EMAIL: str = os.getenv("FROM_EMAIL", "[EMAIL]")
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    """Register a new user. Email and username must be unique."""

    # Check email uniqueness
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    # Check username uniqueness
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists.",
        )

    # Security: public self-registration always creates "candidate".
    # The client-supplied role is never trusted for public registration.
    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="candidate",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("Registered user: id=%d username=%s role=%s", user.id, user.username, user.role)
    return UserOut.model_validate(user)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    """Authenticate with username + password, receive a JWT access token."""

    ip = request.client.host if request.client else "unknown"
    try:
        check_login_rate_limit(payload.username, ip)
    except RuntimeError as e:
        record_login_attempt(payload.username, ip, False)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )

    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        record_login_attempt(payload.username, ip, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not user.is_active:
        record_login_attempt(payload.username, ip, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated.",
        )

    record_login_attempt(payload.username, ip, True)
    token = create_access_token({"sub": user.id, "role": user.role})
    logger.info("Login: user_id=%d username=%s", user.id, user.username)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the currently authenticated user's profile."""
    return UserOut.model_validate(current_user)


# ── Password reset ────────────────────────────────────────────────────────────


def _send_reset_email(recipient: str, reset_link: str) -> bool:
    """Send the password reset email via Resend. Returns True if sent successfully."""
    if not RESEND_API_KEY:
        return False

    try:
        params: resend.Emails.SendParams = {
            "from": FROM_EMAIL,
            "to": [recipient],
            "subject": "PathAI Verify — Password Reset Request",
            "text": (
                f"Click the link below to reset your password. "
                f"This link will expire in 15 minutes.\n\n{reset_link}\n\n"
                f"If you did not request a password reset, please ignore this email."
            ),
        }
        response = resend.Emails.send(params)
        logger.info("Password reset email sent to %s (Resend id=%s)", recipient, response.get("id", "unknown"))
        return True
    except Exception as exc:
        logger.warning("Failed to send password reset email via Resend to %s: %s", recipient, exc)
        return False


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)) -> ForgotPasswordResponse:
    """Request a password reset link. Always returns 200 to prevent email enumeration."""

    ip = request.client.host if request.client else "unknown"
    try:
        check_reset_rate_limit(payload.email, ip)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    record_reset_attempt(payload.email, ip)

    user = db.query(User).filter(User.email == payload.email).first()

    if user is None:
        # Return generic success to prevent user enumeration
        logger.info("Password reset requested for unknown email: %s", payload.email)
        return ForgotPasswordResponse(detail="If an account with that email exists, a reset link has been sent.")

    # Generate and store the reset token
    raw_token = generate_reset_token()
    hashed = hash_reset_token(raw_token)
    expires_at = get_reset_token_expiry()

    reset_token_record = PasswordResetToken(
        user_id=user.id,
        hashed_token=hashed,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_token_record)
    db.commit()

    reset_link = f"{FRONTEND_URL}/reset-password?token={raw_token}"

    # Attempt to send email; if Resend not configured, log the link for development
    sent = _send_reset_email(user.email, reset_link)
    if not sent:
        logger.info(
            "Password reset link for user %s (id=%d): %s",
            user.username,
            user.id,
            reset_link,
        )

    return ForgotPasswordResponse(detail="If an account with that email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> ResetPasswordResponse:
    """Reset password using a valid, non-expired, single-use token."""

    now = datetime.now(timezone.utc)

    # Find all non-expired, unused tokens
    candidates = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > now,
        )
        .all()
    )

    # Try to match the provided token against any stored hashed token
    matched_record: PasswordResetToken | None = None
    for record in candidates:
        if verify_reset_token(payload.token, record.hashed_token):
            matched_record = record
            break

    if matched_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    # Mark as used (single-use)
    matched_record.used = True
    db.add(matched_record)

    # Update the user's password
    user = db.query(User).filter(User.id == matched_record.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found.",
        )

    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    db.commit()

    logger.info("Password reset successful: user_id=%d username=%s", user.id, user.username)
    return ResetPasswordResponse(detail="Password has been reset successfully.")