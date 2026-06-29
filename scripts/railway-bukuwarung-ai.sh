#!/usr/bin/env bash
# Jalankan BukuWarung-AI (FastAPI multi-agent) di Railway.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

pip install -q -r requirements.txt
pip install -q -r bukuwarung-ai/requirements.txt

PORT="${PORT:-8000}"
exec python -m uvicorn main:app --host 0.0.0.0 --port "${PORT}"
