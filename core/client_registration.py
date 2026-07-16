"""
Modul Pendaftaran Client Baru — laris.AI Multi-Tenant.

Dipakai oleh Super Admin di menu 'Pengaturan Bot' untuk daftarkan toko baru.
Semua insert terpusat di modul ini supaya konsisten & validated.

TABEL YANG TERPENGARUH saat pendaftaran baru:
- `clients`           → row baru (PK: client_id)
- `auth.users`        → owner harus sudah punya akun (UUID)
- `wa_users`          → opsional (legacy owner→UUID mapping)
- `warehouses`        → opsional (default warehouse untuk toko baru)
- `client_settings`   → opsional (default settings per tenant)

Metadata fields di `clients.metadata` JSONB:
- user_id            → UUID dari auth.users (WAJIB untuk routing)
- wa_cs              → nomor CS toko (format 62xxx)
- wa_catat           → nomor Owner (format 62xxx)
- webhook_cs         → URL CS Agent (auto-generated)
- webhook_catat      → URL Catat Agent (auto-generated)
- webhook_path       → path webhook WA bot (auto-generated)
- whatsapp_display   → format tampilan 08xxx (untuk UI)
- pattern            → 'multitenant_v1' (versioning)
- migrated_at        → timestamp ISO
"""

from __future__ import annotations

import re
import secrets
import string
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# Validation helpers
# ============================================================
def normalize_phone_to_e164(raw: str) -> str:
    """Normalisasi nomor HP ke format 62xxx (E.164 Indonesia)."""
    if not raw:
        return ""
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return ""
    # 08xx → 628xx
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    # +62xx → 62xx (sudah di-handle re.sub)
    if not digits.startswith("62"):
        digits = "62" + digits
    return digits


def normalize_phone_to_display(e164: str) -> str:
    """Format 628xxx → 08xxx untuk tampilan UI."""
    if not e164:
        return ""
    if e164.startswith("62"):
        return "0" + e164[2:]
    return e164


def slugify_client_id(label: str) -> str:
    """Buat client_id aman dari nama toko."""
    if not label:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return slug[:40] or "toko_baru"


def validate_email(email: str) -> bool:
    """Validasi format email sederhana."""
    if not email:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def validate_fonnte_token(token: str) -> bool:
    """Validasi token Fonnte (minimal panjang + alphanumeric)."""
    if not token:
        return False
    cleaned = token.strip()
    if len(cleaned) < 10:
        return False
    # Token Fonnte biasanya panjang, alphanumeric + dash
    return bool(re.match(r"^[A-Za-z0-9_-]+$", cleaned))


# ============================================================
# Schema introspection — tabel mana yang ada
# ============================================================
def detect_required_tables(core) -> dict[str, bool]:
    """Cek tabel mana yang ada di Supabase (untuk kasih tau admin)."""
    tables_to_check = [
        "clients",          # WAJIB — multi-tenant registry
        "auth.users",       # WAJIB — owner login
        "wa_users",         # opsional — legacy phone→UUID mapping
        "warehouses",       # opsional — auto-create warehouse
        "client_settings",  # opsional — default settings
        "products",         # opsional — auto-init product list
    ]
    result = {}
    for t in tables_to_check:
        try:
            result[t] = core.table_exists(t)
        except Exception:
            result[t] = False
    return result


