"""Local Agent – executes tools and file-system operations on behalf of agents."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalAgent:
    """Runs local tools such as shell commands and file I/O."""

    def __init__(self, workspace: str | Path = ".") -> None:
        self.workspace = Path(workspace).resolve()

    # ── File tools ────────────────────────────────────────────────────────────

    def read_file(self, relative_path: str) -> str:
        target = self._safe_path(relative_path)
        return target.read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> None:
        target = self._safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("Wrote %d chars to %s", len(content), target)

    def list_dir(self, relative_path: str = ".") -> list[str]:
        target = self._safe_path(relative_path)
        return [str(p.relative_to(self.workspace)) for p in target.iterdir()]

    # ── Shell tool ────────────────────────────────────────────────────────────

    async def run_command(
        self, command: str, timeout: float = 30.0
    ) -> tuple[int, str, str]:
        """Run a shell command inside the workspace. Returns (returncode, stdout, stderr)."""
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(self.workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", "Command timed out"
        return proc.returncode or 0, stdout.decode(), stderr.decode()

    # ── Safety ────────────────────────────────────────────────────────────────

    def _safe_path(self, relative_path: str) -> Path:
        target = (self.workspace / relative_path).resolve()
        if not str(target).startswith(str(self.workspace)):
            raise PermissionError(f"Path escape detected: {relative_path}")
        return target
