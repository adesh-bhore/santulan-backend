"""Database Connection and Session Management

Provides SQLAlchemy engine, session factory, and dependency injection for FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings


# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before using
    pool_size=10,         # Connection pool size
    max_overflow=20       # Max connections beyond pool_size
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields a database session and ensures it's closed after use.
    
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
