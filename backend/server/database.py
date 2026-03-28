"""
Database setup. Supports MySQL (Aiven), PostgreSQL (Neon/Aiven), or SQLite fallback.
Set DATABASE_URL env var with your connection string.
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
    # MySQL (Aiven) - already has mysql+pymysql:// prefix from .env
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
    # PostgreSQL (Neon/Aiven)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

    # SSL config for cloud providers
    connect_args = {}
    if "aivencloud.com" in DATABASE_URL or "neon.tech" in DATABASE_URL:
        connect_args["ssl"] = {"ssl_disabled": False}

    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
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
