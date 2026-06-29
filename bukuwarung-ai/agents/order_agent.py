"""OrderAgent — buat, track, update, batalkan pesanan."""

from __future__ import annotations

import re
from typing import Any

from agents.base_agent import AgentContext, AgentResponse, BaseAgent
from agents.data_access import OrderStore, products_from_context

HANDLE_INTENTS = frozenset({"order", "pesan", "beli"})

EXAMPLE_RESPONSES = [
    "Siap Bu! Pesanan 5kg beras + 2L minyak ya? Total Rp 78.000. Konfirmasi untuk lanjut 🙏",
    "Pesanan ORD-A1B2C3D4 status: menunggu pembayaran. Mau cek detail?",
    "Pesanan berhasil diupdate. Jumlah kopi jadi 3 pack.",
    "Pesanan dibatalkan sesuai permintaan. Silakan order ulang kapan saja.",
    "Mohon sebut produk dan jumlahnya ya Bu. Contoh: _pesan kopi 2 pack_",
]

SYSTEM_PROMPT = """Kamu order handler warung UMKM.
Tugas: buat pesanan, lacak status, update, batalkan.
Selalu konfirmasi item + total + nomor order. Tanya detail jika kurang jelas."""


def _parse_amount(text: str) -> int | None:
    """Ekstrak nominal dari teks (50rb, 50000, 50.000)."""
    lower = text.lower().replace(".", "").replace(",", "")
    m = re.search(r"(\d+)\s*(rb|ribu|k)?", lower)
    if not m:
        return None
    val = int(m.group(1))
    if m.group(2) in ("rb", "ribu", "k"):
        val *= 1000
    return val


class OrderAgent(BaseAgent):
    """Order — CRUD pesanan via OrderStore."""

    agent_id = "order"
    name = "Order Agent"
    description = "Buat, track, update, batalkan pesanan"
    capabilities = ["buat_pesanan", "track_order", "update_pesanan", "batal"]
    priority = 80

    def __init__(self, otak, personality, llm, order_store: OrderStore | None = None) -> None:
        super().__init__(otak, personality, llm)
        self._orders = order_store or OrderStore()
        self._last_data: dict[str, Any] = {}

    def get_name(self) -> str:
        return self.name

    def get_capabilities(self) -> list[str]:
        return list(self.capabilities)

    def can_handle(self, intent: str) -> bool:
        return intent.lower() in HANDLE_INTENTS

    def _match_items(self, message: str, context: AgentContext) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        lower = message.lower()
        for p in products_from_context(context):
            name = str(p.get("name", "")).lower()
            if name and name in lower:
                qty_m = re.search(rf"{re.escape(name)}\s*(\d+)", lower)
                qty = int(qty_m.group(1)) if qty_m else 1
                price = int(p.get("price") or 0)
                items.append({"name": name, "qty": qty, "price": price})
        return items

    async def process(
        self,
        message: str,
        context: AgentContext,
        personality: dict[str, Any],
    ) -> str:
        self._last_data = {}
        lower = message.lower()
        amount = _parse_amount(message)
        if amount:
            self._last_data["amount"] = amount

        if any(w in lower for w in ("batal", "cancel")):
            self._last_data["action"] = "cancel"
            return EXAMPLE_RESPONSES[3]

        if any(w in lower for w in ("track", "lacak", "status", "ord-")):
            oid_m = re.search(r"ord-[a-z0-9]+", lower)
            if oid_m:
                order = await self._orders.get_order(oid_m.group(0).upper())
                if order:
                    self._last_data["order_id"] = order["id"]
                    return (
                        f"Pesanan {order['id']} status: {order.get('status', '?')}. "
                        f"Total Rp {int(order.get('total', 0)):,}".replace(",", ".")
                    )
            recent = await self._orders.list_orders(context.user_id, limit=1)
            if recent:
                o = recent[0]
                self._last_data["order_id"] = o["id"]
                return f"Pesanan terakhir {o['id']}: {o.get('status')} — Rp {int(o.get('total', 0)):,}".replace(",", ".")
            return "Belum ada pesanan aktif. Mau buat pesanan baru?"

        if any(w in lower for w in ("update", "ubah", "ganti")):
            self._last_data["action"] = "update"
            return EXAMPLE_RESPONSES[2]

        items = self._match_items(message, context)
        if not items and amount:
            items = [{"name": "custom", "qty": 1, "price": amount}]
        if not items:
            if any(w in lower for w in ("pesan", "order", "beli", "jual")):
                return EXAMPLE_RESPONSES[4]
            system = f"{SYSTEM_PROMPT}\n\nContext:\n{context.otak_context[:400]}"
            reply = await self._call_llm(message, system)
            return reply or EXAMPLE_RESPONSES[4]

        total = sum(i["price"] * i["qty"] for i in items)
        order = await self._orders.create_order(context.user_id, items, total, note=message[:200])
        self._last_data.update({"order_id": order["id"], "total": total, "items": items})

        names = " + ".join(f"{i['qty']}x {i['name']}" for i in items)
        return (
            f"Siap Bu! Pesanan {names} ya? Total Rp {total:,}. "
            f"No. order: {order['id']}. Konfirmasi untuk lanjut 🙏".replace(",", ".")
        )

    async def handle(self, ctx: AgentContext) -> AgentResponse:
        resp = await super().handle(ctx)
        if self._last_data:
            resp.data.update(self._last_data)
        return resp
