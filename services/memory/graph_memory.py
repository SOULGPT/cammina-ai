import uuid
from datetime import datetime, timezone
from database import get_db

def search_skills(query: str, category: str = None) -> list[dict]:
    """Search skills database."""
    # Basic keyword search using SQLite. 
    # For advanced search, we could use FTS5 or ChromaDB, but spec says "SQLite".
    # We will do a basic LIKE search for demonstration.
    with get_db() as conn:
        q = f"%{query}%"
        if category:
            rows = conn.execute(
                "SELECT * FROM skills WHERE category = ? AND (name LIKE ? OR description LIKE ?)",
                (category, q, q)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM skills WHERE name LIKE ? OR description LIKE ?",
                (q, q)
            ).fetchall()
            
        return [dict(r) for r in rows]

def save_skill(name: str, category: str, description: str, learned_from_project: str) -> bool:
    """Save a new skill or update existing."""
    now = datetime.now(timezone.utc).isoformat()
    skill_id = f"skill-{uuid.uuid4()}"
    
    with get_db() as conn:
        try:
            conn.execute('''
                INSERT INTO skills (id, name, category, description, learned_from_project, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (skill_id, name, category, description, learned_from_project, now, now))
            conn.commit()
            return True
        except Exception:
            # Maybe uniqueness constraint on name
            return False

def update_skill_usage(name: str, success: bool) -> None:
    """Update success rate and usage count after using a skill."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute("SELECT usage_count, success_rate FROM skills WHERE name = ?", (name,)).fetchone()
        if row:
            usage = row["usage_count"]
            old_rate = row["success_rate"]
            
            # Recalculate success rate
            successful_uses = old_rate * usage
            if success:
                successful_uses += 1
            
            new_usage = usage + 1
            new_rate = successful_uses / new_usage
            
            conn.execute(
                "UPDATE skills SET usage_count = ?, success_rate = ?, updated_at = ? WHERE name = ?",
                (new_usage, new_rate, now, name)
            )
            conn.commit()