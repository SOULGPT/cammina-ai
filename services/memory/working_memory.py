import json
import uuid
from datetime import datetime, timezone
from database import get_db

def save_working_memory(task_id: str, project_id: str, content: str) -> None:
    """Save context to working memory (memory_snapshots table)."""
    snapshot_id = f"wm-{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat()
    
    with get_db() as conn:
        # Check if working memory for this task already exists to overwrite or create new?
        # The spec says "Key format: 'task:{task_id}:context'. Stores: current step, conversation history, last action."
        # We can just update or insert. Since it's snapshots, maybe just insert or overwrite by task_id and snapshot_type.
        
        row = conn.execute(
            "SELECT id FROM memory_snapshots WHERE task_id = ? AND snapshot_type = 'working_memory'", 
            (task_id,)
        ).fetchone()
        
        if row:
            conn.execute(
                "UPDATE memory_snapshots SET content = ?, created_at = ? WHERE id = ?",
                (content, now, row["id"])
            )
        else:
            conn.execute(
                "INSERT INTO memory_snapshots (id, project_id, task_id, snapshot_type, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (snapshot_id, project_id, task_id, "working_memory", content, now)
            )
        conn.commit()

def load_working_memory(task_id: str) -> dict | None:
    """Load working memory context."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT content FROM memory_snapshots WHERE task_id = ? AND snapshot_type = 'working_memory'", 
            (task_id,)
        ).fetchone()
        if row and row["content"]:
            try:
                return json.loads(row["content"])
            except json.JSONDecodeError:
                return {"raw_content": row["content"]}
        return None

def clear_working_memory(task_id: str) -> None:
    """Clear working memory when task completes."""
    with get_db() as conn:
        conn.execute(
            "DELETE FROM memory_snapshots WHERE task_id = ? AND snapshot_type = 'working_memory'",
            (task_id,)
        )
        conn.commit()