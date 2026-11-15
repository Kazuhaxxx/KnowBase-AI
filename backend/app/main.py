from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import admin, auth, chat, collections, documents, feedback, health, knowledge
from app.api.deps import limiter
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging_config import configure_logging
import app.models  # noqa: F401
from app.services.seed_service import (
    ensure_default_collections,
    ensure_roles_and_demo_users,
    seed_sample_documents,
)

settings = get_settings()
logger = configure_logging(debug=settings.debug)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize schema tables and optional demo data on startup."""
    try:
        current_settings = get_settings()
        Base.metadata.create_all(bind=engine)
        if current_settings.seed_demo_data:
            db = SessionLocal()
            try:
                ensure_default_collections(db)
                users = ensure_roles_and_demo_users(db)
                admin_user = users.get("admin")
                seed_sample_documents(db, admin_user_id=admin_user.id if admin_user else None)
            finally:
                db.close()
    except Exception as exc:
        logger.warning("Startup DB initialization skipped or deferred: %s", exc)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="KnowBase AI — Enterprise Knowledge Assistant API",
        description=(
            "Your Knowledge. One Intelligent Assistant. "
            "Retrieval-Augmented Generation API with hybrid semantic + BM25 search, "
            "cross-encoder reranking, strict RBAC document isolation, knowledge collections, "
            "source citations, and automated evaluation."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_: Request, __: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please wait briefly before retrying."},
        )

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(collections.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(knowledge.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(feedback.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)

    return app


app = create_app()

