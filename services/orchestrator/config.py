import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    agent_url: str = "http://localhost:8765"
    llm_url: str = "http://localhost:8001"
    memory_url: str = "http://localhost:8002"
    
    local_agent_secret: str = ""
    
    # 8000 for Orchestrator
    orchestrator_host: str = "0.0.0.0"
    orchestrator_port: int = 8000
    
    log_level: str = "INFO"
    
    user_home: str = os.path.expanduser("~")
    desktop_path: str = os.path.join(os.path.expanduser("~"), "Desktop")

settings = Settings()
