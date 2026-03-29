"""
Database setup. Supports MySQL (Aiven), PostgreSQL (Neon/Aiven), or SQLite fallback.
Set DATABASE_URL env var with your connection string.
"""
import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool


def _mysql_ssl_context() -> ssl.SSLContext:
    """TLS for cloud MySQL; optional MYSQL_SSL_CA or MYSQL_SSL_VERIFY=false for dev."""
    ca = os.getenv("MYSQL_SSL_CA", "").strip()
    if ca and os.path.isfile(ca):
        return ssl.create_default_context(cafile=ca)
    if os.getenv("MYSQL_SSL_VERIFY", "false").lower() in ("0", "false", "no"):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


def _mysql_url_and_connect_args(url: str) -> tuple[str, dict]:
    """
    PyMySQL rejects SQL-style ?ssl-mode=... in the URL (passed as invalid kwargs).
    Strip it and enable TLS via connect_args when ssl-mode required.
    """
    if "mysql" not in url.lower():
        return url, {}
    parsed = urlparse(url)
    if not parsed.query:
        return url, {}
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    extra: dict = {}
    new_pairs = []
    want_ssl = False
    for k, v in pairs:
        kl = k.lower().replace("_", "-")
        if kl == "ssl-mode":
            if str(v).upper().replace(" ", "") in ("REQUIRED", "VERIFY_CA", "VERIFY_IDENTITY"):
                want_ssl = True
            continue
        new_pairs.append((k, v))
    if want_ssl:
        extra["ssl"] = _mysql_ssl_context()
    new_query = urlencode(new_pairs)
    fixed = urlunparse(parsed._replace(query=new_query))
    return fixed, extra


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
    elif DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

    connect_args: dict = {}
    url = DATABASE_URL

    if "mysql" in url.lower():
        url, mysql_extra = _mysql_url_and_connect_args(url)
        connect_args.update(mysql_extra)
    elif url.startswith("postgresql") and ("aivencloud.com" in url or "neon.tech" in url):
        connect_args["sslmode"] = "require"

    engine = create_engine(
        url,
        connect_args=connect_args or {},
        pool_pre_ping=True,
        pool_recycle=300,
    )
else:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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
