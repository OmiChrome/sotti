"""
config.py — Sotti
Loads and validates all configuration from the .env file.
Import `settings` everywhere; never read os.environ directly.
"""

from pathlib import Path

from pydantic import Field, field_validator
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
    
    # Server network bindings
    server_host: str = Field("0.0.0.0", description="IP address for Uvicorn to bind to")
    server_port: int = Field(8000, description="Port for Uvicorn to bind to")

    @field_validator("watch_dir", mode="before")
    @classmethod
    def normalise_watch_dir(cls, v: object) -> object:
        r"""
        Accepts both quoted and unquoted Windows paths with spaces, e.g.:
            WATCH_DIR=C:\Users\omi\My Screenshots
            WATCH_DIR="C:\Users\omi\My Screenshots"
            WATCH_DIR='C:\Users\omi\My Screenshots'
        Strips surrounding quotes and trailing slashes before Path() conversion.
        """
        if not isinstance(v, str):
            return v
        v = v.strip()
        # Strip matching surrounding quotes (double or single)
        if len(v) >= 2 and v[0] in ('"', "'") and v[-1] == v[0]:
            v = v[1:-1]
        # Strip trailing slashes so Path(...).is_dir() works reliably
        v = v.rstrip("/\\")
        return v


# Module-level singleton — import this everywhere.
settings = Settings()

