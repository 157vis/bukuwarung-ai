"""SupportAgent — komplain, troubleshooting, eskalasi."""

from __future__ import annotations

from typing import Any

from agents.base_agent import AgentContext, BaseAgent

HANDLE_INTENTS = frozenset({"support", "komplain", "error", "help"})

EXAMPLE_RESPONSES = [
    "Mohon maaf atas ketidaknyamanannya Bu 🙏 Kami akan segera cek pesanan Anda.",
    "Coba restart aplikasi / refresh chat dulu ya. Kalau masih error, kirim screenshot.",
    "Kami paham frustrasinya. Tim kami sedang investigasi — update dalam 1x24 jam.",
    "Untuk kasus ini kami eskalasi ke admin. Mohon tunggu, CS manusia akan menghubungi.",
    "Terima kasih sudah melapor. Apakah masalahnya terkait pesanan, pembayaran, atau aplikasi?",
]

SYSTEM_PROMPT = """Kamu technical support warung UMKM.
Tugas: tangani komplain, troubleshooting, eskalasi ke human jika parah.
Gaya empati, minta maaf, beri solusi konkret. Jangan debat dengan pelanggan."""


class SupportAgent(BaseAgent):
    """Support — komplain & troubleshooting."""

    agent_id = "support"
    name = "Support Agent"
    description = "Komplain, troubleshoot, eskalasi"
    capabilities = ["handle_komplain", "troubleshoot", "escalate"]
    priority = 65

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

        severe = any(
            w in lower
            for w in ("penipuan", "scam", "polisi", "media", "viral", "bohong", "tipu")
        )
        if severe:
            context.metadata["escalate"] = True
            return EXAMPLE_RESPONSES[3]

        if any(w in lower for w in ("error", "bug", "gagal", "tidak bisa", "crash")):
            return EXAMPLE_RESPONSES[1]

        if any(w in lower for w in ("komplain", "kecewa", "marah", "lambat", "salah")):
            return EXAMPLE_RESPONSES[0]

        if any(w in lower for w in ("bantu", "help", "tolong")):
            return EXAMPLE_RESPONSES[4]

        system = f"{SYSTEM_PROMPT}\n\nContext:\n{context.otak_context[:500]}"
        reply = await self._call_llm(message, system)
        if reply:
            return reply

        return EXAMPLE_RESPONSES[2]
