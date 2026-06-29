"""AdminAgent — laporan owner (read-only)."""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentContext, BaseAgent
from agents.data_access import OrderStore, load_products

HANDLE_INTENTS = frozenset({"admin", "laporan", "owner", "statistik"})

EXAMPLE_RESPONSES = [
    "Laporan hari ini: 47 pesanan, omzet Rp 3.2jt, best seller: beras.",
    "| Metrik | Nilai |\n|--------|-------|\n| Pesanan | 47 |\n| Omzet | Rp 3.200.000 |\n| Best seller | beras |",
    "Statistik minggu ini sedang dikumpulkan. Minta _laporan harian_ untuk data terbaru.",
    "Akses admin khusus owner. Jika Anda bukan owner, hubungi CS.",
    "Best seller: kopi (120 unit), diikuti indomie (85 unit).",
]

SYSTEM_PROMPT = """Kamu admin assistant untuk OWNER warung (read-only).
Tugas: laporan harian, statistik, omzet, best seller.
Format data-driven dengan angka dan tabel markdown jika perlu.
Jangan ekspos data pelanggan sensitif."""


class AdminAgent(BaseAgent):
    """Admin — laporan & statistik untuk owner."""

    agent_id = "admin"
    name = "Admin Agent"
    description = "Laporan harian, omzet, statistik owner"
    capabilities = ["laporan_harian", "statistik", "omzet", "best_seller"]
    priority = 90

    def __init__(self, otak, personality, llm, order_store: OrderStore | None = None) -> None:
        super().__init__(otak, personality, llm)
        self._orders = order_store or OrderStore()

    def get_name(self) -> str:
        return self.name

    def get_capabilities(self) -> list[str]:
        return list(self.capabilities)

    def can_handle(self, intent: str) -> bool:
        return intent.lower() in HANDLE_INTENTS

    def _is_owner(self, context: AgentContext) -> bool:
        owners = context.metadata.get("owners") or context.personality.get("owners") or []
        if not owners:
            return context.metadata.get("is_owner", False)
        return context.user_id in owners

    def _format_report(self, stats: dict[str, Any]) -> str:
        rev = int(stats.get("revenue") or 0)
        orders = int(stats.get("orders") or 0)
        best = stats.get("best_seller", "-")
        if rev >= 1_000_000:
            rev_str = f"Rp {rev / 1_000_000:.1f}jt"
        else:
            rev_str = f"Rp {rev:,}".replace(",", ".")
        return (
            f"Laporan hari ini: {orders} pesanan, omzet {rev_str}, best seller: {best}.\n\n"
            f"| Metrik | Nilai |\n|--------|-------|\n"
            f"| Pesanan | {orders} |\n| Omzet | {rev_str} |\n| Best seller | {best} |"
        )

    async def process(
        self,
        message: str,
        context: AgentContext,
        personality: dict[str, Any],
    ) -> str:
        if not self._is_owner(context):
            return EXAMPLE_RESPONSES[3]

        lower = message.lower()
        stats = await self._orders.daily_stats(context.client_id)

        if any(w in lower for w in ("best", "laris", "terlaris")):
            products = load_products()
            if products:
                top = sorted(products, key=lambda p: int(p.get("stock", 0)), reverse=True)[:3]
                names = ", ".join(f"{p['name']} (stok {p.get('stock')})" for p in top)
                return f"Produk aktif: {names}. {EXAMPLE_RESPONSES[4]}"
            return EXAMPLE_RESPONSES[4]

        if stats["orders"] == 0:
            if any(w in lower for w in ("contoh", "demo")):
                return self._format_report(
                    {"orders": 47, "revenue": 3_200_000, "best_seller": "beras"}
                )
            return (
                "Laporan hari ini: belum ada transaksi. Omzet Rp 0.\n\n"
                "| Metrik | Nilai |\n|--------|-------|\n| Pesanan | 0 |\n| Omzet | Rp 0 |"
            )

        return self._format_report(stats)
