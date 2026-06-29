"""CSAgent — customer service, sapaan & info umum."""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentContext, BaseAgent

HANDLE_INTENTS = frozenset({"cs", "greeting", "info"})

EXAMPLE_RESPONSES = [
    "Halo Bu! 🙏 Warung buka jam 7 pagi - 9 malam. Ada yang bisa dibantu?",
    "Selamat datang! Kami siap bantu info produk, pesanan, atau pembayaran.",
    "Halo! Untuk lokasi: Jl. Pasar Baru No. 12. Mau order bisa langsung chat di sini ya.",
    "Terima kasih sudah menghubungi kami. Jam operasional: 07.00-21.00 WIB setiap hari.",
]

SYSTEM_PROMPT = """Kamu CS ramah warung UMKM Indonesia.
Tugas: sapaan, info umum, jam operasional, lokasi.
Jika user minta harga/pesan/bayar, arahkan sopan ke tim terkait.
Jawab singkat, hangat, maksimal 3 kalimat."""


class CSAgent(BaseAgent):
    """Customer service — pintu masuk percakapan."""

    agent_id = "cs"
    name = "CS Agent"
    description = "Sapaan, info umum, jam & lokasi"
    capabilities = ["sapaan", "info_umum", "jam_operasional", "lokasi"]
    priority = 60

    def get_name(self) -> str:
        return self.name

    def get_capabilities(self) -> list[str]:
        return list(self.capabilities)

    def can_handle(self, intent: str) -> bool:
        return intent.lower() in HANDLE_INTENTS

    async def process(
        self,
        message: str,
        context: AgentContext,
        personality: dict[str, Any],
    ) -> str:
        lower = message.lower()

        if any(w in lower for w in ("harga", "promo", "rekomendasi")):
            return (
                "Untuk info harga dan rekomendasi produk, tim sales kami siap bantu. "
                "Sebut saja produk yang Bu cari ya!"
            )
        if any(w in lower for w in ("pesan", "order", "beli", "jual")):
            return "Untuk pemesanan, silakan sebut produk + jumlahnya. Contoh: _pesan beras 5kg_ 🙏"
        if any(w in lower for w in ("bayar", "transfer", "qris")):
            return "Untuk pembayaran, tim kami akan kirim detail rekening/e-wallet. Mau lanjut bayar?"

        system = f"{SYSTEM_PROMPT}\n\nContext:\n{context.otak_context[:600]}"
        reply = await self._call_llm(message, system)
        if reply:
            return reply

        if any(w in lower for w in ("jam", "buka", "tutup", "operasional")):
            return EXAMPLE_RESPONSES[0]
        if any(w in lower for w in ("lokasi", "alamat", "dimana")):
            return EXAMPLE_RESPONSES[2]
        if any(w in lower for w in ("halo", "hai", "pagi", "siang")):
            return EXAMPLE_RESPONSES[1]
        return EXAMPLE_RESPONSES[3]
