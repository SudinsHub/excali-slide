from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "dev"
    PORT: int = 8000
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/slides"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/slides_test"
    STORAGE_DIR: str = "./storage"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    MAX_UPLOAD_MB: int = 25

    # LLM Settings (any LiteLLM model string)
    LLM_MODEL_PLANNER: str = "anthropic/claude-3-5-sonnet-20241022"
    LLM_MODEL_SLIDE: str = "anthropic/claude-3-5-sonnet-20241022"
    LLM_MODEL_EDIT: str = "anthropic/claude-3-5-sonnet-20241022"
    LLM_MODEL_VISION: str = "anthropic/claude-3-5-sonnet-20241022"
    LLM_TIMEOUT_S: int = 120
    FAKE_LLM: int = 0

    # Job & Ingest Settings
    JOB_CONCURRENCY: int = 4
    MAX_RESOURCE_CHARS: int = 60000

    # Optional Provider API Keys
    ANTHROPIC_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p.resolve()


settings = Settings()
