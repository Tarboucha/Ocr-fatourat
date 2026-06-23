from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://ocr:ocr@db:5432/ocr"
    JWT_SECRET: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # one week
    UPLOAD_DIR: str = "/data/uploads"
    # Stored as a comma-separated string. pydantic-settings tries json.loads on
    # list-typed fields before validators run, so we keep it a str and split it
    # ourselves via the `cors_origins` property below.
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # OCR / async jobs
    REDIS_URL: str = "redis://redis:6379/0"
    DEFAULT_OCR_PIPELINE: str = "rapidocr"
    # Seconds before a single OCR task is killed (guards against a hung image).
    OCR_TASK_TIME_LIMIT: int = 180
    OCR_TASK_SOFT_TIME_LIMIT: int = 150

    # Invoice extraction
    DEFAULT_EXTRACTOR: str = "heuristic"
    EXTRACT_VLM_BASE_URL: str = "https://api.openai.com/v1"
    EXTRACT_VLM_MODEL: str = "gpt-4o-mini"
    EXTRACT_VLM_API_KEY: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def sync_database_url(self) -> str:
        """Sync (psycopg2) URL derived from the async URL, for the Celery worker."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
