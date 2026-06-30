"""Akses data per-tenant (client_settings, products) — backend service role."""

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


@dataclass
class TenantContext:
    """Konteks tenant untuk orchestrator (dashboard user_id = UUID)."""

    user_id: str
    business_name: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    products: list[dict[str, Any]] = field(default_factory=list)
    authorized_owners: frozenset[str] = field(default_factory=frozenset)

    @property
    def display_name(self) -> str:
        return (self.business_name or "Toko").strip() or "Toko"


async def fetch_client_settings(db: Any, user_id: str) -> dict[str, Any] | None:
    uid = str(user_id).strip()
    if not uid:
        return None
    try:
        result = await asyncio.to_thread(
            lambda: (
                db.table("client_settings")
                .select("*")
                .eq("user_id", uid)
                .limit(1)
                .execute()
            )
        )
        rows = result.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.error("fetch_client_settings user=%s: %s", uid, exc)
        return None


async def fetch_products(db: Any, user_id: str) -> list[dict[str, Any]]:
    uid = str(user_id).strip()
    if not uid:
        return []
    try:
        result = await asyncio.to_thread(
            lambda: (
                db.table("products")
                .select("id, name, stock, price, created_at")
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
    settings = await fetch_client_settings(db, user_id) or {}
    products = await fetch_products(db, user_id)
    owners = parse_authorized_owners(settings.get("authorized_owners"))
    return TenantContext(
        user_id=str(user_id).strip(),
        business_name=str(settings.get("business_name") or "").strip(),
        settings=settings,
        products=products,
        authorized_owners=owners,
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
