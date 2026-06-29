"""Centralized configuration — portable (USB/flashdisk) via pathlib."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Root project = folder yang berisi config.py
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.is_file():
    load_dotenv(ENV_FILE, override=False)


class Settings(BaseModel):
    """Semua environment variables untuk BukuWarung-AI."""

    openrouter_api_key: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    fonnte_token: str = ""
    groq_api_key: str = ""
    primary_model: str = "minimax/minimax-m3"
    backup_model: str = "deepseek/deepseek-chat-v3"
    free_model: str = "qwen/qwen3-coder:free"
    host: str = "0.0.0.0"
    port: int = 8000
    app_name: str = "BukuWarung-AI"
    debug: bool = False
    owner_phones: list[str] = []

    @property
    def owner_phone_set(self) -> frozenset[str]:
        return frozenset("".join(c for c in p if c.isdigit()) for p in self.owner_phones if p)

    @property
    def data_dir(self) -> Path:
        """Folder knowledge base lokal (JSON)."""
        return PROJECT_ROOT / "data"

    @property
    def is_supabase_live(self) -> bool:
        """True jika Supabase URL/key bukan placeholder."""
        url = (self.supabase_url or "").strip().lower()
        key = (self.supabase_key or "").strip().lower()
        if not url or not key:
            return False
        placeholders = ("your_", "your-", "example", "changeme", "placeholder")
        return not any(p in url or p in key for p in placeholders)

    @property
    def is_configured(self) -> bool:
        """True jika key minimal untuk webhook production sudah diisi."""
        return bool(
            self.openrouter_api_key and self.is_supabase_live and self.fonnte_token
        )

    def validate_required(self) -> list[str]:
        """Return daftar env var yang masih kosong."""
        missing: list[str] = []
        checks = {
            "OPENROUTER_API_KEY": self.openrouter_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_KEY": self.supabase_key,
            "FONNTE_TOKEN": self.fonnte_token,
            "GROQ_API_KEY": self.groq_api_key,
        }
        for name, value in checks.items():
            if not (value or "").strip():
                missing.append(name)
        return missing


def _env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes")


def _parse_owner_phones(raw: str) -> list[str]:
    return [p.strip() for p in raw.split(",") if p.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings — baca dari environment / .env."""
    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_key=os.getenv("SUPABASE_KEY", ""),
        fonnte_token=os.getenv("FONNTE_TOKEN", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        primary_model=os.getenv("PRIMARY_MODEL", "minimax/minimax-m3"),
        backup_model=os.getenv("BACKUP_MODEL", "deepseek/deepseek-chat-v3"),
        free_model=os.getenv("FREE_MODEL", "qwen/qwen3-coder:free"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        app_name=os.getenv("APP_NAME", "BukuWarung-AI"),
        debug=_env_bool("DEBUG"),
        owner_phones=_parse_owner_phones(os.getenv("OWNER_PHONES", "")),
    )


def ensure_data_dir() -> Path:
    """Buat folder data/ jika belum ada."""
    data = get_settings().data_dir
    data.mkdir(parents=True, exist_ok=True)
    return data
