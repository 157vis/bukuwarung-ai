"""Cek tabel & data test di Supabase — tanpa print secret."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        if v:
            out[k.strip()] = v
    return out


def _parse_toml_secrets(path: Path) -> dict[str, str]:
    if not path.is_file() or tomllib is None:
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return {k: str(v) for k, v in data.items() if isinstance(v, str) and v}
    except Exception:
        return {}


def _is_valid_key(k: str) -> bool:
    if not k or len(k) < 40:
        return False
    low = k.lower()
    if any(x in low for x in ("your", "service_role_key", "placeholder", "changeme", "xxxx")):
        return False
    return k.count(".") >= 2


def _find_credentials() -> tuple[str, str, str]:
    sources = [
        ("bukuwarung-ai/.env", _parse_env_file(ROOT / ".env")),
        ("kita-cuan-wa-bot/.env", _parse_env_file(REPO / "kita-cuan-wa-bot" / ".env")),
        ("root/.env", _parse_env_file(REPO / ".env")),
        (".streamlit/secrets.toml", _parse_toml_secrets(REPO / ".streamlit" / "secrets.toml")),
    ]
    url, key, src = "", "", "tidak ditemukan"
    for name, vals in sources:
        u = vals.get("SUPABASE_URL", "")
        k = vals.get("SUPABASE_KEY", "")
        if u and _is_valid_key(k):
            return u, k, name
        if u and not url:
            url, src = u, name
        if _is_valid_key(k) and not key:
            key = k
    return url, key, src


url, key, env_src = _find_credentials()

print("ENV_SOURCE:", env_src)
print("SUPABASE_URL:", url or "(kosong)")
print("SUPABASE_KEY:", "SET" if key and len(key) > 20 else "(kosong/placeholder)")

if not url or not _is_valid_key(key):
    print("\nTidak bisa konek - SUPABASE_KEY kosong atau masih placeholder.")
    print("Ambil service_role key di Supabase > Settings > API")
    sys.exit(2)

from supabase import create_client

db = create_client(url, key)

TABLES = [
    "client_settings",
    "clients",
    "brand_voices",
    "otak_memories",
    "wa_users",
    "wa_messages",
    "products",
    "orders",
    "transactions",
    "warehouses",
    "approvals",
]

print("\n=== CEK TABEL (project:", url.split("//")[1].split(".")[0], ") ===")
for name in TABLES:
    try:
        r = db.table(name).select("*").limit(5).execute()
        rows = r.data or []
        suffix = "+" if len(rows) == 5 else ""
        print(f"{name}: ADA ({len(rows)} sample{suffix})")
        for row in rows[:3]:
            if name == "clients":
                print(f"  - {row.get('client_id')} | {row.get('name')} | active={row.get('is_active')}")
            elif name == "brand_voices":
                print(f"  - {row.get('client_id')} | profile={row.get('profile_key')}")
            elif name == "wa_users":
                print(f"  - phone={row.get('phone')} | user_id={row.get('user_id')} | {row.get('label')}")
            elif name == "otak_memories":
                print(f"  - user={row.get('user_id')} | {str(row.get('content', ''))[:50]}")
            elif name == "products":
                print(f"  - {row.get('name')} | user_id={row.get('user_id')} | stock={row.get('stock')}")
            elif name == "wa_users":
                pass
    except Exception as exc:
        err = str(exc)
        if any(x in err for x in ("PGRST205", "does not exist", "404")):
            print(f"{name}: BELUM ADA")
        elif "401" in err or "JWT" in err:
            print(f"{name}: AUTH GAGAL (401) — periksa SUPABASE_KEY (pakai service_role)")
            break
        else:
            print(f"{name}: ERROR — {err[:100]}")
