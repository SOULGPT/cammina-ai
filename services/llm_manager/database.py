"""SQLite Database interaction for LLM Manager."""
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from config import settings

logger = logging.getLogger(__name__)

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db() -> None:
    """Initialize the SQLite database default values."""
    with get_db() as conn:
        # We assume the schema is already initialized via init_db.py / schema_sqlite.sql.
        # Insert default providers if they don't exist
        providers = [
            ('prov-001', 'openrouter'),
            ('prov-002', 'nvidia'),
            ('prov-003', 'groq'),
            ('prov-004', 'ollama')
        ]
        for pid, pname in providers:
            conn.execute('''
                INSERT OR IGNORE INTO provider_status (id, provider_name, status, requests_today)
                VALUES (?, ?, 'active', 0)
            ''', (pid, pname))
        conn.commit()
        logger.info("Database checked at %s", settings.db_path)

def get_active_providers() -> list[dict]:
    with get_db() as conn:
        now = datetime.now(timezone.utc).isoformat()
        rows = conn.execute('''
            SELECT * FROM provider_status 
            ORDER BY 
                CASE provider_name 
                    WHEN 'openrouter' THEN 1 
                    WHEN 'nvidia' THEN 2 
                    WHEN 'groq' THEN 3 
                    WHEN 'ollama' THEN 4 
                    ELSE 5 
                END
        ''').fetchall()
        
        providers = []
        for r in rows:
            p = dict(r)
            # Check if rate limit has expired
            if p["status"] == "rate_limited" and p["reset_at"] and p["reset_at"] < now:
                conn.execute(
                    "UPDATE provider_status SET status = 'active', reset_at = NULL, last_used = ? WHERE provider_name = ?",
                    (now, p["provider_name"])
                )
                conn.commit()
                p["status"] = "active"
                p["reset_at"] = None
            providers.append(p)
        return providers

def mark_rate_limited(provider_name: str, reset_after_seconds: int = 60) -> None:
    with get_db() as conn:
        reset_at = datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + reset_after_seconds, 
            tz=timezone.utc
        ).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE provider_status SET status = 'rate_limited', reset_at = ?, last_used = ? WHERE provider_name = ?",
            (reset_at, now, provider_name)
        )
        conn.commit()

def increment_request_count(provider_name: str) -> None:
    with get_db() as conn:
        now = datetime.now(timezone.utc).isoformat()
        # In a real app we'd reset this daily based on the timestamp.
        conn.execute(
            "UPDATE provider_status SET requests_today = requests_today + 1, last_used = ? WHERE provider_name = ?",
            (now, provider_name)
        )
        conn.commit()

def save_checkpoint(task_id: str, current_step: int, messages_history: list) -> None:
    with get_db() as conn:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute('''
            INSERT INTO tasks (id, current_step, messages_history, timestamp, title)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                current_step = excluded.current_step,
                messages_history = excluded.messages_history,
                timestamp = excluded.timestamp
        ''', (task_id, current_step, json.dumps(messages_history), now, "LLM Task"))
        conn.commit()

def load_checkpoint(task_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row:
            data = dict(row)
            if data["messages_history"]:
                data["messages_history"] = json.loads(data["messages_history"])
            return data
        return None
