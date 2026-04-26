import json
import logging
from datetime import datetime, timezone
from database import get_db

logger = logging.getLogger(__name__)

def save_checkpoint(task_id: str, current_step: int, messages: list, files_modified: list, commands_run: list, next_action: str) -> str:
    """Save a checkpoint of the task state."""
    state = {
        "current_step": current_step,
        "messages": messages,
        "files_modified": files_modified,
        "commands_run": commands_run,
        "next_action": next_action
    }
    
    checkpoint_data = json.dumps(state)
    now = datetime.now(timezone.utc).isoformat()
    
    with get_db() as conn:
        # Check if task exists, if not we might need to insert or just update if we assume tasks are pre-created.
        # The schema requires project_id and title if inserting. Since we might not have it here, 
        # it's best to UPDATE if task exists, or INSERT minimal data if it's a new task.
        row = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
        
        if row:
            conn.execute(
                "UPDATE tasks SET checkpoint_data = ?, current_step = ?, messages_history = ?, timestamp = ? WHERE id = ?",
                (checkpoint_data, current_step, json.dumps(messages), now, task_id)
            )
        else:
            conn.execute(
                "INSERT INTO tasks (id, title, checkpoint_data, current_step, messages_history, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, "Unknown Task", checkpoint_data, current_step, json.dumps(messages), now)
            )
        conn.commit()
        return f"cp-{now}"

def load_checkpoint(task_id: str) -> dict | None:
    """Load latest checkpoint for a task."""
    with get_db() as conn:
        row = conn.execute("SELECT checkpoint_data FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row and row["checkpoint_data"]:
            try:
                return json.loads(row["checkpoint_data"])
            except json.JSONDecodeError:
                pass
        return None