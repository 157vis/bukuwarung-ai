"""Reproduce webhook 500 error locally."""
import asyncio
import json
import sys
from fastapi.testclient import TestClient

# Set env sebelum import
import os
os.environ["GROQ_API_KEY"] = "gsk_test_dummy"
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_KEY"] = "test_dummy"
os.environ["WA_API_KEY"] = "test_dummy"
os.environ["WA_PROVIDER"] = "fonnte"

sys.path.insert(0, ".")

try:
    from main import app
    print("[OK] main imported")
except Exception as e:
    print(f"[FAIL] import main: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test webhook GET
client = TestClient(app)
print("\n=== GET /webhook ===")
r = client.get("/webhook")
print(f"HTTP {r.status_code}: {r.json()}")

# Test webhook POST (Fonnte-like payload)
print("\n=== POST /webhook (halo) ===")
payload = {
    "device": "6282112826851",
    "message": "halo",
    "sender": "6281234567890",
    "name": "Test",
    "inboxid": "diag-1"
}
try:
    r = client.post("/webhook", json=payload)
    print(f"HTTP {r.status_code}: {r.text[:500]}")
except Exception as e:
    print(f"[FAIL] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
