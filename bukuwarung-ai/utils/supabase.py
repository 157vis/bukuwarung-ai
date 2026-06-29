"""Supabase client factory — portable."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Buat Supabase client dari env (singleton)."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("SUPABASE_URL dan SUPABASE_KEY wajib diisi di .env")
    return create_client(settings.supabase_url, settings.supabase_key)


def table(client: Client, name: str) -> Any:
    """Shortcut ke tabel Supabase."""
    return client.table(name)
