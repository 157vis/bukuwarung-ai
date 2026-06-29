"""Railway entrypoint saat Root Directory = / (repo root).

Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
Delegasi ke bukuwarung-ai/main.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent / "bukuwarung-ai"
_MAIN_FILE = _APP_DIR / "main.py"

if not _MAIN_FILE.is_file():
    raise RuntimeError(
        f"bukuwarung-ai/main.py tidak ditemukan di {_APP_DIR}. "
        "Set Railway Root Directory = bukuwarung-ai ATAU pastikan folder ada di repo."
    )

if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

_spec = importlib.util.spec_from_file_location("bukuwarung_main", _MAIN_FILE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Gagal load {_MAIN_FILE}")

_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

app = _module.app
