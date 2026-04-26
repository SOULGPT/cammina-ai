import httpx
from config import settings
import planner
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

async def handle_error(step: dict, action_taken: dict, result: dict, history: list, task_id: str) -> dict:
    """Ask LLM to provide a fix for a failed step."""
    
    # 1. Log error to memory service (Chroma/SQLite)
    # This matches the user's requirement to log errors
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{settings.memory_url}/memory/save", json={
                "task_id": task_id,
                "project_id": "unknown", # Normally would pass project_id
                "content": f"Failed action: {action_taken}. Error: {result.get('stderr', result.get('error'))}",
                "memory_type": "project"
            })
    except Exception as e:
        logger.error(f"Failed to log error to memory: {e}")

    # 2. Get a fix from the LLM
    prompt = f"""You are Cammina AI Orchestrator Error Handler.
We attempted this step: {step['action']}
We took this action: {action_taken}
It failed with this result: {result}

Recent history:
{history[-3:] if len(history) > 3 else history}

Analyze the failure and provide an alternative action to fix it.
Respond ONLY with a JSON object representing the next action, e.g.:
{{"command": "echo 'new approach'", "cwd": "/"}}"""

    messages = [{"role": "user", "content": prompt}]
    response = await planner.complete(messages, task_id)
    
    try:
        import json
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to parse fix JSON: {response}")
        return {}