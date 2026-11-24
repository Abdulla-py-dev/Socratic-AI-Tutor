"""
Authentication API routes: register, login, and current user info.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import (
    authenticate_student,
    create_access_token,
    get_current_student,
    get_password_hash,
)
from backend.database import get_db
from backend.models import Student
from backend.schemas import StudentLogin, StudentOut, StudentRegister, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def register(student_in: StudentRegister, db: Session = Depends(get_db)):
    """Register a new student."""
    # Check for duplicate email
    if db.query(Student).filter(Student.email == student_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    student = Student(
        full_name=student_in.full_name,
        email=student_in.email,
        hashed_password=get_password_hash(student_in.password),
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.post("/login", response_model=Token)
def login(student_in: StudentLogin, db: Session = Depends(get_db)):
    """Authenticate student and return JWT access token."""
    student = authenticate_student(db, student_in.email, student_in.password)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": student.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=StudentOut)
def read_me(current_student: Student = Depends(get_current_student)):
    """Get the currently authenticated student's profile."""
    return current_student