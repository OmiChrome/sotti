"""
config.py — Sotti
Loads and validates all configuration from the .env file.
Import `settings` everywhere; never read os.environ directly.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    gemini_api_key: str = Field(..., description="Google Gemini API key")
    gemini_api_key_fallback: str | None = Field(
        default=None, description="Optional fallback Google Gemini API key"
    )

    # Three-model architecture
    ocr_model: str = Field(..., description="Vision model: reads images → writes question.md")
    orchestrator_model: str = Field(..., description="Orchestration model: classifies images, guides code model")
    code_model: str = Field(..., description="Code model: generates + iteratively fixes Java solutions")

    # Backwards compat: if only sub_agent_model is set, use it as code_model
    sub_agent_model: str | None = Field(default=None, description="Deprecated alias for code_model")

    watch_dir: Path = Field(..., description="Directory to monitor for new screenshots")
    settle_seconds: int = Field(..., ge=1, description="Quiet period (seconds) before a batch is sealed")

    # oppe-pyq reference directory
    oppe_pyq_dir: Path = Field(
        default=_PROJECT_ROOT / "oppe-pyq",
        description="Directory containing previous year questions as Java templates",
    )

    # Data output directory
    data_dir: Path = Field(
        default=_PROJECT_ROOT / "data",
        description="Root directory where per-question folders are created",
    )

    # Server network bindings
    server_host: str = Field("0.0.0.0", description="IP address for Uvicorn to bind to")
    server_port: int = Field(8000, description="Port for Uvicorn to bind to")

    def model_post_init(self, __context: object) -> None:
        # Backwards compat: fall back to sub_agent_model if code_model not set
        if not self.code_model and self.sub_agent_model:
            object.__setattr__(self, "code_model", self.sub_agent_model)

    @field_validator("watch_dir", "oppe_pyq_dir", "data_dir", mode="before")
    @classmethod
    def normalise_path(cls, v: object) -> object:
        r"""
        Accepts both quoted and unquoted Windows paths, strips surrounding quotes.
        """
        if not isinstance(v, str):
            return v
        v = v.strip()
        if len(v) >= 2 and v[0] in ('"', "'") and v[-1] == v[0]:
            v = v[1:-1]
        v = v.rstrip("/\\")
        return v


# Module-level singleton — import this everywhere.
settings = Settings()
