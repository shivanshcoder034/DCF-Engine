"""Database engine, session management, and initialization module.

Configures the SQLite connection using centralized settings and provides
safe transactional session context management.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from src.data.models import Base

logger = logging.getLogger(__name__)

# Ensure the database directory exists
settings.ensure_directories()

# Configure SQLite engine with thread safety for Streamlit concurrency
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def init_db() -> None:
    """Initialize database tables idempotently without dropping existing data."""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("Database tables verified and initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize database: %s", exc)
        raise RuntimeError(f"Database initialization error: {exc}") from exc


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager providing a transactional SQLAlchemy session with automatic rollback on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
