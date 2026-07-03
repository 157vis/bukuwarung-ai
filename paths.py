"""Path helpers — portable di flashdisk / HDD / komputer mana pun.

Catatan: Bot WhatsApp (kita-cuan-wa-bot) sudah dipisah ke repo
tersendiri (https://github.com/157vis/kita-cuan-wa-bot) — deploy
independent di Railway. Folder ini hanya untuk monorepo Streamlit
dashboard + BukuWarung-AI webhook CS.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
STATIC_DIR = PROJECT_ROOT / "static"
SQL_DIR = PROJECT_ROOT / "sql"
STREAMLIT_DIR = PROJECT_ROOT / ".streamlit"

_BOOTSTRAPPED = False


def bootstrap_paths() -> Path:
    """Pastikan root project ada di sys.path (sekali saja)."""
    global _BOOTSTRAPPED
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    _BOOTSTRAPPED = True
    return PROJECT_ROOT


def load_project_dotenv() -> Path | None:
    """Muat .env dari root repo. Return path yang berhasil atau None."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None

    candidate = PROJECT_ROOT / ".env"
    if candidate.is_file():
        load_dotenv(candidate, override=False)
        return candidate
    return None


def ensure_cwd() -> None:
    """Set working directory ke root project (aman saat dijalankan dari shortcut/script)."""
    os.chdir(PROJECT_ROOT)
