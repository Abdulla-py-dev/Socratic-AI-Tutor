"""
FastAPI application entry point for the Socratic AI Tutor backend.

Exposes:
- GET /    : A simple welcome / root endpoint.
- GET /health : Application health check, including database connectivity.

CORS is configured to allow the local Streamlit frontend (default port 8501)
to communicate with this API during development.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import check_database_connection, create_tables
from backend.routes.auth_routes import router as auth_router
from backend.routes.document_routes import router as document_router

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Socratic AI Tutor API",
    description=(
        "Backend API for the Socratic AI Tutor project. "
        "Provides AI-powered personalized learning using Socratic questioning."
    ),
    version="0.1.0",
)

# Create database tables on startup
create_tables()

# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------
# Allow the local Streamlit frontend during development. Streamlit runs on
# http://localhost:8501 by default. Adjust origins as needed for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(document_router)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def read_root():
    """Root endpoint — returns a welcome message."""
    return {
        "message": "Welcome to the Socratic AI Tutor API",
        "version": settings.ollama_model,  # useful sanity check of loaded config
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint.

    Returns the application status and whether the database is reachable.
    """
    db_ok = check_database_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "service": "Socratic AI Tutor API",
    }