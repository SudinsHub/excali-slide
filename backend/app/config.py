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

    # LLM placeholders
    LLM_MODEL_PLANNER: str = "gemini-2.0-flash"
    LLM_MODEL_SLIDE: str = "gemini-2.0-flash"
    LLM_MODEL_EDIT: str = "gemini-2.0-flash"
    LLM_MODEL_VISION: str = "gemini-2.0-flash"

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
