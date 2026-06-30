"""Supabase client factory — admin (service role) + anon (public/RLS)."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from config import get_settings


def _supabase_url() -> str:
    return (os.getenv("SUPABASE_URL") or get_settings().supabase_url or "").strip()


def _service_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or get_settings().supabase_key
        or ""
    ).strip()


def _anon_key() -> str:
    return (os.getenv("SUPABASE_ANON_KEY") or "").strip()


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """Service role — bypass RLS (webhook / backend)."""
    url, key = _supabase_url(), _service_key()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL dan SUPABASE_SERVICE_KEY wajib diisi di .env")
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_anon() -> Client:
    """Anon key — RLS aktif (endpoint publik / dashboard)."""
    url, key = _supabase_url(), _anon_key()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL dan SUPABASE_ANON_KEY wajib diisi di .env")
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Backward-compatible alias → admin client."""
    return get_supabase_admin()


def table(client: Client, name: str) -> Any:
    """Shortcut ke tabel Supabase."""
    return client.table(name)
