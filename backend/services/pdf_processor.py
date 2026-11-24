"""
PDF processing service for extracting text from uploaded PDF documents.

Uses PyMuPDF (fitz) for text extraction and PDF validation.
Handles corrupted, password-protected, and empty PDFs safely.
"""

import os
import uuid
from pathlib import Path
from typing import BinaryIO

import fitz  # PyMuPDF

from backend.config import settings


MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}
PDF_SIGNATURE = b"%PDF"


def get_upload_dir() -> Path:
    """Get the upload directory, creating it if necessary."""
    upload_dir = Path(settings.upload_dir) if hasattr(settings, "upload_dir") else Path("./uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def generate_stored_filename(original_filename: str) -> str:
    """
    Generate a unique, secure stored filename.

    Uses UUID to prevent collisions and path traversal attacks.
    Preserves the .pdf extension for clarity.
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".pdf"
    return f"{uuid.uuid4().hex}{ext}"


def validate_pdf_file(file: BinaryIO, filename: str) -> tuple[bool, str]:
    """
    Validate uploaded file is a PDF.

    Checks:
    - File extension
    - MIME type (from filename)
    - PDF magic bytes/signature
    - File size limit

    Returns (is_valid, error_message).
    """
    # Check file extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file extension. Only .pdf files are allowed."

    # Check file size by seeking to end
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)} MB."

    if file_size == 0:
        return False, "Empty file."

    # Check PDF signature (magic bytes)
    header = file.read(4)
    file.seek(0)

    if header != PDF_SIGNATURE:
        return False, "Invalid PDF file: missing PDF signature."

    return True, ""


def extract_text_from_pdf(filepath: Path) -> tuple[list[str], int, str]:
    """
    Extract text from PDF using PyMuPDF.

    Returns:
        - List of page texts (empty string for pages with no extractable text)
        - Total page count
        - Error message (empty if successful)
    """
    try:
        doc = fitz.open(filepath)
    except fitz.FileDataError as e:
        return [], 0, f"Corrupted or invalid PDF: {e}"
    except Exception as e:
        return [], 0, f"Failed to open PDF: {e}"

    page_count = len(doc)
    page_texts = []

    try:
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text("text")  # Extract plain text
            page_texts.append(text.strip())
    except Exception as e:
        doc.close()
        return [], 0, f"Failed to extract text from PDF: {e}"

    doc.close()

    # Check if any text was extracted
    has_text = any(text for text in page_texts)
    if not has_text:
        return page_texts, page_count, "No extractable text found in PDF (may be scanned/image-based)."

    return page_texts, page_count, ""


def save_uploaded_file(file: BinaryIO, stored_filename: str) -> Path:
    """
    Save uploaded file to the upload directory.

    Returns the full path to the saved file.
    """
    filepath = get_upload_dir() / stored_filename
    with open(filepath, "wb") as f:
        content = file.read()
        f.write(content)
    return filepath


def delete_stored_file(stored_filename: str) -> bool:
    """
    Delete a stored file from the upload directory.

    Returns True if file was deleted, False if not found.
    """
    filepath = get_upload_dir() / stored_filename
    try:
        filepath.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def process_pdf_upload(file: BinaryIO, filename: str) -> dict:
    """
    Process a PDF upload: validate, save, extract text.

    Returns a dict with:
        - success: bool
        - stored_filename: str
        - file_size: int
        - page_count: int
        - page_texts: list[str]
        - error: str (if any)
    """
    # Validate
    is_valid, error = validate_pdf_file(file, filename)
    if not is_valid:
        return {
            "success": False,
            "error": error,
        }

    # Generate secure filename
    stored_filename = generate_stored_filename(filename)

    # Save file
    try:
        file.seek(0)
        filepath = save_uploaded_file(file, stored_filename)
        file_size = filepath.stat().st_size
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save file: {e}",
        }

    # Extract text
    page_texts, page_count, extract_error = extract_text_from_pdf(filepath)

    if extract_error and "No extractable text" not in extract_error:
        # Actual error - clean up and return failure
        delete_stored_file(stored_filename)
        return {
            "success": False,
            "error": extract_error,
        }

    return {
        "success": True,
        "stored_filename": stored_filename,
        "file_size": file_size,
        "page_count": page_count,
        "page_texts": page_texts,
        "error": extract_error if "No extractable text" in extract_error else "",
    }