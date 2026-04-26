import httpx
from config import settings
import logging

logger = logging.getLogger(__name__)

async def complete(messages: list[dict], task_id: str, max_tokens: int = 1500) -> str:
    """Send a completion request to the LLM Manager."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "messages": messages,
            "task_id": task_id,
            "max_tokens": max_tokens
        }
        resp = await client.post(f"{settings.llm_url}/complete", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["response"]

async def ask_clarifying_questions(task_description: str, task_id: str) -> list[str]:
    """Ask LLM to generate clarifying questions."""
    prompt = f"""You are Cammina AI Orchestrator. 
The user wants to accomplish this task: "{task_description}"

Generate exactly 0 to 5 clarifying questions to ensure you understand exactly what to do. 
If the task is perfectly clear, return an empty list.
Return the questions as a JSON array of strings ONLY. Example: ["Q1", "Q2"]"""

    messages = [{"role": "user", "content": prompt}]
    response = await complete(messages, task_id)
    
    try:
        import json
        questions = json.loads(response)
        if isinstance(questions, list):
            return questions[:5]
    except Exception as e:
        logger.error(f"Failed to parse questions JSON: {response}")
    return []

async def create_plan(task_description: str, answers: dict, task_id: str) -> list[dict]:
    """Ask LLM to create a step-by-step execution plan."""
    answers_str = "\\n".join([f"Q: {k}\\nA: {v}" for k, v in answers.items()])
    prompt = f"""You are Cammina AI Orchestrator.
Task: "{task_description}"
User Answers:
{answers_str}

Create a strict step-by-step plan to achieve this. 
RULES:
1. Generate extremely specific, atomic steps.
2. Each step must be a single, clear action.
3. Every step must include the exact absolute file path if it involves files.
4. Never generate vague steps like "open file in editor" or "setup project".
5. Use "file" type for any file creation or editing.

Respond ONLY with a JSON array of objects. 
Format: [ {{"step": 1, "action": "Write hello world to /path/to/app.py", "type": "file"}} ]"""

    messages = [{"role": "user", "content": prompt}]
    response = await complete(messages, task_id)
    
    try:
        import json
        plan = json.loads(response)
        if isinstance(plan, list):
            return plan
    except Exception as e:
        logger.error(f"Failed to parse plan JSON: {response}")
    
    # Fallback plan
    return [{"step": 1, "action": "Analyze task and begin execution", "type": "terminal"}]

async def decide_next_command(step: dict, history: list, task_id: str) -> dict:
    """Ask LLM to provide the exact command or file content to execute."""
    prompt = f"""You are Cammina AI execution agent.
We are on step: {step['action']} (Type: {step['type']})

Recent history:
{history[-3:] if len(history) > 3 else history}

Respond ONLY with a JSON object for the next action:
1. For terminal commands: {{"command": "ls -la", "cwd": "/"}}
2. For writing or creating files: {{"file_path": "/absolute/path/to/file", "content": "full file content here"}}
3. For reading files: {{"file_path": "/absolute/path/to/file"}}

CRITICAL: When creating or updating a file, always use the file write format (2) with the full content. Do not use terminal commands like 'echo', 'sed', or 'vi' to modify files."""

    messages = [{"role": "user", "content": prompt}]
    response = await complete(messages, task_id)
    
    try:
        import json
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to parse command JSON: {response}")
        return {}