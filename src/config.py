from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    llama_model: str = "llama3.1:8b"
    llama_base_url: str = "http://localhost:11434"
    llama_timeout_seconds: float = 120.0
    app_env: str = "local"


@lru_cache
def get_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    import os

    return Settings(
        llama_model=os.getenv("LLAMA_MODEL", "llama3.2:latest"),
        llama_base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434"),
        llama_timeout_seconds=float(os.getenv("LLAMA_TIMEOUT_SECONDS", "300")),
        app_env=os.getenv("APP_ENV", "local"),
    )
