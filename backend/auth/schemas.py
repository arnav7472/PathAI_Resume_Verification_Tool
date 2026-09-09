"""
Pydantic schemas for authentication requests and responses.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Register a new user.

    Note: the ``role`` field is accepted for API compatibility only.  Public
    registration always creates ``role="candidate"``; the client-supplied
    value is never trusted (see the register route).
    """
    email: str = Field(..., min_length=5, max_length=255)
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    role: str = Field(default="candidate", pattern="^(candidate)$")


class UserOut(BaseModel):
    """Public user info returned after registration or token verification."""
    id: int
    email: str
    username: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT access token response."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login credentials."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    """Request a password reset email."""
    email: str = Field(..., min_length=5, max_length=255)


class ResetPasswordRequest(BaseModel):
    """Submit a new password with a reset token."""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class ForgotPasswordResponse(BaseModel):
    """Response after requesting a password reset."""
    detail: str


class ResetPasswordResponse(BaseModel):
    """Response after successfully resetting the password."""
    detail: str