"""
PostgreSQL / MySQL database setup. Set DATABASE_URL env var (Neon / Aiven, etc.).
"""
import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool


def _mysql_ssl_context() -> ssl.SSLContext:
    """
    Aiven / cloud MySQL often needs TLS. Default verify can fail on macOS (cert chain).
    Set MYSQL_SSL_CA=/path/to/ca.pem for strict verify, or MYSQL_SSL_VERIFY=false for dev.
    """
    ca = os.getenv("MYSQL_SSL_CA", "").strip()
    if ca and os.path.isfile(ca):
        ctx = ssl.create_default_context(cafile=ca)
        return ctx
    if os.getenv("MYSQL_SSL_VERIFY", "false").lower() in ("0", "false", "no"):
        # Dev / quick connect — encrypts but does not verify server cert (not for production)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


def _mysql_url_and_ssl(url: str) -> tuple[str, dict]:
    """
    PyMySQL does not accept MySQL shell-style ?ssl-mode=REQUIRED in the URL query string
    (it becomes an invalid keyword argument). Strip it and use connect_args instead.
    """
    if "mysql" not in url.lower():
        return url, {}
    parsed = urlparse(url)
    if not parsed.query:
        return url, {}
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    connect_args: dict = {}
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
        connect_args["ssl"] = _mysql_ssl_context()
    new_query = urlencode(new_pairs)
    fixed = urlunparse(parsed._replace(query=new_query))
    return fixed, connect_args


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Neon/Aiven Postgres: use psycopg2 driver
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
        engine = create_engine(DATABASE_URL)
    elif "mysql" in DATABASE_URL.lower():
        url_fixed, ca = _mysql_url_and_ssl(DATABASE_URL)
        engine = create_engine(url_fixed, connect_args=ca)
    else:
        engine = create_engine(DATABASE_URL)
else:
    # Fallback: in-memory SQLite for dev (no DB setup needed)
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
    _ensure_users_role_column()


def _ensure_users_role_column():
    """Add users.role if DB was created before this column existed."""
    try:
        with engine.begin() as conn:
            d = conn.dialect.name
            if d == "mysql":
                r = conn.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'"
                    )
                )
                if (r.scalar() or 0) == 0:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) NULL"))
            elif d == "postgresql":
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32)"))
            elif d == "sqlite":
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32)"))
                except Exception:
                    pass
    except Exception as e:
        print(f"Auth DB migration (role column): {e}")
