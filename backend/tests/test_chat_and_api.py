from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services.generation.prompts import INSUFFICIENT_EVIDENCE_FALLBACK
from app.services.generation.providers import LLMGenerationResult, LLMProvider
from tests.conftest import auth_headers


class FakeGroundedLLM(LLMProvider):
    provider_name = "mock_ollama"
    model_name = "llama3.2:3b-test"

    async def generate(self, system_prompt: str, user_prompt: str) -> LLMGenerationResult:
        return LLMGenerationResult(
            content=(
                "To resolve OneDrive sync error `0x8004de40`, run "
                "`%localappdata%\\Microsoft\\OneDrive\\onedrive.exe /reset` [Source 1]."
            ),
            provider=self.provider_name,
            model=self.model_name,
        )

    async def stream(self, system_prompt: str, user_prompt: str):
        yield "Test token"


def test_chat_grounded_citations_history_isolation_and_feedback(client: TestClient, monkeypatch):
    settings = get_settings()
    admin_headers = auth_headers(client, settings.demo_admin_email, settings.demo_admin_password)
    emp_headers = auth_headers(client, settings.demo_employee_email, settings.demo_employee_password)
    it_headers = auth_headers(client, settings.demo_it_email, settings.demo_it_password)

    # Seed one employee doc and one restricted doc
    client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={
            "files": (
                "m365_sync.md",
                b"# M365 OneDrive Sync\nError 0x8004de40: run onedrive.exe /reset to clear stale tokens.",
                "text/markdown",
            )
        },
        data={"category": "Microsoft 365", "department": "IT", "access_classification": "employee"},
    )
    client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={
            "files": (
                "restricted_vault.md",
                b"# Restricted Break-Glass\nBreak-glass HSM password retrieval requires CISO quorum.",
                "text/markdown",
            )
        },
        data={"category": "Account and Access", "department": "SecOps", "access_classification": "restricted"},
    )

    # Patch LLM provider to avoid needing external Ollama daemon during API test
    monkeypatch.setattr(
        "app.services.generation.chat_service.get_llm_provider",
        lambda: FakeGroundedLLM(),
    )

    # 1. Grounded chat question returns verified citation
    chat_resp = client.post(
        "/api/chat",
        headers=emp_headers,
        json={"question": "How do I fix OneDrive error 0x8004de40?", "retrieval_mode": "hybrid"},
    )
    assert chat_resp.status_code == 200, chat_resp.text
    payload = chat_resp.json()
    conv_id = payload["conversation_id"]
    assistant_msg = payload["assistant_message"]
    assert assistant_msg["evidence_sufficient"] is True
    assert len(assistant_msg["citations"]) == 1
    assert assistant_msg["citations"][0]["original_filename"] == "m365_sync.md"

    # 2. Employee asking about restricted content gets insufficient evidence fallback (no leak!)
    restricted_resp = client.post(
        "/api/chat",
        headers=emp_headers,
        json={"question": "What is the break-glass HSM password retrieval CISO quorum procedure?"},
    )
    assert restricted_resp.status_code == 200
    assert restricted_resp.json()["assistant_message"]["evidence_sufficient"] is False
    assert INSUFFICIENT_EVIDENCE_FALLBACK in restricted_resp.json()["assistant_message"]["content"]
    assert restricted_resp.json()["assistant_message"]["citations"] == []

    # 3. Conversation isolation: IT user cannot view or delete employee's conversation
    assert client.get(f"/api/conversations/{conv_id}", headers=it_headers).status_code == 404
    assert client.delete(f"/api/conversations/{conv_id}", headers=it_headers).status_code == 404

    # 4. Feedback submission works for owner
    fb_resp = client.post(
        "/api/feedback",
        headers=emp_headers,
        json={"message_id": assistant_msg["id"], "rating": "helpful", "comment": "Fixed my sync!"},
    )
    assert fb_resp.status_code == 201
    assert fb_resp.json()["rating"] == "helpful"

    # 5. Analytics reflects real counts without storing prompt text
    analytics = client.get("/api/admin/analytics", headers=admin_headers).json()
    assert analytics["total_questions"] == 2
    assert analytics["helpful_feedback"] == 1
    assert analytics["failed_retrieval_count"] == 1

