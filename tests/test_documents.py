"""
Automated tests for Phase 3: PDF Study Material Management.

Tests cover:
- Document upload (valid PDF, invalid file types, size limits)
- Document listing (own documents only)
- Document detail (ownership enforcement)
- Document deletion (ownership enforcement, file cleanup)
"""

import os
import tempfile
from pathlib import Path
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment variables BEFORE importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_socratic_tutor.db")
os.environ.setdefault("UPLOAD_DIR", "./test_uploads")

from backend.config import settings  # noqa: E402
# Override upload_dir for tests (settings is a singleton, so we patch it)
settings.upload_dir = "./test_uploads"
from backend.database import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import Document, Student  # noqa: E402

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_socratic_tutor.db"
TEST_UPLOAD_DIR = Path("./test_uploads")

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool,
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
    TEST_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    # Clean up test database file (ignore permission errors on Windows)
    try:
        Path("./test_socratic_tutor.db").unlink(missing_ok=True)
    except PermissionError:
        pass
    # Clean up test upload directory
    import shutil
    try:
        shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clean_data():
    """Clean students and documents tables before each test for isolation."""
    db = TestingSessionLocal()
    db.query(Document).delete()
    db.query(Student).delete()
    db.commit()
    db.close()
    # Clean upload directory
    import shutil
    try:
        shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)
    except Exception:
        pass
    TEST_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


