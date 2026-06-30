"""Centralized configuration — portable (USB/flashdisk) via pathlib."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.is_file():
    load_dotenv(ENV_FILE, override=False)


class Settings(BaseModel):
    """Environment variables backend BukuWarung-AI (Multi-Tenant)."""

    openrouter_api_key: str = ""
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_anon_key: str = ""
    groq_api_key: str = ""
    railway_url: str = ""
    secret_key: str = ""
    primary_model: str = "minimax/minimax-m3"
    backup_model: str = "deepseek/deepseek-chat-v3"
    free_model: str = "qwen/qwen3-coder:free"
    host: str = "0.0.0.0"
    port: int = 8000
    app_name: str = "BukuWarung-AI"
    debug: bool = False

    @property
    def supabase_key(self) -> str:
        """Alias backward-compatible → service role."""
        return self.supabase_service_key

    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / "data"

    @property
    def is_supabase_live(self) -> bool:
        url = (self.supabase_url or "").strip().lower()
        key = (self.supabase_service_key or "").strip().lower()
        if not url or not key:
            return False
        placeholders = ("your_", "your-", "example", "changeme", "placeholder", "xxxx")
        return not any(p in url or p in key for p in placeholders)

    @property
    def is_configured(self) -> bool:
        """Webhook production: Supabase + OpenRouter + Groq (token WA dari client_settings)."""
        return bool(
            self.openrouter_api_key
            and self.is_supabase_live
            and self.groq_api_key
        )

    def validate_required(self) -> list[str]:
        missing: list[str] = []
        checks = {
            "OPENROUTER_API_KEY": self.openrouter_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_SERVICE_KEY": self.supabase_service_key,
            "GROQ_API_KEY": self.groq_api_key,
        }
        for name, value in checks.items():
            if not (value or "").strip():
                missing.append(name)
        return missing


def _env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings — baca dari environment / .env."""
    service = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or ""
    )
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_service_key=service,
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        railway_url=os.getenv("RAILWAY_URL", "").rstrip("/"),
        secret_key=os.getenv("SECRET_KEY", ""),
        primary_model=os.getenv("PRIMARY_MODEL", "minimax/minimax-m3"),
        backup_model=os.getenv("BACKUP_MODEL", "deepseek/deepseek-chat-v3"),
        free_model=os.getenv("FREE_MODEL", "qwen/qwen3-coder:free"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        app_name=os.getenv("APP_NAME", "BukuWarung-AI"),
        debug=_env_bool("DEBUG"),
    )


def ensure_data_dir() -> Path:
    data = get_settings().data_dir
    data.mkdir(parents=True, exist_ok=True)
    return data
