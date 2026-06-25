from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env."""

    app_name: str = "AI Operations Agent"
    app_env: str = "local"

    database_url: str = "sqlite:///./data/operations.db"
    knowledge_base_dir: str = "./knowledge_base"
    memory_window: int = Field(default=8, ge=2, le=50)
    max_agent_steps: int = Field(default=6, ge=1, le=12)

    llm_provider: Literal["", "openai", "groq", "ollama", "mock"] = ""

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    request_timeout_seconds: int = Field(default=60, ge=5, le=300)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AI_OPS_",
        extra="ignore",
    )

    @property
    def data_dir(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.replace("sqlite:///", "", 1)
            return Path(db_path).parent
        return Path("./data")


@lru_cache
def get_settings() -> Settings:
    return Settings()
