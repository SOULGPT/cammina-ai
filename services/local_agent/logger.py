"""Append-only JSON-lines logger for agent actions."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_lock = threading.Lock()


def log_action(
    log_file: Path,
    *,
    endpoint: str,
    action: str,
    result: str,
    duration_ms: float,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append one structured entry to the JSONL log file (thread-safe)."""
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "endpoint": endpoint,
        "action": action,
        "result": result,
        "duration_ms": round(duration_ms, 2),
        "error": error,
    }
    if extra:
        entry.update(extra)

    line = json.dumps(entry, ensure_ascii=False)
    with _lock:
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
