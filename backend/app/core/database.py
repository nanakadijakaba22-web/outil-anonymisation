"""
Database session management and connection handling.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.json_utils import json_dumps

# Create database engine with custom JSON serializer for RobustJSON
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    echo=False,  # Set to True for SQL query debugging
    json_serializer=json_dumps,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Modern SQLAlchemy 2.0 Base class
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Modern SQLAlchemy 2.0 Base class."""
    pass


def get_db():
    """
    Dependency function to get database session.

    Usage in FastAPI endpoints:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
