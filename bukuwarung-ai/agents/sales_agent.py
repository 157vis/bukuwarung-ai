"""SalesAgent — rekomendasi produk, harga, stok, promo."""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentContext, BaseAgent
from agents.data_access import products_from_context

HANDLE_INTENTS = frozenset({"sales", "product", "price"})

EXAMPLE_RESPONSES = [
    "Untuk bumbu dapur, kita ada 3 pilihan Bu: bawang goreng, cabe bubuk, dan ketumbar. Mau yang mana?",
    "Kopi sachet Rp 3.500/stick, stok masih 50. Mau ambil berapa?",
    "Ada promo beli 3 Indomie gratis 1 minggu ini. Mau sekalian?",
    "Gula pasir Rp 15.000/kg, stok terbatas 10 kg. Alternatifnya ada gula merah ya Bu.",
    "Kalau budget terbatas, Indomie dan kopi paling laris harga ramah di kantong.",
]

SYSTEM_PROMPT = """Kamu sales assistant warung UMKM Indonesia.
Tugas: rekomendasi produk, info harga, cek stok, promo.
Gaya persuasif tapi tidak maksa — selalu tawarkan alternatif.
Gunakan data produk yang diberikan. Jawab maksimal 4 kalimat."""


class SalesAgent(BaseAgent):
    """Sales — katalog & rekomendasi."""

    agent_id = "sales"
    name = "Sales Agent"
    description = "Rekomendasi, harga, stok, promo"
    capabilities = ["rekomendasi_produk", "info_harga", "stok", "promo"]
    priority = 70

    def get_name(self) -> str:
        return self.name

    def get_capabilities(self) -> list[str]:
        return list(self.capabilities)

    def can_handle(self, intent: str) -> bool:
        return intent.lower() in HANDLE_INTENTS

    def _catalog_text(self, context: AgentContext) -> str:
        products = products_from_context(context)
        if not products:
            return "Katalog kosong."
        lines = []
        for p in products[:15]:
            name = p.get("name", "?")
            price = int(p.get("price") or 0)
            stock = p.get("stock", "?")
            lines.append(f"- {name}: Rp {price:,} (stok {stock})".replace(",", "."))
        return "\n".join(lines)

    def _find_product(self, message: str, context: AgentContext) -> dict[str, Any] | None:
        lower = message.lower()
        for p in products_from_context(context):
            if str(p.get("name", "")).lower() in lower:
                return p
        return None

    async def process(
        self,
        message: str,
        context: AgentContext,
        personality: dict[str, Any],
    ) -> str:
        catalog = self._catalog_text(context)
        product = self._find_product(message, context)
        lower = message.lower()

        if not products_from_context(context):
            return "Maaf Bu, katalog produk sedang diperbarui. Coba lagi sebentar ya 🙏"

        if product:
            price = int(product.get("price") or 0)
            stock = product.get("stock", 0)
            if int(stock or 0) <= 0:
                return (
                    f"Maaf, {product['name']} sedang habis. "
                    "Mau coba produk lain? Saya bisa rekomendasikan alternatif."
                )
            return (
                f"{product['name'].title()} harga Rp {price:,} — stok {stock}. "
                "Mau pesan berapa?".replace(",", ".")
            )

        if any(w in lower for w in ("rekomendasi", "sarankan", "pilihan")):
            return EXAMPLE_RESPONSES[0]

        if any(w in lower for w in ("promo", "diskon")) or (
            "murah" in lower and "rekomendasi" not in lower
        ):
            return EXAMPLE_RESPONSES[2]

        if any(w in lower for w in ("stok", "ada", "tersedia")):
            return f"Stok terkini:\n{catalog}"

        system = (
            f"{SYSTEM_PROMPT}\n\nKatalog:\n{catalog}\n\n"
            f"Context:\n{context.otak_context[:400]}"
        )
        reply = await self._call_llm(message, system)
        if reply:
            return reply

        if any(w in lower for w in ("rekomendasi", "sarankan", "pilihan")):
            return EXAMPLE_RESPONSES[0]
        if "bumbu" in lower or "dapur" in lower:
            return EXAMPLE_RESPONSES[0]
        return EXAMPLE_RESPONSES[4]
