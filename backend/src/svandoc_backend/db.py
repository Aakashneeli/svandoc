"""Database configuration and SQLAlchemy bootstrap."""

from __future__ import annotations

import os
from collections.abc import Generator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/svandoc"
DEFAULT_DB_POOL_SIZE = 5
DEFAULT_DB_MAX_OVERFLOW = 10
DEFAULT_DB_POOL_TIMEOUT_SECONDS = 30
DEFAULT_DB_POOL_RECYCLE_SECONDS = 1800


def normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)
    if raw_url.startswith("postgresql://"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url


def should_require_ssl(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname.endswith(".supabase.co")


def ensure_sslmode(url: str) -> str:
    parsed = urlparse(url)
    existing = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "sslmode" not in existing and should_require_ssl(url):
        existing["sslmode"] = "require"
        return urlunparse(parsed._replace(query=urlencode(existing)))
    return url


def get_database_url() -> str:
    configured = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    return ensure_sslmode(normalize_database_url(configured))


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def database_engine_options() -> dict[str, int | bool]:
    return {
        "pool_pre_ping": True,
        "pool_size": _int_env("DB_POOL_SIZE", DEFAULT_DB_POOL_SIZE),
        "max_overflow": _int_env("DB_MAX_OVERFLOW", DEFAULT_DB_MAX_OVERFLOW),
        "pool_timeout": _int_env("DB_POOL_TIMEOUT_SECONDS", DEFAULT_DB_POOL_TIMEOUT_SECONDS),
        "pool_recycle": _int_env("DB_POOL_RECYCLE_SECONDS", DEFAULT_DB_POOL_RECYCLE_SECONDS),
        "pool_use_lifo": True,
    }


class Base(DeclarativeBase):
    pass


engine = create_engine(get_database_url(), **database_engine_options())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
