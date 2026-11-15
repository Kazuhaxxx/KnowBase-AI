import json
from typing import Any, Generator, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings


class EmbeddingVector(TypeDecorator):
    """Portable vector column: pgvector Vector(dim) on PostgreSQL, JSON on SQLite for unit tests."""

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 384, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Optional[list[float]], dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return [float(x) for x in value]
        return [float(x) for x in value]

    def process_result_value(self, value: Any, dialect: Any) -> Optional[list[float]]:
        if value is None:
            return None
        if isinstance(value, str):
            return [float(x) for x in json.loads(value)]
        return [float(x) for x in value]


class Base(DeclarativeBase):
    """Declarative SQLAlchemy base class."""


def _build_engine(database_url: str):
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    elif database_url.startswith("postgresql"):
        connect_args = {"connect_timeout": 3}
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


settings = get_settings()
engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_health(db: Session) -> dict[str, Any]:
    """Check DB connectivity and pgvector extension status without exposing credentials."""
    try:
        db.execute(text("SELECT 1"))
        dialect = db.bind.dialect.name if db.bind else "unknown"
        pgvector_enabled = False
        if dialect == "postgresql":
            res = db.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar()
            pgvector_enabled = bool(res)
        return {
            "connected": True,
            "dialect": dialect,
            "pgvector_enabled": pgvector_enabled,
        }
    except Exception:
        return {
            "connected": False,
            "dialect": "unknown",
            "pgvector_enabled": False,
        }
