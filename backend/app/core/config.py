from functools import lru_cache
from typing import Dict, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DOCUMENT_CATEGORIES: List[str] = [
    # Enterprise & General Knowledge Categories
    "Company Policies",
    "Standard Operating Procedures (SOPs)",
    "HR & Benefits",
    "Product Manuals",
    "Technical Documentation",
    "Training & Onboarding",
    "Legal & Compliance",
    "General Knowledge",
    # IT Support & Operations Categories
    "Network",
    "Hardware",
    "Software",
    "Microsoft 365",
    "Account and Access",
    "VPN",
    "IT Policies",
    "Troubleshooting",
    "General IT Support",
]

ACCESS_CLASSIFICATIONS: List[str] = [
    "public",
    "employee",
    "it_only",
    "restricted",
]

ROLE_CLASSIFICATION_ACCESS: Dict[str, List[str]] = {
    "employee": ["public", "employee"],
    "it_staff": ["public", "employee", "it_only"],
    "admin": ["public", "employee", "it_only", "restricted"],
}


class Settings(BaseSettings):
    """Centralized environment-driven configuration for KnowBase AI."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "KnowBase AI"
    app_env: str = "development"
    debug: bool = False
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Security
    jwt_secret_key: str = "dev-insecure-secret-change-in-production-32chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    rate_limit_default: str = "60/minute"
    rate_limit_chat: str = "20/minute"
    rate_limit_auth: str = "15/minute"

    # Database
    database_url: str = (
        "postgresql+psycopg://helpdesk:helpdesk_dev_password@localhost:5432/helpdesk_ai"
    )

    # Storage & Uploads
    upload_dir: str = "./backend/storage/uploads"
    max_upload_size_mb: int = 15
    allowed_extensions: str = ".pdf,.docx,.txt,.md"

    # AI Execution Modes
    ai_execution_mode: str = Field(default="local", pattern="^(local|cloud)$")

    # Mode A: Local AI (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: int = 90

    # Mode B: Cloud AI (Gemini — Backend Only)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Embeddings & Reranking
    embedding_backend: str = "sentence_transformers"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    enable_reranking: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # RAG Pipeline Parameters
    chunk_size: int = 650
    chunk_overlap: int = 120
    retrieval_top_k_semantic: int = 12
    retrieval_top_k_bm25: int = 12
    retrieval_top_n_final: int = 5
    rrf_k: int = 60
    semantic_weight: float = 0.6
    bm25_weight: float = 0.4
    enable_query_rewriting: bool = True
    evidence_min_score: float = 0.22
    evidence_min_term_coverage: float = 0.15

    # Demo Seeding
    seed_demo_data: bool = True
    demo_admin_email: str = "admin@novatech-demo.internal"
    demo_admin_password: str = "AdminDemo!2026"
    demo_it_email: str = "itstaff@novatech-demo.internal"
    demo_it_password: str = "ItStaffDemo!2026"
    demo_employee_email: str = "employee@novatech-demo.internal"
    demo_employee_password: str = "EmployeeDemo!2026"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extension_set(self) -> set[str]:
        return {ext.strip().lower() for ext in self.allowed_extensions.split(",") if ext.strip()}

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

