#!/usr/bin/env bash
# Jalankan dashboard Streamlit di Railway (Linux container).
set -euo pipefail

mkdir -p .streamlit

cat > .streamlit/secrets.toml <<EOF
SUPABASE_URL = "${SUPABASE_URL}"
SUPABASE_KEY = "${SUPABASE_KEY}"
GROQ_API_KEY = "${GROQ_API_KEY}"
EOF

PORT="${PORT:-8501}"
exec python -m streamlit run app.py \
  --server.port="${PORT}" \
  --server.address=0.0.0.0 \
  --server.headless=true
