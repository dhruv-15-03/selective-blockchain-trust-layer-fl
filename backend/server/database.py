"""
PostgreSQL database setup. Set DATABASE_URL env var (Neon/Aiven connection string).
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Neon/Aiven use postgresql:// - replace with postgresql+psycopg2:// for SQLAlchemy
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(DATABASE_URL)
else:
    # Fallback: in-memory SQLite for dev (no DB setup needed)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