# ============================================================
# User UUID lookup
# ============================================================
def get_user_uuid_by_email(core, email: str) -> str | None:
    """Ambil UUID user dari auth.users by email. Requires service_role key.

    Returns UUID string atau None kalau user tidak ditemukan.
    """
    if not email:
        return None
    try:
        # Pakai Supabase Admin API via SQL Editor / RPC
        # Karena service_role key biasanya dipakai oleh admin tools
        resp = (
            core.supabase.table("users")
            .select("id, email")
            .eq("email", email.strip().lower())
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            return rows[0].get("id")
    except Exception as exc:
        logger.debug("get_user_uuid_by_email fallback error: %s", exc)
    return None


# ============================================================
# Main registration function
# ============================================================
def register_new_client(
    core,
    *,
    client_id: str,
    name: str,
    wa_cs: str,
    wa_catat: str,
    fonnte_token: str,
    owner_email: str,
    owner_phones: list[str] | None = None,
    is_active: bool = True,
    create_default_warehouse: bool = True,
    auto_setup_webhook_urls: bool = True,
    bukuwarung_base_url: str = "https://bukuwarung-ai-larisai.up.railway.app",
) -> dict[str, Any]:
    """Daftarkan client baru ke tabel `clients` (multi-tenant registry).

    Args:
        core: LarisCore instance (sudah punya supabase client)
        client_id: slug unik (huruf kecil + underscore)
        name: nama toko untuk tampilan
        wa_cs: nomor WhatsApp CS (format 62xxx)
        wa_catat: nomor WhatsApp Owner (format 62xxx)
        fonnte_token: token Fonnte untuk device CS
        owner_email: email owner (untuk lookup UUID)
        owner_phones: list nomor owner (untuk backward compat)
        is_active: apakah toko langsung aktif
        create_default_warehouse: apakah auto-create warehouse "Gudang Utama"
        auto_setup_webhook_urls: apakah generate webhook URLs otomatis
        bukuwarung_base_url: base URL bukuwarung-ai untuk webhook

    Returns:
        dict dengan keys:
            - success: bool
            - message: str
            - client_id: str (kalau sukses)
            - user_id: str (UUID owner, kalau ketemu)
            - tables_affected: list[str]
            - webhook_urls: dict[str, str]
    """
    result = {
        "success": False,
        "message": "",
        "client_id": client_id,
        "user_id": None,
        "tables_affected": [],
        "webhook_urls": {},
    }

    # === Validasi input ===
    if not client_id or not re.match(r"^[a-z0-9_]+$", client_id):
        result["message"] = "client_id harus huruf kecil + angka + underscore saja"
        return result

    if not name:
        result["message"] = "Nama toko wajib diisi"
        return result

    wa_cs_e164 = normalize_phone_to_e164(wa_cs)
    wa_catat_e164 = normalize_phone_to_e164(wa_catat)

    if not wa_cs_e164 or len(wa_cs_e164) < 9:
        result["message"] = f"Nomor CS tidak valid: {wa_cs}"
        return result

    if not wa_catat_e164 or len(wa_catat_e164) < 9:
        result["message"] = f"Nomor Owner tidak valid: {wa_catat}"
        return result

    if not validate_fonnte_token(fonnte_token):
        result["message"] = "Token Fonnte tidak valid (min 10 karakter alphanumeric)"
        return result

    if not validate_email(owner_email):
        result["message"] = f"Email owner tidak valid: {owner_email}"
        return result

    # === Cek tabel yang ada ===
    tables = detect_required_tables(core)
    if not tables.get("clients"):
        result["message"] = (
            "Tabel 'clients' belum ada di Supabase. "
            "Jalankan setup_laris_ai.sql atau add_free_tier_minimal.sql dulu."
        )
        return result

    # === Cek apakah client_id sudah ada ===
    try:
        existing = (
            core.supabase.table("clients")
            .select("client_id")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            result["message"] = f"client_id '{client_id}' sudah ada. Gunakan slug lain."
            return result
    except Exception as exc:
        result["message"] = f"Gagal cek existing client: {exc}"
        return result

    # === Cari UUID owner ===
    owner_uuid = get_user_uuid_by_email(core, owner_email)
    if not owner_uuid:
        # Coba insert dengan UUID kosong dulu, nanti di-update manual
        owner_uuid = ""
        logger.warning(
            "Owner UUID untuk %s tidak ditemukan via auth.users. "
            "Owner harus sudah pernah login di Streamlit dulu.",
            owner_email,
        )

    # === Auto-setup webhook URLs ===
    webhook_urls = {}
    if auto_setup_webhook_urls and owner_uuid:
        webhook_urls = {
            "webhook_cs": f"{bukuwarung_base_url}/webhook/csat/{owner_uuid}",
            "webhook_catat": f"{bukuwarung_base_url}/webhook/catat/{owner_uuid}",
            "webhook_path": f"/webhook-whatsapp/{client_id}",
        }

    # === Build metadata ===
    metadata = {
        "user_id": owner_uuid,
        "wa_cs": wa_cs_e164,
        "wa_catat": wa_catat_e164,
        "whatsapp_display": normalize_phone_to_display(wa_cs_e164),
        "whatsapp_cs_display": normalize_phone_to_display(wa_cs_e164),
        "whatsapp_catat_display": normalize_phone_to_display(wa_catat_e164),
        "pattern": "multitenant_v1",
        "migrated_at": datetime.now(timezone.utc).isoformat(),
    }
    if webhook_urls:
        metadata.update(webhook_urls)

    # === Tentukan owner_phones ===
    if not owner_phones:
        owner_phones = [wa_catat_e164]
    else:
        owner_phones = [normalize_phone_to_e164(p) for p in owner_phones if p]

    # === Insert ke tabel clients ===
    payload = {
        "client_id": client_id,
        "name": name,
        "fonnte_token": fonnte_token.strip(),
        "owner_phones": owner_phones,
        "profile_key": client_id,
        "products": {"items": []},
        "payment_methods": {"cash": True, "transfer": True},
        "is_active": is_active,
        "metadata": metadata,
    }

    try:
        core.supabase.table("clients").insert(payload).execute()
        result["tables_affected"].append("clients")
    except Exception as exc:
        result["message"] = f"Gagal insert ke tabel clients: {str(exc)[:200]}"
        logger.exception("register_new_client insert failed: %s", exc)
        return result

    # === Optional: Auto-create default warehouse ===
    if create_default_warehouse and tables.get("warehouses") and owner_uuid:
        try:
            core.supabase.table("warehouses").insert({
                "user_id": owner_uuid,
                "name": "Gudang Utama",
                "location": "",
                "notes": f"Auto-created saat pendaftaran {client_id}",
            }).execute()
            result["tables_affected"].append("warehouses")
        except Exception as exc:
            logger.warning("Auto-create warehouse gagal: %s", exc)

    # === Sukses ===
    result["success"] = True
    result["user_id"] = owner_uuid
    result["message"] = (
        f"✅ Toko '{name}' berhasil didaftarkan!\n\n"
        f"Client ID: `{client_id}`\n"
        f"Plan: 🆓 Free (default)\n"
        f"Tabel ter-update: {', '.join(result['tables_affected'])}\n\n"
        f"📌 Langkah selanjutnya:\n"
        f"1. Setup webhook di Fonnte Dashboard → {webhook_urls.get('webhook_path', '/webhook-whatsapp/' + client_id)}\n"
        f"2. Test customer chat ke nomor CS\n"
        f"3. Owner login & coba catat transaksi"
    )
    result["webhook_urls"] = webhook_urls
    return result


# ============================================================
# Check existing client
# ============================================================
def check_client_exists(core, client_id: str) -> dict[str, Any] | None:
    """Cek apakah client ada dan return info ringkasnya."""
    if not client_id:
        return None
    try:
        resp = (
            core.supabase.table("clients")
            .select("client_id, name, is_active, owner_phones, metadata, plan_tier")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        return rows[0]
    except Exception:
        return None


def list_all_clients(core) -> list[dict[str, Any]]:
    """List semua client (untuk admin monitoring)."""
    try:
        resp = (
            core.supabase.table("clients")
            .select("client_id, name, is_active, owner_phones, plan_tier, plan_expires_at, created_at")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.error("list_all_clients: %s", exc)
        return []