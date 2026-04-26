"""Settings for the local agent service."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the repo root (3 levels up from this file)
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    local_agent_host: str = "0.0.0.0"
    local_agent_port: int = 8765
    local_agent_secret: str = "change-me-in-env"
    log_level: str = "INFO"

    # Absolute path to the shared logs directory
    @property
    def log_file(self) -> Path:
        log_dir = _REPO_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "agent_actions.json"


settings = Settings()
