"""Shared data access untuk agent — products, orders, payment (portable + fallback)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"
TABLE_ORDERS = "orders"


def load_products() -> list[dict[str, Any]]:
    """Muat katalog dari data/products.json."""
    path = DATA_DIR / "products.json"
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("load_products gagal: %s", exc)
    return []


def load_payment_methods() -> list[dict[str, Any]]:
    """Muat metode pembayaran dari data/payment_methods.json."""
    path = DATA_DIR / "payment_methods.json"
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("load_payment_methods gagal: %s", exc)
    return []


class OrderStore:
    """CRUD pesanan — Supabase dengan fallback dict lokal."""

    def __init__(self, supabase_client: Any | None = None) -> None:
        self._db = supabase_client
        self._local: dict[str, dict[str, Any]] = {}
        self._use_local = supabase_client is None

    async def create_order(
        self,
        user_id: str,
        items: list[dict[str, Any]],
        total: int,
        note: str = "",
    ) -> dict[str, Any]:
        """Buat pesanan baru."""
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        row = {
            "id": order_id,
            "user_id": user_id,
            "items": items,
            "total": total,
            "status": "pending",
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if self._use_local:
            self._local[order_id] = row
            return row
        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(TABLE_ORDERS).insert(row).execute()
            )
            return (result.data or [row])[0]
        except (OSError, ValueError, KeyError, AttributeError) as exc:
            logger.warning("create_order supabase gagal: %s", exc)
            self._local[order_id] = row
            return row

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        if order_id in self._local:
            return self._local[order_id]
        if self._use_local:
            return None
        try:
            result = await asyncio.to_thread(
                lambda: (
                    self._db.table(TABLE_ORDERS)
                    .select("*")
                    .eq("id", order_id)
                    .limit(1)
                    .execute()
                )
            )
            rows = result.data or []
            return rows[0] if rows else None
        except (OSError, ValueError, KeyError, AttributeError):
            return None

    async def list_orders(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        local = [o for o in self._local.values() if o.get("user_id") == user_id]
        if self._use_local:
            return sorted(local, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]
        try:
            result = await asyncio.to_thread(
                lambda: (
                    self._db.table(TABLE_ORDERS)
                    .select("*")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
            )
            return result.data or []
        except (OSError, ValueError, KeyError, AttributeError):
            return local[:limit]

    async def daily_stats(self, client_id: str) -> dict[str, Any]:
        """Statistik harian sederhana (admin)."""
        orders = list(self._local.values()) if self._use_local else []
        if not self._use_local and self._db:
            try:
                result = await asyncio.to_thread(
                    lambda: self._db.table(TABLE_ORDERS).select("*").limit(200).execute()
                )
                orders = result.data or []
            except (OSError, ValueError, KeyError, AttributeError):
                orders = list(self._local.values())

        total_orders = len(orders)
        revenue = sum(int(o.get("total") or 0) for o in orders)
        product_counts: dict[str, int] = {}
        for o in orders:
            for item in o.get("items") or []:
                name = str(item.get("name", "lainnya"))
                product_counts[name] = product_counts.get(name, 0) + int(item.get("qty") or 1)
        best = max(product_counts, key=product_counts.get) if product_counts else "-"
        return {
            "orders": total_orders,
            "revenue": revenue,
            "best_seller": best,
            "client_id": client_id,
        }
