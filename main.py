"""ASGI entry point untuk Railway.

Railway/Nixpacks sering menjalankan `uvicorn main:app` dari root repo.
Bot FastAPI aslinya ada di `kita-cuan-wa-bot/main.py` — file ini meneruskan `app`.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BOT_MAIN = _ROOT / "kita-cuan-wa-bot" / "main.py"

_spec = spec_from_file_location("laris_wa_bot_main", _BOT_MAIN)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Tidak menemukan bot di {_BOT_MAIN}")

_mod = module_from_spec(_spec)
_spec.loader.exec_module(_mod)

app = _mod.app
