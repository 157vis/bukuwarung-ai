"""Bridge ke laris_core (repo root) — transaksi & AI extractor dengan service role."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from config import get_settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from laris_core import LarisCore  # noqa: E402

from utils.supabase import get_supabase_admin  # noqa: E402


@lru_cache(maxsize=1)
def get_tenant_core() -> LarisCore:
    """LarisCore service role untuk webhook backend (bypass RLS, scoped via user_id)."""
    settings = get_settings()
    url = (settings.supabase_url or os.getenv("SUPABASE_URL", "")).strip()
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or settings.supabase_key
        or ""
    ).strip()
    groq = (settings.groq_api_key or os.getenv("GROQ_API_KEY", "")).strip()
    if not url or not key or not groq:
        raise RuntimeError("SUPABASE_URL, SUPABASE_SERVICE_KEY, GROQ_API_KEY wajib untuk tenant core")
    return LarisCore.from_service_client(
        url,
        key,
        groq,
        supabase_client=get_supabase_admin(),
    )
