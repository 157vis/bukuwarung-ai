"""Path helpers — portable di flashdisk / HDD / komputer mana pun."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BOT_DIR = PROJECT_ROOT / "kita-cuan-wa-bot"
STATIC_DIR = PROJECT_ROOT / "static"
SQL_DIR = PROJECT_ROOT / "sql"
STREAMLIT_DIR = PROJECT_ROOT / ".streamlit"

_BOOTSTRAPPED = False


def bootstrap_paths() -> Path:
    """Pastikan root project & folder bot ada di sys.path (sekali saja)."""
    global _BOOTSTRAPPED
    root = str(PROJECT_ROOT)
    bot = str(BOT_DIR)
    if root not in sys.path:
        sys.path.insert(0, root)
    if bot not in sys.path:
        sys.path.insert(0, bot)
    _BOOTSTRAPPED = True
    return PROJECT_ROOT


def load_project_dotenv() -> Path | None:
    """Muat .env dari folder bot lalu root. Return path yang berhasil atau None."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None

    for candidate in (BOT_DIR / ".env", PROJECT_ROOT / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return candidate
    return None


def ensure_cwd() -> None:
    """Set working directory ke root project (aman saat dijalankan dari shortcut/script)."""
    os.chdir(PROJECT_ROOT)
