"""PaymentAgent — info pembayaran, konfirmasi transfer, cek status."""

from __future__ import annotations

import re
from typing import Any

from agents.base_agent import AgentContext, BaseAgent
from agents.data_access import OrderStore, load_payment_methods

HANDLE_INTENTS = frozenset({"payment", "bayar", "transfer"})

EXAMPLE_RESPONSES = [
    "Bisa transfer ke BCA 1234567890 a.n. Warung Berkah. Setelah transfer, kirim bukti ya Bu 🙏",
    "GoPay 081234567890 a.n. Warung Berkah. Nominal sesuai total pesanan.",
    "Pembayaran QRIS tersedia — scan di kasir atau minta kode QR ke admin.",
    "Terima kasih! Transfer Rp 78.000 kami terima. Pesanan diproses.",
    "Status pembayaran: menunggu konfirmasi. Mohon kirim bukti transfer jika belum.",
]

SYSTEM_PROMPT = """Kamu payment handler warung UMKM.
Tugas: info rekening/e-wallet, konfirmasi transfer, cek status bayar.
Selalu sebutkan nominal dan metode dengan jelas. Jangan minta PIN/password."""


class PaymentAgent(BaseAgent):
    """Payment — metode bayar & konfirmasi."""

    agent_id = "payment"
    name = "Payment Agent"
    description = "Info pembayaran & konfirmasi transfer"
    capabilities = ["info_pembayaran", "konfirmasi_transfer", "cek_status"]
    priority = 75

    def __init__(self, otak, personality, llm, order_store: OrderStore | None = None) -> None:
        super().__init__(otak, personality, llm)
        self._orders = order_store or OrderStore()

    def get_name(self) -> str:
        return self.name

    def get_capabilities(self) -> list[str]:
        return list(self.capabilities)

    def can_handle(self, intent: str) -> bool:
        return intent.lower() in HANDLE_INTENTS

    def _methods_text(self) -> str:
        methods = load_payment_methods()
        if not methods:
            return EXAMPLE_RESPONSES[0]
        lines = []
        for m in methods:
            if m.get("type") == "transfer":
                lines.append(
                    f"{m.get('bank')} {m.get('account_number')} a.n. {m.get('account_name')}"
                )
            elif m.get("type") == "ewallet":
                lines.append(
                    f"{m.get('provider')} {m.get('account_number')} a.n. {m.get('account_name')}"
                )
            else:
                lines.append(str(m.get("account_number", "QRIS")))
        return "\n".join(lines)

    async def process(
        self,
        message: str,
        context: AgentContext,
        personality: dict[str, Any],
    ) -> str:
        lower = message.lower()
        methods = self._methods_text()

        if any(w in lower for w in ("sudah bayar", "sudah transfer", "bukti")):
            amount_m = re.search(r"(\d[\d.,]*)\s*(rb|ribu)?", lower.replace(".", ""))
            nominal = ""
            if amount_m:
                val = int(amount_m.group(1).replace(",", ""))
                if amount_m.group(2):
                    val *= 1000
                nominal = f" Rp {val:,}".replace(",", ".")
            return f"Terima kasih! Konfirmasi transfer{nominal} kami catat. Pesanan segera diproses 🙏"

        if any(w in lower for w in ("status", "cek", "sudah masuk")):
            recent = await self._orders.list_orders(context.user_id, limit=1)
            if recent:
                st = recent[0].get("status", "pending")
                return f"Status pembayaran pesanan {recent[0]['id']}: {st}."
            return EXAMPLE_RESPONSES[4]

        if any(w in lower for w in ("qris", "gopay", "ovo", "dana")):
            for line in methods.split("\n"):
                if any(w in line.lower() for w in ("gopay", "qris", "ovo", "dana")):
                    return f"Bisa bayar via: {line}. Kirim bukti setelah bayar ya Bu."
            return EXAMPLE_RESPONSES[2]

        if any(w in lower for w in ("bayar", "transfer", "rekening", "pembayaran")):
            return f"Metode pembayaran:\n{methods}\n\nKirim bukti setelah transfer 🙏"

        system = f"{SYSTEM_PROMPT}\n\nMetode:\n{methods}\n\nContext:\n{context.otak_context[:400]}"
        reply = await self._call_llm(message, system)
        return reply or EXAMPLE_RESPONSES[0]
