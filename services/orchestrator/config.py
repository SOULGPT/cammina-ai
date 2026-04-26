from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    orchestrator_host: str = "0.0.0.0"
    orchestrator_port: int = 8000
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    llm_manager_url: str = "http://localhost:8001"
    memory_url: str = "http://localhost:8002"
    local_agent_url: str = "http://localhost:8003"
