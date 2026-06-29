#!/usr/bin/env bash
# Jalankan dashboard Streamlit di Railway (Linux container).
set -euo pipefail

mkdir -p .streamlit

cat > .streamlit/secrets.toml <<EOF
SUPABASE_URL = "${SUPABASE_URL}"
SUPABASE_KEY = "${SUPABASE_KEY}"
GROQ_API_KEY = "${GROQ_API_KEY}"
BUKUWARUNG_BASE_URL = "${BUKUWARUNG_BASE_URL:-https://bukuwarung-ai-larisai.up.railway.app}"
CATAT_BOT_BASE_URL = "${CATAT_BOT_BASE_URL:-https://kita-cuan-wa-bot-larisai.up.railway.app}"
EOF

PORT="${PORT:-8501}"
exec python -m streamlit run app.py \
  --server.port="${PORT}" \
  --server.address=0.0.0.0 \
  --server.headless=true
