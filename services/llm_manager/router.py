import logging
from typing import Any

import httpx
import openai
from openai import AsyncOpenAI

from config import settings
import database

logger = logging.getLogger(__name__)

class LLMRouter:
    def __init__(self):
        # Initialize clients lazily or handle empty keys gracefully
        self.clients = {}
        if settings.openrouter_api_key:
            self.clients["openrouter"] = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
            )
        if settings.nvidia_api_key:
            self.clients["nvidia"] = AsyncOpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=settings.nvidia_api_key,
            )
        if settings.groq_api_key:
            self.clients["groq"] = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
            )
        
        self.httpx_client = httpx.AsyncClient(timeout=90.0)
        
        self.models = {
            "openrouter": "meta-llama/llama-3.1-8b-instruct:free",
            "nvidia": "meta/llama-3.1-8b-instruct",
            "groq": "llama-3.1-8b-instant",
            "ollama": "llama3"
        }

        self.vision_models = {
            "nvidia": "nvidia/llama-3.2-90b-vision-instruct",
            "groq": "llama-3.2-90b-vision-preview",
            "openrouter": "meta-llama/llama-3.2-90b-vision-instruct"
        }
        
    def update_keys(self, openrouter: str = None, nvidia: str = None, groq: str = None):
        if openrouter:
            self.clients["openrouter"] = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter,
            )
        if nvidia:
            self.clients["nvidia"] = AsyncOpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=nvidia,
            )
        if groq:
            self.clients["groq"] = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq,
            )

    async def _attempt_completion(self, provider_name: str, messages: list[dict], model: str, max_tokens: int) -> dict[str, Any]:
        try:
            logger.info(f"Attempting completion with {provider_name} using model {model}")
            
            if provider_name in self.clients:
                client = self.clients[provider_name]
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                result_text = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
                
            elif provider_name == "ollama":
                url = f"{settings.ollama_base_url}/api/chat"
                payload = {
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_predict": max_tokens}
                }
                resp = await self.httpx_client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                result_text = data.get("message", {}).get("content", "")
                tokens_used = data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            else:
                raise ValueError(f"Unknown provider: {provider_name}")
            
            database.increment_request_count(provider_name)
            return {
                "response": result_text,
                "provider_used": provider_name,
                "tokens_used": tokens_used
            }
        except Exception as e:
            logger.error(f"Error with {provider_name}: {e}")
            raise e

    async def complete(self, messages: list[dict], task_id: str, max_tokens: int = 1000, max_retries: int = 3) -> dict[str, Any]:
        active_providers = database.get_active_providers()
        available_names = [p["provider_name"] for p in active_providers if p["status"] == "active"]
        
        if not available_names:
            raise RuntimeError("No active providers available.")

        for attempt in range(max_retries):
            for provider_name in available_names:
                try:
                    return await self._attempt_completion(provider_name, messages, self.models.get(provider_name, "llama3"), max_tokens)
                except (openai.RateLimitError, httpx.HTTPStatusError):
                    database.mark_rate_limited(provider_name, reset_after_seconds=60)
                    continue
                except Exception:
                    continue
        raise RuntimeError(f"All providers exhausted.")

    async def complete_with_vision(self, messages: list[dict], task_id: str, max_tokens: int = 1000, max_retries: int = 3) -> dict[str, Any]:
        """Specialized completion for multimodal/vision requests."""
        active_providers = database.get_active_providers()
        # Prioritize providers that have vision models defined
        available_names = [p["provider_name"] for p in active_providers if p["status"] == "active" and p["provider_name"] in self.vision_models]
        
        if not available_names:
            logger.warning("No vision-capable providers active. Falling back to standard complete (might fail).")
            return await self.complete(messages, task_id, max_tokens, max_retries)

        for attempt in range(max_retries):
            for provider_name in available_names:
                try:
                    return await self._attempt_completion(provider_name, messages, self.vision_models[provider_name], max_tokens)
                except (openai.RateLimitError, httpx.HTTPStatusError):
                    database.mark_rate_limited(provider_name, reset_after_seconds=60)
                    continue
                except Exception:
                    continue
        raise RuntimeError(f"All vision providers exhausted.")

    async def close(self):
        await self.httpx_client.aclose()
