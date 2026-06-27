#!/usr/bin/env bash
# Jalankan bot WhatsApp (FastAPI) di Railway.
set -euo pipefail

cd kita-cuan-wa-bot
PORT="${PORT:-8000}"
exec python -m uvicorn main:app --host 0.0.0.0 --port "${PORT}"
