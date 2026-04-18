"""
config.py — Sotti
Loads and validates all configuration from the .env file.
Import `settings` everywhere; never read os.environ directly.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Resolve .env relative to the project root (two levels up from src/)
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    gemini_api_key: str = Field(..., description="Google Gemini API key")
    orchestrator_model: str = Field(
        default="gemini-2.5-flash-preview-04-17",
        description="Model used for question-pack extraction",
    )
    sub_agent_model: str = Field(
        default="gemma-4-31b-it",
        description="Model reserved for sub-agent tasks (Phase 3)",
    )
    watch_dir: Path = Field(
        default=Path(r"C:\Users\omi\Pictures\Screenshots"),
        description="Directory to monitor for new screenshots",
    )
    settle_seconds: int = Field(
        default=10,
        ge=1,
        description="Quiet period (seconds) before a batch is sealed",
    )


# Module-level singleton — import this everywhere.
settings = Settings()
