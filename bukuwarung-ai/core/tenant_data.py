"""Akses data per-tenant (clients + products) — backend service role.

FIX 2026-07-16: Sebelumnya query ke tabel `client_settings` (UUID PK), tapi
real schema pakai tabel `clients` (client_id text PK, UUID ada di metadata.user_id).
Sekarang lookup via `metadata->>user_id` di tabel `clients`.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    normalized = (phone or "").replace("@s.whatsapp.net", "").strip().lstrip("+")
    normalized = "".join(ch for ch in normalized if ch.isdigit())
    if normalized.startswith("0"):
        normalized = "62" + normalized[1:]
    return normalized


def parse_authorized_owners(raw: Any) -> frozenset[str]:
    """Parse `authorized_owners` dari JSONB/list/string → frozenset phone numbers."""
    phones: list[str] = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        items = [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]
    else:
        items = []
    for item in items:
        digits = normalize_phone(str(item))
        if digits:
            phones.append(digits)
    return frozenset(phones)


def _parse_metode_bayar(raw: Any) -> list[str]:
    """Parse metode_bayar dari array/string → list of strings."""
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        return [s.strip() for s in raw.split(",") if s.strip()]
    return []


@dataclass
class TenantContext:
    """Konteks tenant untuk orchestrator (dashboard user_id = UUID)."""

    user_id: str
    client_id: str = ""
    business_name: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    products: list[dict[str, Any]] = field(default_factory=list)
    authorized_owners: frozenset[str] = field(default_factory=frozenset)

    # === Info toko untuk CS Agent (kolom baru Phase 3) ===
    jam_buka: str = "07:00"
    jam_tutup: str = "21:00"
    hari_operasional: str = "Setiap hari"
    alamat: str = ""
    kota: str = ""
    no_telp: str = ""
    ongkir_info: str = ""
    metode_bayar: list[str] = field(default_factory=list)
    tagline: str = ""
    profile_key: str = "ramah_warm"

    @property
    def display_name(self) -> str:
        return (self.business_name or "Toko").strip() or "Toko"

    def to_cs_prompt(self) -> str:
        """Render ringkasan toko untuk dimasukkan ke system prompt CS Agent."""
        lines = [
            f"Nama toko: {self.display_name}",
            f"Jam buka: {self.jam_buka} - {self.jam_tutup} ({self.hari_operasional})",
        ]
        if self.alamat:
            lokasi = self.alamat
            if self.kota:
                lokasi = f"{lokasi}, {self.kota}"
            lines.append(f"Lokasi: {lokasi}")
        if self.no_telp:
            lines.append(f"Telepon: {self.no_telp}")
        if self.metode_bayar:
            lines.append(f"Metode bayar: {', '.join(self.metode_bayar)}")
        if self.ongkir_info:
            lines.append(f"Ongkir: {self.ongkir_info}")
        if self.tagline:
            lines.append(f"Tagline: {self.tagline}")
        return "\n".join(lines)


async def fetch_client_by_user_id(db: Any, user_id: str) -> dict[str, Any] | None:
    """Lookup client row dari tabel `clients` berdasarkan metadata->>user_id.

    Returns: dict dengan semua kolom clients, atau None kalau tidak ketemu.
    Schema real tabel clients:
      client_id, name, fonnte_token, owner_phones, profile_key,
      products (jsonb), payment_methods (jsonb), is_active, metadata (jsonb),
      business_name, jam_buka, jam_tutup, hari_operasional, alamat, kota,
      no_telp, ongkir_info, metode_bayar (array), tagline, plan_tier, ...
    """
    uid = str(user_id).strip()
    if not uid:
        return None
    try:
        result = await asyncio.to_thread(
            lambda: (
                db.table("clients")
                .select("*")
                .eq("metadata->>user_id", uid)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error("fetch_client_by_user_id user=%s: %s", uid, exc)
        return None


async def fetch_client_by_client_id(db: Any, client_id: str) -> dict[str, Any] | None:
    """Lookup client row dari tabel `clients` berdasarkan client_id (PK)."""
    cid = str(client_id).strip()
    if not cid:
        return None
    try:
        result = await asyncio.to_thread(
            lambda: (
                db.table("clients")
                .select("*")
                .eq("client_id", cid)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error("fetch_client_by_client_id client_id=%s: %s", cid, exc)
        return None


# Backward-compat alias (dipakai di tempat lain kalau ada)
async def fetch_client_settings(db: Any, user_id: str) -> dict[str, Any] | None:
    """DEPRECATED: Pakai fetch_client_by_user_id. Disini untuk backward compat."""
    return await fetch_client_by_user_id(db, user_id)


async def fetch_products(db: Any, user_id: str) -> list[dict[str, Any]]:
    """Ambil daftar produk milik tenant."""
    uid = str(user_id).strip()
    if not uid:
        return []
    try:
        result = await asyncio.to_thread(
            lambda: (
                db.table("products")
                .select("id, name, stock, price, category, is_active, created_at")
                .eq("user_id", uid)
                .order("name")
                .execute()
            )
        )
        return list(result.data or [])
    except Exception as exc:
        logger.error("fetch_products user=%s: %s", uid, exc)
        return []


async def build_tenant_context(db: Any, user_id: str) -> TenantContext:
    """Build TenantContext lengkap (info toko + products) dari tabel clients."""
    client_row = await fetch_client_by_user_id(db, user_id)
    products = await fetch_products(db, user_id)

    if not client_row:
        logger.warning("build_tenant_context: no client for user_id=%s", user_id)
        return TenantContext(
            user_id=str(user_id).strip(),
            products=products,
        )

    # === Parse metadata (backward compat) ===
    metadata = client_row.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    # === Combine: kolom langsung > metadata fallback ===
    business_name = (
        client_row.get("business_name")
        or metadata.get("business_name")
        or client_row.get("name")
        or ""
    )
    jam_buka = client_row.get("jam_buka") or metadata.get("jam_buka") or "07:00"
    jam_tutup = client_row.get("jam_tutup") or metadata.get("jam_tutup") or "21:00"
    hari_operasional = (
        client_row.get("hari_operasional")
        or metadata.get("hari_operasional")
        or "Setiap hari"
    )
    alamat = client_row.get("alamat") or metadata.get("alamat") or ""
    kota = client_row.get("kota") or metadata.get("kota") or ""
    no_telp = client_row.get("no_telp") or metadata.get("no_telp") or ""
    ongkir_info = client_row.get("ongkir_info") or metadata.get("ongkir_info") or ""
    tagline = client_row.get("tagline") or metadata.get("tagline") or ""

    metode_bayar_raw = client_row.get("metode_bayar")
    if metode_bayar_raw:
        metode_bayar = _parse_metode_bayar(metode_bayar_raw)
    else:
        metode_bayar = _parse_metode_bayar(metadata.get("metode_bayar"))

    # === Authorized owners ===
    authorized_raw = client_row.get("owner_phones") or metadata.get("authorized_owners")
    authorized_owners = parse_authorized_owners(authorized_raw)

    # === Profile key (personality) ===
    profile_key = (
        client_row.get("profile_key")
        or metadata.get("profile_key")
        or "ramah_warm"
    )

    return TenantContext(
        user_id=str(user_id).strip(),
        client_id=client_row.get("client_id", ""),
        business_name=str(business_name).strip(),
        settings=client_row,
        products=products,
        authorized_owners=authorized_owners,
        jam_buka=str(jam_buka).strip(),
        jam_tutup=str(jam_tutup).strip(),
        hari_operasional=str(hari_operasional).strip(),
        alamat=str(alamat).strip(),
        kota=str(kota).strip(),
        no_telp=str(no_telp).strip(),
        ongkir_info=str(ongkir_info).strip(),
        metode_bayar=metode_bayar,
        tagline=str(tagline).strip(),
        profile_key=str(profile_key).strip() or "ramah_warm",
    )


def format_products_for_prompt(products: list[dict[str, Any]], *, limit: int = 20) -> str:
    if not products:
        return "(Belum ada produk di katalog — jangan mengarang nama/harga produk.)"
    lines: list[str] = []
    for p in products[:limit]:
        name = str(p.get("name") or "").strip()
        if not name:
            continue
        stock = p.get("stock")
        price = p.get("price")
        extra = []
        if price is not None:
            extra.append(f"Rp {int(price):,}")
        if stock is not None:
            extra.append(f"stok {int(stock)}")
        suffix = f" ({', '.join(extra)})" if extra else ""
        lines.append(f"- {name}{suffix}")
    return "\n".join(lines) if lines else "(Katalog produk kosong.)"