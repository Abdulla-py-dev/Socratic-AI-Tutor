"""
Document API routes for PDF study material management.

Endpoints:
- POST /documents/upload: Upload and process a PDF document
- GET /documents/: List current student's documents
- GET /documents/{document_id}: Get document details
- DELETE /documents/{document_id}: Delete a document
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.auth import get_current_student
from backend.database import get_db
from backend.models import Document, Student
from backend.schemas import DocumentOut, DocumentDetail, DocumentUploadResponse
from backend.services.pdf_processor import process_pdf_upload, delete_stored_file

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF document for the current student.

    Validates file type, size, and PDF signature.
    Extracts text content and stores metadata.
    """
    # Validate content type
    if file.content_type not in {"application/pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are allowed.",
        )

    # Read file content
    file_content = await file.read()

    # Process upload
    from io import BytesIO
    file_stream = BytesIO(file_content)
    result = process_pdf_upload(file_stream, file.filename or "document.pdf")

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    # Create document record
    document = Document(
        student_id=current_student.id,
        original_filename=file.filename or "document.pdf",
        stored_filename=result["stored_filename"],
        file_size=result["file_size"],
        page_count=result["page_count"],
        processing_status="completed" if not result["error"] else "completed_with_warnings",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """List all documents belonging to the current student."""
    documents = (
        db.query(Document)
        .filter(Document.student_id == current_student.id)
        .order_by(Document.upload_date.desc())
        .all()
    )
    return documents


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Get details of a specific document owned by the current student."""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.student_id == current_student.id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    """Delete a document and its stored file (only if owned by current student)."""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.student_id == current_student.id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete stored file
    delete_stored_file(document.stored_filename)

    # Delete database record
    db.delete(document)
    db.commit()

    return None