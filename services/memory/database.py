import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

_REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = _REPO_ROOT / "database" / "cammina.db"
CHROMA_PATH = _REPO_ROOT / "database" / "chroma_data"
PROJECTS_DIR = _REPO_ROOT / "logs" / "projects"

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
