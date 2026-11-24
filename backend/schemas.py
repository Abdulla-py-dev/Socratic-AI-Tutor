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


class DocumentUploadResponse(BaseModel):
    """Schema for document upload response."""

    id: int
    original_filename: str
    stored_filename: str
    file_size: int
    page_count: int
    upload_date: datetime
    processing_status: str

    model_config = ConfigDict(from_attributes=True)


class DocumentOut(BaseModel):
    """Schema for document output (list and detail)."""

    id: int
    original_filename: str
    file_size: int
    page_count: int
    upload_date: datetime
    processing_status: str

    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(DocumentOut):
    """Schema for detailed document view (includes stored filename)."""

    stored_filename: str

    model_config = ConfigDict(from_attributes=True)