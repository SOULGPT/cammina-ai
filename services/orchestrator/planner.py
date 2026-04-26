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

SYSTEM_PROMPT = """You are a task planner for Cammina AI.
You break tasks into simple steps.

CRITICAL RULES - FOLLOW EXACTLY:
1. To write a file, ALWAYS use action type "file_write" with file_path and content
2. NEVER use terminal commands to create or edit files
3. NEVER add steps like "open terminal", "open text editor", "save file", "close file"
4. NEVER use "touch", "nano", "vim", "open", "pip install" unless explicitly asked
5. NEVER delete files unless the task says "delete" or "remove"
6. For file creation tasks, use ONLY 2 steps:
   Step 1: Write the file using file_write action
   Step 2: Verify the file exists using file_read action

Output steps as JSON array:
[
  {
    "step": 1,
    "description": "Write the file",
    "action_type": "file_write",
    "file_path": "/full/path/to/file.py",
    "content": "file content here"
  },
  {
    "step": 2,
    "description": "Verify file exists",
    "action_type": "file_read",
    "file_path": "/full/path/to/file.py"
  }
]

Keep it simple. Maximum 5 steps for simple tasks."""

async def create_plan(task_description: str, answers: dict, task_id: str) -> list[dict]:
    """Ask LLM to create a step-by-step execution plan."""
    answers_str = "\\n".join([f"Q: {k}\\nA: {v}" for k, v in answers.items()])
    prompt = f"""{SYSTEM_PROMPT}

Task: "{task_description}"
User Answers:
{answers_str}"""

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
    desc = step.get('description', step.get('action', 'Unknown step'))
    atype = step.get('action_type', step.get('type', 'terminal'))
    
    prompt = f"""You are Cammina AI execution agent.
We are on step: {desc} (Type: {atype})

Recent history:
{history[-3:] if len(history) > 3 else history}

CRITICAL RULES:
1. When creating or updating a file, always use the file write format (2) with the full content. Do not use terminal commands like 'echo', 'sed', or 'vi' to modify files.
2. NEVER use 'rm' or 'delete' commands unless the original task description explicitly requested deletion.
3. Once a file is written successfully, do not attempt to 'close' or 'cleanup' it.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await complete(messages, task_id)
    
    try:
        import json
        return json.loads(response)
    except Exception as e:
        logger.error(f"Failed to parse command JSON: {response}")
        return {}