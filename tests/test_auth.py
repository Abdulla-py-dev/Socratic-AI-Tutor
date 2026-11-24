"""
Automated tests for Phase 2: Student Authentication.

Tests cover:
- Student registration (valid, duplicate email, validation)
- Student login (valid, invalid password, nonexistent email)
- Protected endpoint /auth/me (authenticated, unauthenticated, invalid token)
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment variables BEFORE importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_socratic_tutor.db")

from backend.config import settings  # noqa: E402
from backend.database import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import Student  # noqa: E402

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_socratic_tutor.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,  # Avoid connection pooling for clean file deletion on Windows
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override get_db dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create test tables once per module."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    # Dispose engine to release file lock on Windows
    test_engine.dispose()
    # Clean up test database file (ignore permission errors on Windows)
    try:
        Path("./test_socratic_tutor.db").unlink(missing_ok=True)
    except PermissionError:
        pass  # File locked by another process; will be cleaned up on next run


@pytest.fixture(autouse=True)
def clean_students():
    """Clean students table before each test for isolation."""
    db = TestingSessionLocal()
    db.query(Student).delete()
    db.commit()
    db.close()
    yield


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------

def test_register_student():
    """Test successful student registration."""
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Johnson",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["id"] == 1
    assert data["full_name"] == "Alice Johnson"
    assert data["email"] == "alice@example.com"
    assert "hashed_password" not in data
    assert data["created_at"] is not None


def test_register_duplicate_email():
    """Test registration with an already registered email."""
    # First registration
    client.post(
        "/auth/register",
        json={
            "full_name": "Alice Johnson",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    # Second registration with same email
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Alice Smith",
            "email": "alice@example.com",
            "password": "anotherpass",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_register_validation_error():
    """Test registration with invalid input (missing fields, bad email)."""
    # Missing password
    response = client.post(
        "/auth/register",
        json={"full_name": "Bob", "email": "bob@example.com"},
    )
    assert response.status_code == 422

    # Invalid email
    response = client.post(
        "/auth/register",
        json={"full_name": "Bob", "email": "not-an-email", "password": "pass123"},
    )
    assert response.status_code == 422

    # Password too short
    response = client.post(
        "/auth/register",
        json={"full_name": "Bob", "email": "bob@example.com", "password": "123"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login Tests
# ---------------------------------------------------------------------------

def test_login_valid():
    """Test successful login returns JWT token."""
    # Register first
    client.post(
        "/auth/register",
        json={
            "full_name": "Alice Johnson",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    # Login
    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_login_invalid_password():
    """Test login with wrong password returns 401."""
    client.post(
        "/auth/register",
        json={
            "full_name": "Alice Johnson",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_email():
    """Test login with nonexistent email returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "anypassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


# ---------------------------------------------------------------------------
# Protected Endpoint Tests
# ---------------------------------------------------------------------------

def test_me_authenticated():
    """Test GET /auth/me with valid token returns student info."""
    # Register and login
    client.post(
        "/auth/register",
        json={
            "full_name": "Alice Johnson",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "securepass123"},
    )
    token = login_resp.json()["access_token"]

    # Access protected endpoint
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == 1
    assert data["full_name"] == "Alice Johnson"
    assert data["email"] == "alice@example.com"
    assert "hashed_password" not in data


def test_me_unauthenticated():
    """Test GET /auth/me without token returns 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    # OAuth2PasswordBearer returns "Not authenticated" when no header is provided
    assert response.json()["detail"] in ("Could not validate credentials", "Not authenticated")


def test_me_invalid_token():
    """Test GET /auth/me with invalid token returns 401."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_me_expired_token():
    """Test GET /auth/me with expired token returns 401."""
    # Manually create an expired token
    from backend.auth import create_access_token
    from datetime import timedelta

    expired_token = create_access_token(
        data={"sub": "alice@example.com"},
        expires_delta=timedelta(seconds=-10),
    )
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Security Tests
# ---------------------------------------------------------------------------

def test_password_not_stored_in_plaintext():
    """Verify passwords are hashed, not stored in plaintext."""
    client.post(
        "/auth/register",
        json={
            "full_name": "Alice Johnson",
            "email": "alice@example.com",
            "password": "securepass123",
        },
    )
    db = TestingSessionLocal()
    student = db.query(Student).filter(Student.email == "alice@example.com").first()
    db.close()

    assert student is not None
    assert student.hashed_password != "securepass123"
    assert student.hashed_password.startswith("$2b$")  # bcrypt hash prefix


def test_jwt_signature_verification():
    """Test that tokens with wrong signature are rejected."""
    # Create a token with a different secret
    from jose import jwt
    wrong_token = jwt.encode(
        {"sub": "alice@example.com"},
        "wrong-secret-key",
        algorithm="HS256",
    )
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert response.status_code == 401