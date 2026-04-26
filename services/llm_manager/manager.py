"""LLM Manager – routes inference requests to configured providers."""

from __future__ import annotations

import logging
from enum import Enum

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class CompletionRequest(BaseModel):
    prompt: str
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "llama3.2"
    max_tokens: int = 2048
    temperature: float = 0.7
    stream: bool = False


class CompletionResponse(BaseModel):
    text: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMManager:
    """Unified interface over multiple LLM providers."""

    def __init__(self, ollama_base_url: str = "http://localhost:11434") -> None:
        self.ollama_base_url = ollama_base_url
        self._client = httpx.AsyncClient(timeout=120.0)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        if request.provider == LLMProvider.OLLAMA:
            return await self._ollama_complete(request)
        raise NotImplementedError(f"Provider {request.provider} not yet implemented")

    async def _ollama_complete(self, request: CompletionRequest) -> CompletionResponse:
        url = f"{self.ollama_base_url}/api/generate"
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return CompletionResponse(
            text=data.get("response", ""),
            provider=LLMProvider.OLLAMA,
            model=request.model,
        )

    async def close(self) -> None:
        await self._client.aclose()
