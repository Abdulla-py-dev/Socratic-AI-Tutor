"""
SQLAlchemy database setup for the Socratic AI Tutor backend.

Provides:
- engine: the SQLAlchemy engine that manages connections to the database.
- SessionLocal: a factory for creating database sessions.
- Base: the declarative base class that all ORM models will inherit from.
- get_db: a FastAPI dependency that yields a database session and ensures
  it is always closed, even if an exception occurs.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings


# Build the SQLAlchemy engine from the configured database URL.
# For SQLite we enable check_same_thread=False so the same engine can be
# used across multiple threads (required by FastAPI's threaded server).
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
    echo=False,  # Set to True to log all SQL statements for debugging.
)

# SessionLocal is a session factory. Each call produces a new Session.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative base. All ORM models (e.g. User, Course) will inherit from this.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session to each request.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...

    The session is always closed after the request, even if an exception is
    raised, thanks to the try/finally block.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Verify that the database is reachable by executing a trivial query.

    Returns True if the connection works, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def create_tables() -> None:
    """
    Create all tables defined on the SQLAlchemy Base metadata.

    Imports models lazily to avoid circular import issues.
    """
    import backend.models  # noqa: F401  # registers models on Base.metadata
    Base.metadata.create_all(bind=engine)