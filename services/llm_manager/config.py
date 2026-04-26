from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str = ""
    nvidia_api_key: str = ""
    groq_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    llm_manager_host: str = "0.0.0.0"
    llm_manager_port: int = 8001
    log_level: str = "INFO"

    @property
    def db_path(self) -> str:
        db_dir = _REPO_ROOT / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "cammina.db")

settings = Settings()
