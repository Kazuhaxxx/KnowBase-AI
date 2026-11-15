import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Configure deterministic test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["EMBEDDING_BACKEND"] = "mock"
os.environ["ENABLE_RERANKING"] = "false"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-suite-jwt-secret-key-at-least-32-chars"

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.embeddings.provider import get_embedding_service  # noqa: E402
from app.services.seed_service import ensure_roles_and_demo_users  # noqa: E402


@pytest.fixture()
def test_db(tmp_path: Path):
    get_settings.cache_clear()
    get_embedding_service.cache_clear()

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    os.environ["UPLOAD_DIR"] = str(upload_dir)

    db_file = tmp_path / "test_helpdesk.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    ensure_roles_and_demo_users(db)
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def client(test_db):
    app = create_app()

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


def auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
