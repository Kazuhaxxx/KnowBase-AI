from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import logging
from typing import AsyncGenerator

import httpx

from app.core.config import get_settings

logger = logging.getLogger("helpdesk_ai.llm")


class LLMUnavailableError(RuntimeError):
    """Raised when the configured LLM provider is unreachable or misconfigured."""


@dataclass
class LLMGenerationResult:
    content: str
    provider: str
    model: str


class LLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> LLMGenerationResult: ...

    @abstractmethod
    async def stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]: ...


class OllamaProvider(LLMProvider):
    """Mode A: Local AI execution via Ollama REST API."""

    provider_name = "ollama"

    def __init__(self, base_url: str, model_name: str, timeout_seconds: int = 90) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    @staticmethod
    async def check_availability(base_url: str) -> tuple[bool, list[str]]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{base_url.rstrip('/')}/api/tags")
                if resp.status_code != 200:
                    return False, []
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                return True, models
        except Exception:
            return False, []

    async def generate(self, system_prompt: str, user_prompt: str) -> LLMGenerationResult:
        payload = {
            "model": self.model_name,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 1024},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(
                f"Ollama is not reachable at {self.base_url}. "
                f"Start Ollama locally and run 'ollama pull {self.model_name}', "
                "or configure AI_EXECUTION_MODE=cloud with a backend GEMINI_API_KEY."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"Ollama request failed: {exc}") from exc

        # Automatic memory fallback: if VRAM or buffer fails, retry with lower context
        if resp.status_code >= 400 and any(
            err in resp.text.lower() for err in ("out of memory", "cudamalloc", "cpu_repack", "failed to allocate")
        ):
            logger.warning("Ollama memory pressure encountered. Retrying inference with reduced context (num_ctx=512)...")
            payload["options"]["num_ctx"] = 512
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            except Exception as exc:
                raise LLMUnavailableError(f"Ollama low-memory retry failed: {exc}") from exc

        if resp.status_code == 404:
            raise LLMUnavailableError(
                f"Ollama model '{self.model_name}' is not installed. "
                f"Run 'ollama pull {self.model_name}' (or 'ollama pull qwen2.5:0.5b' for low-spec PCs) and retry."
            )
        if resp.status_code >= 400:
            raise LLMUnavailableError(f"Ollama returned HTTP {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        text = data.get("message", {}).get("content", "").strip()
        if not text:
            raise LLMUnavailableError("Ollama returned an empty response.")
        return LLMGenerationResult(content=text, provider=self.provider_name, model=self.model_name)

    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model_name,
            "stream": True,
            "options": {"temperature": 0.1, "num_ctx": 1024},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        body_text = body.decode(errors="ignore")
                        if "out of memory" in body_text.lower() or "cudamalloc" in body_text.lower():
                            logger.warning("Ollama GPU VRAM full. Retrying stream with CPU offload (num_gpu=0)...")
                            payload["options"]["num_gpu"] = 0
                            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as cpu_resp:
                                if cpu_resp.status_code >= 400:
                                    cpu_body = await cpu_resp.aread()
                                    raise LLMUnavailableError(f"Ollama CPU stream failed: {cpu_body.decode(errors='ignore')[:200]}")
                                async for line in cpu_resp.aiter_lines():
                                    if not line:
                                        continue
                                    chunk = json.loads(line)
                                    token = chunk.get("message", {}).get("content", "")
                                    if token:
                                        yield token
                            return

                        raise LLMUnavailableError(
                            f"Ollama streaming failed ({resp.status_code}): {body_text[:200]}"
                        )
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(
                f"Ollama is not reachable at {self.base_url}. "
                f"Start Ollama and pull '{self.model_name}'."
            ) from exc


class GeminiProvider(LLMProvider):
    """Mode B: Optional Cloud AI execution via Google Gemini REST API (backend-only)."""

    provider_name = "gemini"

    def __init__(self, api_key: str, model_name: str, timeout_seconds: int = 60) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    async def generate(self, system_prompt: str, user_prompt: str) -> LLMGenerationResult:
        if not self.api_key:
            raise LLMUnavailableError(
                "Cloud AI mode is selected, but GEMINI_API_KEY is not configured on the backend."
            )
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.1},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(
                    url,
                    headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"Gemini API request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise LLMUnavailableError(f"Gemini API error ({resp.status_code}). Check backend configuration.")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise LLMUnavailableError("Gemini API returned no candidates.")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise LLMUnavailableError("Gemini API returned empty content.")
        return LLMGenerationResult(content=text, provider=self.provider_name, model=self.model_name)

    async def stream(self, system_prompt: str, user_prompt: str) -> AsyncGenerator[str, None]:
        # Fallback chunked yield over generate() for reliable SSE formatting
        res = await self.generate(system_prompt, user_prompt)
        for token in res.content.split(" "):
            yield token + " "


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.ai_execution_mode == "cloud":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model,
        )
    return OllamaProvider(
        base_url=settings.ollama_base_url,
        model_name=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )

