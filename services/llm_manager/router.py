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
        
        self.httpx_client = httpx.AsyncClient(timeout=30.0)
        
        self.providers = ["openrouter", "nvidia", "groq", "ollama"]
        self.models = {
            "openrouter": "meta-llama/llama-3.1-8b-instruct:free",
            "nvidia": "meta/llama-3.1-8b-instruct",
            "groq": "llama-3.1-8b-instant",
            "ollama": "llama3"
        }
        self.current_provider_index = 0
        
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

    async def complete(self, messages: list[dict], task_id: str, max_tokens: int = 1000, max_retries: int = 3) -> dict[str, Any]:
        """
        Attempts to call LLM providers in priority order.
        If a 429 or timeout occurs, saves a checkpoint and moves to the next provider.
        """
        # Load checkpoint if resuming (optional logic, but implemented as requested)
        checkpoint = database.load_checkpoint(task_id)
        current_step = checkpoint["current_step"] if checkpoint else 0
        
        active_providers = database.get_active_providers()
        
        # Filter strictly active
        available_names = [p["provider_name"] for p in active_providers if p["status"] == "active"]
        
        if not available_names:
            raise RuntimeError("No active providers available (all rate limited or offline).")

        for attempt in range(max_retries):
            for provider_name in available_names:
                try:
                    logger.info(f"Attempting completion with {provider_name}")
                    
                    if provider_name in self.clients:
                        # OpenAI compatible (OpenRouter, Nvidia, Groq)
                        client = self.clients[provider_name]
                        response = await client.chat.completions.create(
                            model=self.models[provider_name],
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=0.7,
                        )
                        result_text = response.choices[0].message.content
                        tokens_used = response.usage.total_tokens if response.usage else 0
                        
                    elif provider_name == "ollama":
                        # Raw httpx for Ollama
                        url = f"{settings.ollama_base_url}/api/chat"
                        payload = {
                            "model": self.models["ollama"],
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
                        continue # Unknown provider
                    
                    # Success!
                    database.increment_request_count(provider_name)
                    
                    return {
                        "response": result_text,
                        "provider_used": provider_name,
                        "tokens_used": tokens_used
                    }
                    
                except openai.RateLimitError:
                    logger.warning(f"Rate limit hit for {provider_name}")
                    database.mark_rate_limited(provider_name, reset_after_seconds=60)
                    database.save_checkpoint(task_id, current_step, messages)
                    continue # Try next provider
                except openai.APITimeoutError:
                    logger.warning(f"Timeout for {provider_name}")
                    database.save_checkpoint(task_id, current_step, messages)
                    continue # Try next provider
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        logger.warning(f"Rate limit hit for {provider_name}")
                        database.mark_rate_limited(provider_name, reset_after_seconds=60)
                        database.save_checkpoint(task_id, current_step, messages)
                        continue
                    logger.error(f"HTTP error for {provider_name}: {e}")
                    database.save_checkpoint(task_id, current_step, messages)
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error with {provider_name}: {e}")
                    database.save_checkpoint(task_id, current_step, messages)
                    continue
                    
        raise RuntimeError(f"All providers exhausted or failed after {max_retries} retries.")

    async def close(self):
        await self.httpx_client.aclose()
