"""
Cammina AI - SQLite Migration Script
=====================================
Run this once to upgrade your existing cammina.db
without losing any data.

Usage:
    python database/migrate_sqlite.py

Or from project root:
    python -m database.migrate_sqlite
"""

import sqlite3
import os
import sys

DB_PATH = os.getenv("DATABASE_URL", "./database/cammina.db")


def get_columns(cursor, table: str) -> set:
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def get_tables(cursor) -> set:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def get_triggers(cursor) -> set:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    return {row[0] for row in cursor.fetchall()}


def get_indexes(cursor) -> set:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    return {row[0] for row in cursor.fetchall()}


def migrate(db_path: str):
    if not os.path.exists(db_path):
        print(f"  [ERROR] Database not found at: {db_path}")
        print("  Run init_db.py first to create a fresh database.")
        sys.exit(1)

    print(f"\n  Cammina AI — SQLite Migration")
    print(f"  Database: {db_path}\n")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    tables   = get_tables(cur)
    triggers = get_triggers(cur)
    indexes  = get_indexes(cur)

    changes = 0

    # --------------------------------------------------
    # STEP 1: Add missing columns to existing tables
    # --------------------------------------------------
    print("  [1/6] Adding missing columns...")

    column_migrations = {
        "projects": [
            ("updated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ],
        "tasks": [
            ("paused_at",  "DATETIME"),
            ("updated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
        ],
        "skills": [
            ("solution", "TEXT"),
        ],
        "provider_status": [
            ("reset_at", "DATETIME"),
        ],
    }

    for table, cols in column_migrations.items():
        if table not in tables:
            print(f"    [SKIP] Table '{table}' does not exist yet — will be created in step 2")
            continue
        existing = get_columns(cur, table)
        for col_name, col_def in cols:
            if col_name not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                print(f"    [+] {table}.{col_name}")
                changes += 1
            else:
                print(f"    [ok] {table}.{col_name} already exists")

    # --------------------------------------------------
    # STEP 2: Create new tables
    # --------------------------------------------------
    print("\n  [2/6] Creating new tables...")

    new_tables = {
        "task_events": """
            CREATE TABLE IF NOT EXISTS task_events (
              id          TEXT PRIMARY KEY,
              task_id     TEXT REFERENCES tasks(id),
              project_id  TEXT REFERENCES projects(id),
              event_type  TEXT NOT NULL,
              step_number INTEGER,
              action      TEXT,
              result      TEXT,
              error       TEXT,
              provider    TEXT,
              metadata    TEXT,
              created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "project_files": """
            CREATE TABLE IF NOT EXISTS project_files (
              id           TEXT PRIMARY KEY,
              project_id   TEXT REFERENCES projects(id),
              task_id      TEXT REFERENCES tasks(id),
              file_path    TEXT NOT NULL,
              action       TEXT NOT NULL,
              content_hash TEXT,
              size_bytes   INTEGER,
              created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
    }

    for table_name, ddl in new_tables.items():
        if table_name not in tables:
            cur.execute(ddl)
            print(f"    [+] Created table: {table_name}")
            changes += 1
        else:
            print(f"    [ok] {table_name} already exists")

    # --------------------------------------------------
    # STEP 3: Add updated_at triggers
    # --------------------------------------------------
    print("\n  [3/6] Adding updated_at triggers...")

    trigger_defs = {
        "trg_projects_updated_at": (
            "projects",
            """CREATE TRIGGER trg_projects_updated_at
               AFTER UPDATE ON projects FOR EACH ROW
               BEGIN
                 UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
               END"""
        ),
        "trg_tasks_updated_at": (
            "tasks",
            """CREATE TRIGGER trg_tasks_updated_at
               AFTER UPDATE ON tasks FOR EACH ROW
               BEGIN
                 UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
               END"""
        ),
        "trg_skills_updated_at": (
            "skills",
            """CREATE TRIGGER trg_skills_updated_at
               AFTER UPDATE ON skills FOR EACH ROW
               BEGIN
                 UPDATE skills SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
               END"""
        ),
    }

    for trig_name, (tbl, ddl) in trigger_defs.items():
        if trig_name not in triggers:
            if tbl in tables:
                cur.execute(ddl)
                print(f"    [+] Trigger: {trig_name}")
                changes += 1
            else:
                print(f"    [SKIP] {trig_name} — table {tbl} missing")
        else:
            print(f"    [ok] {trig_name} already exists")

    # --------------------------------------------------
    # STEP 4: Add missing indexes
    # --------------------------------------------------
    print("\n  [4/6] Adding missing indexes...")

    new_indexes = {
        "idx_task_events_task":    "CREATE INDEX IF NOT EXISTS idx_task_events_task    ON task_events(task_id)",
        "idx_task_events_created": "CREATE INDEX IF NOT EXISTS idx_task_events_created ON task_events(created_at)",
        "idx_skills_category":     "CREATE INDEX IF NOT EXISTS idx_skills_category     ON skills(category)",
        "idx_project_files_prj":   "CREATE INDEX IF NOT EXISTS idx_project_files_prj   ON project_files(project_id)",
        "idx_project_files_task":  "CREATE INDEX IF NOT EXISTS idx_project_files_task  ON project_files(task_id)",
    }

    for idx_name, ddl in new_indexes.items():
        if idx_name not in indexes:
            cur.execute(ddl)
            print(f"    [+] Index: {idx_name}")
            changes += 1
        else:
            print(f"    [ok] {idx_name} already exists")

    # --------------------------------------------------
    # STEP 5: Unique constraint on env_variables
    # SQLite can't ADD CONSTRAINT — recreate table if needed
    # --------------------------------------------------
    print("\n  [5/6] Checking env_variables unique constraint...")

    cur.execute("""
        SELECT sql FROM sqlite_master
        WHERE type='table' AND name='env_variables'
    """)
    row = cur.fetchone()
    if row and "UNIQUE(project_id, key_name)" not in row[0].replace(" ", "").upper():
        print("    [~] Recreating env_variables with unique constraint (no data loss)...")
        cur.executescript("""
            BEGIN;
            CREATE TABLE env_variables_new (
              id              TEXT PRIMARY KEY,
              project_id      TEXT REFERENCES projects(id),
              key_name        TEXT NOT NULL,
              encrypted_value TEXT NOT NULL,
              created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(project_id, key_name)
            );
            INSERT OR IGNORE INTO env_variables_new
              SELECT id, project_id, key_name, encrypted_value, created_at
              FROM env_variables;
            DROP TABLE env_variables;
            ALTER TABLE env_variables_new RENAME TO env_variables;
            COMMIT;
        """)
        print("    [+] env_variables recreated with UNIQUE(project_id, key_name)")
        changes += 1
    else:
        print("    [ok] Unique constraint already present")

    # --------------------------------------------------
    # STEP 6: Seed missing default providers
    # --------------------------------------------------
    print("\n  [6/6] Seeding default providers...")

    providers = [
        ("prov-001", "openrouter"),
        ("prov-002", "nvidia"),
        ("prov-003", "groq"),
        ("prov-004", "together_ai"),
        ("prov-005", "ollama"),
    ]

    for pid, pname in providers:
        cur.execute(
            "INSERT OR IGNORE INTO provider_status (id, provider_name, status, requests_today) VALUES (?, ?, 'active', 0)",
            (pid, pname)
        )
        if cur.rowcount:
            print(f"    [+] Provider: {pname}")
            changes += 1
        else:
            print(f"    [ok] {pname} already seeded")

    # --------------------------------------------------
    # COMMIT
    # --------------------------------------------------
    conn.commit()
    conn.close()

    print(f"\n  Migration complete — {changes} change(s) applied.")
    if changes == 0:
        print("  Database is already up to date.")
    print()


if __name__ == "__main__":
    migrate(DB_PATH)
