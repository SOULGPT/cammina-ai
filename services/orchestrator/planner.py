import httpx
import re
import logging
from config import settings

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

PLANNER_SYSTEM_PROMPT = """
You are a task planner for Cammina AI running on macOS.
You break tasks into atomic steps.

AVAILABLE ACTION TYPES (use ONLY these):
1. file_write   - Write content to a file
2. file_read    - Read a file
3. file_list    - List files in a directory  
4. terminal     - Run a shell command
5. done         - Mark task complete

OUTPUT FORMAT - return a JSON array ONLY, no explanation:
[
  {
    "step": 1,
    "description": "Brief description",
    "action_type": "file_write",
    "file_path": "/absolute/path/to/file.py",
    "content": "file content here"
  },
  {
    "step": 2,
    "description": "Verify file exists",
    "action_type": "file_read",
    "file_path": "/absolute/path/to/file.py"
  }
]

STRICT RULES:
1. NEVER use action_type other than the 5 listed above
2. For file_write: always include file_path and content
3. For terminal: always include command and cwd
4. For file_read/file_list: always include file_path
5. NEVER add steps like "open terminal", "open editor", "save file", "close file"
6. NEVER use terminal to create files - use file_write instead
7. NEVER run: apt-get, brew install, nano, vim, open, touch, cat > file
8. NEVER delete files unless task explicitly says "delete" or "remove"
9. Keep steps minimal - file creation = 1 step (file_write), not 5 steps
10. Always use absolute paths starting with /Users/miruzaankhan

EXAMPLES:

Task: "create a python file that prints hello"
CORRECT:
[{"step":1,"description":"Create python file","action_type":"file_write","file_path":"/Users/miruzaankhan/Desktop/hello.py","content":"print('hello')"}]

Task: "create a react app called myapp"
CORRECT:
[
  {"step":1,"description":"Create project with npx","action_type":"terminal","command":"npx create-react-app myapp","cwd":"/Users/miruzaankhan/Desktop"},
  {"step":2,"description":"List created files","action_type":"file_list","file_path":"/Users/miruzaankhan/Desktop/myapp"}
]

Task: "push my repo to github"
CORRECT:
[
  {"step":1,"description":"Add all files","action_type":"terminal","command":"git add .","cwd":"/Users/miruzaankhan/Desktop/cammina"},
  {"step":2,"description":"Commit changes","action_type":"terminal","command":"git commit -m 'update'","cwd":"/Users/miruzaankhan/Desktop/cammina"},
  {"step":3,"description":"Push to origin","action_type":"terminal","command":"git push origin main","cwd":"/Users/miruzaankhan/Desktop/cammina"}
]
"""

async def create_plan(task_description: str, answers: dict, task_id: str) -> list[dict]:
    """Ask LLM to create a step-by-step execution plan."""
    answers_str = "\\n".join([f"Q: {k}\\nA: {v}" for k, v in answers.items()])
    prompt = f"""{PLANNER_SYSTEM_PROMPT}

Task: "{task_description}"
User Answers:
{answers_str}"""

    messages = [{"role": "user", "content": prompt}]
    response = await complete(messages, task_id)
    
    # Strip markdown backticks if present
    clean_response = response.strip()
    if clean_response.startswith("```"):
        clean_response = re.sub(r'^```[a-zA-Z]*\\n|\\n```$', '', clean_response, flags=re.DOTALL)
    
    try:
        import json
        plan = json.loads(clean_response)
        if isinstance(plan, list):
            return plan
    except Exception as e:
        logger.error(f"Failed to parse plan JSON: {response}")
    
    # Fallback plan
    return [{"step": 1, "description": "Manual task analysis", "action_type": "terminal", "command": "ls -la", "cwd": "/Users/miruzaankhan"}]

async def get_alternative_approach(step: dict, error: str, history: list, task_id: str) -> dict:
    """Ask LLM for a completely different approach to the failed step."""
    prompt = f"""The previous step failed.
Step: {step.get('description')}
Action attempted: {step.get('action_type')}
Error received: {error}

Recent history:
{history[-3:] if len(history) > 3 else history}

Do NOT retry the same command. 
Suggest a completely different approach using ONLY: file_write, file_read, file_list, terminal, done.
Return a SINGLE JSON object representing the new action.
"""
    messages = [{"role": "user", "content": prompt}]
    response = await complete(messages, task_id)
    
    clean_response = response.strip()
    if clean_response.startswith("```"):
        clean_response = re.sub(r'^```[a-zA-Z]*\\n|\\n```$', '', clean_response, flags=re.DOTALL)
        
    try:
        import json
        return json.loads(clean_response)
    except Exception as e:
        logger.error(f"Failed to parse alternative approach JSON: {response}")
        return {}