# Helper functions
def create_test_student(email: str = "test@example.com", password: str = "testpass123"):
    """Create a test student and return auth token."""
    client.post(
        "/auth/register",
        json={"full_name": "Test User", "email": email, "password": password},
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    return login_resp.json()["access_token"]


def create_test_pdf(content: str = "Hello World") -> bytes:
    """Create a minimal valid PDF for testing."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Upload Tests
# ---------------------------------------------------------------------------

def test_upload_valid_pdf():
    """Test uploading a valid PDF document."""
    token = create_test_student()

    pdf_content = create_test_pdf("Test PDF Content")
    files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}

    response = client.post(
        "/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["id"] == 1
    assert data["original_filename"] == "test.pdf"
    assert data["file_size"] == len(pdf_content)
    assert data["page_count"] == 1
    assert data["processing_status"] in ("completed", "completed_with_warnings")
    assert "stored_filename" in data
    assert data["stored_filename"].endswith(".pdf")


def test_upload_rejects_non_pdf():
    """Test that non-PDF files are rejected."""
    token = create_test_student()

    files = {"file": ("test.txt", BytesIO(b"not a pdf"), "text/plain")}

    response = client.post(
        "/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_upload_rejects_invalid_pdf_signature():
    """Test that files without PDF signature are rejected."""
    token = create_test_student()

    files = {"file": ("fake.pdf", BytesIO(b"This is not a PDF"), "application/pdf")}

    response = client.post(
        "/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "Invalid PDF file" in response.json()["detail"]


def test_upload_rejects_oversized_file():
    """Test that files exceeding size limit are rejected."""
    token = create_test_student()

    # Create a file larger than 20MB
    large_content = b"x" * (21 * 1024 * 1024)
    # Need a valid PDF structure for signature check
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "x" * 100000)  # Large text
    pdf_bytes = doc.tobytes()
    doc.close()

    # If still not large enough, pad it
    if len(pdf_bytes) < 21 * 1024 * 1024:
        pdf_bytes = pdf_bytes + b"x" * (21 * 1024 * 1024 - len(pdf_bytes))

    files = {"file": ("large.pdf", BytesIO(pdf_bytes), "application/pdf")}

    response = client.post(
        "/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert "exceeds maximum allowed size" in response.json()["detail"]


def test_upload_requires_authentication():
    """Test that upload requires valid authentication."""
    pdf_content = create_test_pdf("Test PDF Content")
    files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}

    response = client.post(
        "/documents/upload",
        files=files,
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# List Documents Tests
# ---------------------------------------------------------------------------

def test_list_documents_returns_own_documents():
    """Test that list returns only current student's documents."""
    token1 = create_test_student("user1@example.com")
    token2 = create_test_student("user2@example.com")

    # User 1 uploads a document
    pdf_content = create_test_pdf("User 1 Document")
    files = {"file": ("doc1.pdf", BytesIO(pdf_content), "application/pdf")}
    client.post("/documents/upload", files=files, headers={"Authorization": f"Bearer {token1}"})

    # User 2 uploads a document
    pdf_content = create_test_pdf("User 2 Document")
    files = {"file": ("doc2.pdf", BytesIO(pdf_content), "application/pdf")}
    client.post("/documents/upload", files=files, headers={"Authorization": f"Bearer {token2}"})

    # User 1 lists documents
    response = client.get("/documents", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["original_filename"] == "doc1.pdf"

    # User 2 lists documents
    response = client.get("/documents", headers={"Authorization": f"Bearer {token2}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["original_filename"] == "doc2.pdf"


def test_list_documents_empty_for_new_user():
    """Test that new users have empty document list."""
    token = create_test_student("newuser@example.com")

    response = client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_documents_requires_auth():
    """Test that listing documents requires authentication."""
    response = client.get("/documents")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Get Document Detail Tests
# ---------------------------------------------------------------------------

def test_get_document_detail_own():
    """Test getting detail of own document."""
    token = create_test_student()

    pdf_content = create_test_pdf("Test Document")
    files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload", files=files, headers={"Authorization": f"Bearer {token}"}
    )
    doc_id = upload_resp.json()["id"]

    response = client.get(
        f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["original_filename"] == "test.pdf"
    assert "stored_filename" in data


def test_get_document_detail_not_found():
    """Test getting detail of non-existent document."""
    token = create_test_student()

    response = client.get(
        "/documents/999", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_get_document_detail_other_user():
    """Test that users cannot access other users' documents."""
    token1 = create_test_student("user1@example.com")
    token2 = create_test_student("user2@example.com")

    pdf_content = create_test_pdf("User 1 Document")
    files = {"file": ("doc1.pdf", BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload", files=files, headers={"Authorization": f"Bearer {token1}"}
    )
    doc_id = upload_resp.json()["id"]

    # User 2 tries to access User 1's document
    response = client.get(
        f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token2}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_get_document_detail_requires_auth():
    """Test that getting document detail requires authentication."""
    token = create_test_student()
    pdf_content = create_test_pdf("Test Document")
    files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload", files=files, headers={"Authorization": f"Bearer {token}"}
    )
    doc_id = upload_resp.json()["id"]

    response = client.get(f"/documents/{doc_id}")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Delete Document Tests
# ---------------------------------------------------------------------------

def test_delete_own_document():
    """Test deleting own document removes file and DB record."""
    token = create_test_student()

    pdf_content = create_test_pdf("Test Document")
    files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload", files=files, headers={"Authorization": f"Bearer {token}"}
    )
    doc_id = upload_resp.json()["id"]
    stored_filename = upload_resp.json()["stored_filename"]

    # Verify file exists
    file_path = TEST_UPLOAD_DIR / stored_filename
    assert file_path.exists()

    # Delete document
    response = client.delete(
        f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

    # Verify file deleted
    assert not file_path.exists()

    # Verify DB record gone
    response = client.get(
        f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_delete_other_user_document():
    """Test that users cannot delete other users' documents."""
    token1 = create_test_student("user1@example.com")
    token2 = create_test_student("user2@example.com")

    pdf_content = create_test_pdf("User 1 Document")
    files = {"file": ("doc1.pdf", BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload", files=files, headers={"Authorization": f"Bearer {token1}"}
    )
    doc_id = upload_resp.json()["id"]

    # User 2 tries to delete User 1's document
    response = client.delete(
        f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token2}"}
    )

    assert response.status_code == 404

    # Verify document still exists for User 1
    response = client.get(
        f"/documents/{doc_id}", headers={"Authorization": f"Bearer {token1}"}
    )
    assert response.status_code == 200


def test_delete_nonexistent_document():
    """Test deleting non-existent document returns 404."""
    token = create_test_student()

    response = client.delete(
        "/documents/999", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404


def test_delete_document_requires_auth():
    """Test that deleting document requires authentication."""
    token = create_test_student()
    pdf_content = create_test_pdf("Test Document")
    files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload", files=files, headers={"Authorization": f"Bearer {token}"}
    )
    doc_id = upload_resp.json()["id"]

    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

def test_upload_pdf_with_no_text():
    """Test uploading a PDF with no extractable text (image-based)."""
    token = create_test_student()

    # Create a PDF with no text content (empty page)
    import fitz
    doc = fitz.open()
    doc.new_page()  # Empty page
    pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": ("empty.pdf", BytesIO(pdf_bytes), "application/pdf")}

    response = client.post(
        "/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should succeed but with warning status
    assert response.status_code == 201
    data = response.json()
    assert data["processing_status"] == "completed_with_warnings"


def test_multiple_uploads_same_student():
    """Test multiple document uploads for same student."""
    token = create_test_student()

    for i in range(3):
        pdf_content = create_test_pdf(f"Document {i}")
        files = {"file": (f"doc{i}.pdf", BytesIO(pdf_content), "application/pdf")}
        response = client.post(
            "/documents/upload", files=files, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201

    # List should show all 3
    response = client.get("/documents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_filename_path_traversal_protection():
    """Test that malicious filenames are sanitized."""
    token = create_test_student()

    pdf_content = create_test_pdf("Test")
    # Try path traversal in filename
    files = {"file": ("../../../etc/passwd.pdf", BytesIO(pdf_content), "application/pdf")}

    response = client.post(
        "/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.json()
    # Stored filename should be UUID-based, not the original
    assert data["stored_filename"].endswith(".pdf")
    assert ".." not in data["stored_filename"]
    assert "etc" not in data["stored_filename"]
    assert "passwd" not in data["stored_filename"]