import httpx
from config import settings
import logging

logger = logging.getLogger(__name__)

def _get_headers() -> dict:
    return {"Authorization": f"Bearer {settings.local_agent_secret}"}

async def run_terminal(command: str, cwd: str = None) -> dict:
    """Execute a terminal command via Local Agent."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {"command": command}
        if cwd:
            payload["cwd"] = cwd
        try:
            resp = await client.post(
                f"{settings.agent_url}/terminal", 
                json=payload, 
                headers=_get_headers()
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"exit_code": -1, "stdout": "", "stderr": str(e), "error": True}

async def file_read(path: str) -> dict:
    """Read a file via Local Agent."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.agent_url}/file/read", 
                json={"path": path}, 
                headers=_get_headers()
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

async def file_write(path: str, content: str) -> dict:
    """Write a file via Local Agent."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.agent_url}/file/write", 
                json={"path": path, "content": content}, 
                headers=_get_headers()
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}