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
    gemini_api_key_fallback: str | None = Field(
        default=None, description="Optional fallback Google Gemini API key"
    )
    orchestrator_model: str = Field(..., description="Model used for question-pack extraction (OCR)")
    sub_agent_model: str = Field(..., description="Model used for Java code generation and retry loop")
    watch_dir: Path = Field(..., description="Directory to monitor for new screenshots")
    settle_seconds: int = Field(..., ge=1, description="Quiet period (seconds) before a batch is sealed")


# Module-level singleton — import this everywhere.
settings = Settings()
