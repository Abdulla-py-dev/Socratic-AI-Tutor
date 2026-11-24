"""
Pydantic schemas for request/response validation and serialization.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentRegister(BaseModel):
    """Schema for student registration input."""

    full_name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)


class StudentLogin(BaseModel):
    """Schema for student login input."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class StudentOut(BaseModel):
    """Schema for safe student output (no sensitive fields)."""

    id: int
    full_name: str
    email: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)