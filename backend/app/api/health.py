from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import check_database_health, get_db
from app.services.generation.providers import OllamaProvider

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)) -> dict:
    """Return service health, DB/pgvector status, and AI mode availability without secrets."""
    settings = get_settings()
    db_status = check_database_health(db)

    ollama_available = False
    ollama_models: list[str] = []
    if settings.ai_execution_mode == "local":
        ollama_available, ollama_models = await OllamaProvider.check_availability(
            settings.ollama_base_url
        )

    return {
        "status": "ok" if db_status["connected"] else "degraded",
        "app": settings.app_name,
        "ai_execution_mode": settings.ai_execution_mode,
        "ollama_available": ollama_available,
        "ollama_models_installed": ollama_models,
        "gemini_configured": bool(settings.gemini_api_key),
        "database": db_status,
    }

