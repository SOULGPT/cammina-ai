"""
Cammina-AI  ·  Local Agent
FastAPI service that gives the AI "hands" on the local Mac.

Endpoints
─────────
GET  /health
POST /terminal
POST /file/read
POST /file/write
POST /file/list
POST /file/delete
POST /browser/screenshot
POST /app/open
POST /clipboard/copy
POST /clipboard/paste

Every request (except /health) requires:
  Authorization: Bearer <LOCAL_AGENT_SECRET>
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import pyautogui
import pyperclip
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, Field

from auth import require_auth
from config import settings
from logger import log_action
import browser

# ── Logging setup ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Cammina-AI Local Agent",
    description="Executes real commands on the local Mac on behalf of Cammina AI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shorthand type alias for authenticated routes ──────────────────────────────

Auth = Annotated[None, Depends(require_auth)]

# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/health", tags=["meta"])
async def health() -> dict:
    """No auth required — used by orchestrator and Docker health checks."""
    return {
        "status": "healthy",
        "service": "cammina-local-agent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  TERMINAL
# ══════════════════════════════════════════════════════════════════════════════


class TerminalRequest(BaseModel):
    command: str = Field(..., description="Shell command to execute")
    cwd: str | None = Field(None, description="Working directory (optional)")


class TerminalResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float


@app.post("/terminal", response_model=TerminalResponse, tags=["execution"])
async def run_terminal(_: Auth, body: TerminalRequest) -> TerminalResponse:
    """Execute a shell command and return its output."""
    t0 = time.perf_counter()
    error_msg: str | None = None
    result_status = "success"

    try:
        proc = await asyncio.create_subprocess_shell(
            body.command,
            cwd=body.cwd or None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=60.0
            )
        except asyncio.TimeoutError:
            proc.kill()
            duration_ms = (time.perf_counter() - t0) * 1000
            log_action(
                settings.log_file,
                endpoint="/terminal",
                action=body.command,
                result="timeout",
                duration_ms=duration_ms,
                error="Command timed out after 60 s",
            )
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Command timed out after 60 seconds",
            )

        exit_code = proc.returncode if proc.returncode is not None else -1
        stdout = stdout_bytes.decode(errors="replace")
        stderr = stderr_bytes.decode(errors="replace")

    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        error_msg = str(exc)
        result_status = "error"
        log_action(
            settings.log_file,
            endpoint="/terminal",
            action=body.command,
            result=result_status,
            duration_ms=duration_ms,
            error=error_msg,
        )
        raise HTTPException(status_code=500, detail=error_msg)

    duration_ms = (time.perf_counter() - t0) * 1000
    if exit_code != 0:
        result_status = "non_zero_exit"

    log_action(
        settings.log_file,
        endpoint="/terminal",
        action=body.command,
        result=result_status,
        duration_ms=duration_ms,
        error=stderr or None,
        extra={"exit_code": exit_code, "cwd": body.cwd},
    )

    return TerminalResponse(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        duration_ms=round(duration_ms, 2),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  FILE — READ
# ══════════════════════════════════════════════════════════════════════════════


class FileReadRequest(BaseModel):
    path: str


class FileReadResponse(BaseModel):
    content: str
    size_bytes: int
    path: str


@app.post("/file/read", response_model=FileReadResponse, tags=["file"])
async def file_read(_: Auth, body: FileReadRequest) -> FileReadResponse:
    t0 = time.perf_counter()
    try:
        p = Path(body.path).expanduser().resolve()
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {body.path}")
        if not p.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {body.path}")
        content = p.read_text(encoding="utf-8", errors="replace")
        size = p.stat().st_size
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        log_action(settings.log_file, endpoint="/file/read", action=body.path,
                   result="error", duration_ms=duration_ms, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    duration_ms = (time.perf_counter() - t0) * 1000
    log_action(settings.log_file, endpoint="/file/read", action=body.path,
               result="success", duration_ms=duration_ms,
               extra={"size_bytes": size})
    return FileReadResponse(content=content, size_bytes=size, path=str(p))


# ══════════════════════════════════════════════════════════════════════════════
#  FILE — WRITE
# ══════════════════════════════════════════════════════════════════════════════


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileWriteResponse(BaseModel):
    success: bool
    path: str


@app.post("/file/write", response_model=FileWriteResponse, tags=["file"])
async def file_write(_: Auth, body: FileWriteRequest) -> FileWriteResponse:
    t0 = time.perf_counter()
    try:
        p = Path(body.path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body.content, encoding="utf-8")
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        log_action(settings.log_file, endpoint="/file/write", action=body.path,
                   result="error", duration_ms=duration_ms, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    duration_ms = (time.perf_counter() - t0) * 1000
    log_action(settings.log_file, endpoint="/file/write", action=body.path,
               result="success", duration_ms=duration_ms,
               extra={"bytes_written": len(body.content.encode())})
    return FileWriteResponse(success=True, path=str(p))


# ══════════════════════════════════════════════════════════════════════════════
#  FILE — LIST
# ══════════════════════════════════════════════════════════════════════════════


class FileListRequest(BaseModel):
    path: str


class FileListResponse(BaseModel):
    files: list[str]
    folders: list[str]
    path: str


@app.post("/file/list", response_model=FileListResponse, tags=["file"])
async def file_list(_: Auth, body: FileListRequest) -> FileListResponse:
    t0 = time.perf_counter()
    try:
        p = Path(body.path).expanduser().resolve()
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {body.path}")
        if not p.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {body.path}")

        files: list[str] = []
        folders: list[str] = []
        for child in sorted(p.iterdir()):
            if child.is_dir():
                folders.append(child.name)
            else:
                files.append(child.name)
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        log_action(settings.log_file, endpoint="/file/list", action=body.path,
                   result="error", duration_ms=duration_ms, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    duration_ms = (time.perf_counter() - t0) * 1000
    log_action(settings.log_file, endpoint="/file/list", action=body.path,
               result="success", duration_ms=duration_ms,
               extra={"files": len(files), "folders": len(folders)})
    return FileListResponse(files=files, folders=folders, path=str(p))


# ══════════════════════════════════════════════════════════════════════════════
#  FILE — DELETE
# ══════════════════════════════════════════════════════════════════════════════


class FileDeleteRequest(BaseModel):
    path: str


class FileDeleteResponse(BaseModel):
    success: bool


@app.post("/file/delete", response_model=FileDeleteResponse, tags=["file"])
async def file_delete(_: Auth, body: FileDeleteRequest) -> FileDeleteResponse:
    t0 = time.perf_counter()
    try:
        p = Path(body.path).expanduser().resolve()
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {body.path}")
        if p.is_dir():
            import shutil
            shutil.rmtree(p)
        else:
            p.unlink()
    except HTTPException:
        raise
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        log_action(settings.log_file, endpoint="/file/delete", action=body.path,
                   result="error", duration_ms=duration_ms, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    duration_ms = (time.perf_counter() - t0) * 1000
    log_action(settings.log_file, endpoint="/file/delete", action=body.path,
               result="success", duration_ms=duration_ms)
    return FileDeleteResponse(success=True)


# ══════════════════════════════════════════════════════════════════════════════
#  BROWSER — SCREENSHOT
# ══════════════════════════════════════════════════════════════════════════════




# ══════════════════════════════════════════════════════════════════════════════
#  APP — OPEN
# ══════════════════════════════════════════════════════════════════════════════


class AppOpenRequest(BaseModel):
    app_name: str = Field(..., description="Name of the macOS application to open")


class AppOpenResponse(BaseModel):
    success: bool
    app: str


@app.post("/app/open", response_model=AppOpenResponse, tags=["mac"])
async def app_open(_: Auth, body: AppOpenRequest) -> AppOpenResponse:
    """Open a macOS application by name using the `open` command."""
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            ["open", "-a", body.app_name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Failed to open {body.app_name}")
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        log_action(settings.log_file, endpoint="/app/open", action=body.app_name,
                   result="error", duration_ms=duration_ms, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    duration_ms = (time.perf_counter() - t0) * 1000
    log_action(settings.log_file, endpoint="/app/open", action=body.app_name,
               result="success", duration_ms=duration_ms)
    return AppOpenResponse(success=True, app=body.app_name)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIPBOARD — COPY
# ══════════════════════════════════════════════════════════════════════════════


class ClipboardCopyRequest(BaseModel):
    text: str


class ClipboardCopyResponse(BaseModel):
    success: bool


@app.post("/clipboard/copy", response_model=ClipboardCopyResponse, tags=["mac"])
async def clipboard_copy(_: Auth, body: ClipboardCopyRequest) -> ClipboardCopyResponse:
    """Copy text to the macOS clipboard."""
    t0 = time.perf_counter()
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, pyperclip.copy, body.text)
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        log_action(settings.log_file, endpoint="/clipboard/copy",
                   action=f"copy ({len(body.text)} chars)",
                   result="error", duration_ms=duration_ms, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    duration_ms = (time.perf_counter() - t0) * 1000
    log_action(settings.log_file, endpoint="/clipboard/copy",
               action=f"copy ({len(body.text)} chars)",
               result="success", duration_ms=duration_ms)
    return ClipboardCopyResponse(success=True)


# ══════════════════════════════════════════════════════════════════════════════
#  CLIPBOARD — PASTE
# ══════════════════════════════════════════════════════════════════════════════


class ClipboardPasteResponse(BaseModel):
    content: str


@app.post("/clipboard/paste", response_model=ClipboardPasteResponse, tags=["mac"])
async def clipboard_paste(_: Auth) -> ClipboardPasteResponse:
    """Return the current macOS clipboard content."""
    t0 = time.perf_counter()
    try:
        loop = asyncio.get_event_loop()
        content: str = await loop.run_in_executor(None, pyperclip.paste)
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        log_action(settings.log_file, endpoint="/clipboard/paste", action="paste",
                   result="error", duration_ms=duration_ms, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    duration_ms = (time.perf_counter() - t0) * 1000
    log_action(settings.log_file, endpoint="/clipboard/paste", action="paste",
               result="success", duration_ms=duration_ms,
               extra={"content_length": len(content)})
    return ClipboardPasteResponse(content=content)


# ══════════════════════════════════════════════════════════════════════════════
#  CURSOR / SCREEN CONTROL
# ══════════════════════════════════════════════════════════════════════════════

class CursorTypeRequest(BaseModel):
    text: str

@app.post("/cursor/screenshot", tags=["mac"])
async def cursor_screenshot(_: Auth):
    result = browser.take_screenshot()
    return result

@app.post("/cursor/type", tags=["mac"])
async def cursor_type(_: Auth, body: CursorTypeRequest):
    result = browser.focus_and_type_in_cursor(body.text)
    return result

@app.post("/cursor/type_antigravity", tags=["mac"])
async def cursor_type_antigravity(_: Auth, body: CursorTypeRequest):
    result = browser.focus_and_type_in_antigravity(body.text)
    return result

@app.post("/cursor/focus", tags=["mac"])
async def cursor_focus(_: Auth, body: dict):
    result = browser.focus_app(body.get("app", "Cursor"))
    return result

@app.post("/cursor/read_terminal", tags=["mac"])
async def cursor_read_terminal(_: Auth):
    result = browser.take_screenshot()
    return result

@app.get("/app/active", tags=["mac"])
async def app_active(_: Auth):
    result = browser.get_active_window()
    return result

@app.post("/cursor/read_chat", tags=["mac"])
async def cursor_read_chat(_: Auth):
    result = browser.read_cursor_chat()
    return result

@app.post("/browser/screenshot", tags=["mac"])
async def take_screenshot(_: Auth):
    result = browser.take_screenshot()
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.local_agent_host, port=settings.local_agent_port, reload=True)
