"""FastAPI dependency — validates the Authorization bearer token."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from config import settings
from logger import log_action


async def require_auth(authorization: str | None = Header(default=None)) -> None:
    """Raise 401 if the Authorization header is missing or token is wrong."""
    if authorization is None:
        log_action(
            settings.log_file,
            endpoint="auth",
            action="missing_header",
            result="unauthorized",
            duration_ms=0,
            error="Authorization header missing",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    # Accept both "Bearer <token>" and bare "<token>"
    token = authorization.removeprefix("Bearer ").strip()

    if token != settings.local_agent_secret:
        log_action(
            settings.log_file,
            endpoint="auth",
            action="invalid_token",
            result="unauthorized",
            duration_ms=0,
            error="Invalid token",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization token",
        )
