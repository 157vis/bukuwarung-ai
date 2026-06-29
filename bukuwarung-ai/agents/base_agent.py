"""Abstract base class untuk 6 agent spesialis BukuWarung-AI."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.otak_ai import OtakAI
    from core.personality import PersonalityEngine
    from utils.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

# Respons terlalu pendek/panjang atau kata terlarang
MIN_RESPONSE_LEN = 3
MAX_RESPONSE_LEN = 4000
FORBIDDEN_WORDS = frozenset(
    {
        "password",
        "token rahasia",
        "api key",
        "bunuh",
        "bom",
        "hack",
        "curang",
        "penipuan",
    }
)


@dataclass
class AgentContext:
    """Context eksekusi agent yang dioper ke ``process()``."""

    client_id: str
    user_id: str
    message: str
    otak_context: str = ""
    personality: dict[str, Any] = field(default_factory=dict)
    user_lang: str = "id"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Balasan terstruktur setelah pipeline base agent."""

    text: str
    agent_id: str
    intent: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract agent — subclass wajib implement ``process`` & metadata methods.

    Dependency injection:
        otak: OtakAI untuk memory & logging interaksi.
        personality: PersonalityEngine untuk adaptasi tone.
        llm: OpenRouterClient untuk pemanggilan model.

    Attributes:
        agent_id: Slug unik agent (mis. ``cs``, ``order``).
        name: Nama tampilan agent.
        description: Deskripsi singkat peran agent.
        capabilities: Daftar kemampuan untuk routing/dokumentasi.
        priority: Prioritas saat conflict resolution (lebih tinggi menang).
    """

    agent_id: str = "base"
    name: str = "Base Agent"
    description: str = ""
    capabilities: list[str] = []
    priority: int = 50

    def __init__(
        self,
        otak: OtakAI,
        personality: PersonalityEngine,
        llm: OpenRouterClient,
    ) -> None:
        """Inisialisasi agent dengan dependensi inti.

        Args:
            otak: Sistem memory & context.
            personality: Engine brand voice per client.
            llm: Client OpenRouter untuk inference.
        """
        self._otak = otak
        self._personality = personality
        self._llm = llm
        self._logger = logging.getLogger(f"agent.{self.agent_id}")

    # ------------------------------------------------------------------
    # Abstract API (wajib di subclass)
    # ------------------------------------------------------------------

    @abstractmethod
    async def process(
        self,
        message: str,
        context: AgentContext,
        personality: dict[str, Any],
    ) -> str:
        """Proses pesan user dan kembalikan teks respons mentah.

        Args:
            message: Pesan masuk dari user.
            context: Context lengkap (otak, metadata, user_id).
            personality: Config brand voice client.

        Returns:
            Teks balasan sebelum formatting personality.
        """

    @abstractmethod
    def get_name(self) -> str:
        """Nama tampilan agent."""

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Daftar kemampuan agent untuk dokumentasi / routing."""

    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Return True jika agent ini cocok menangani intent."""

    # ------------------------------------------------------------------
    # Orchestrator adapter (konkret — memanggil abstract methods)
    # ------------------------------------------------------------------

    async def handle(self, ctx: AgentContext) -> AgentResponse:
        """Pipeline standar — dipanggil ``AgentOrchestrator``.

        Alur: can_handle → process → validate → format → log memory.

        Args:
            ctx: Context eksekusi dari orchestrator.

        Returns:
            ``AgentResponse`` siap kirim ke WhatsApp.
        """
        intent = str(ctx.metadata.get("intent") or self.agent_id)

        if not self.can_handle(intent):
            self._logger.info(
                "agent %s menolak intent %s (priority=%s)",
                self.agent_id,
                intent,
                self.priority,
            )
            return AgentResponse(
                text="",
                agent_id=self.agent_id,
                intent=intent,
                data={"skipped": True},
            )

        raw = await self.process(ctx.message, ctx, ctx.personality)

        if not self._validate_response(raw):
            self._logger.warning("response invalid dari %s — pakai fallback", self.agent_id)
            raw = "Maaf, ada kendala memproses pesan Anda. Silakan coba lagi."

        formatted = await self._format_response(raw, ctx.personality, ctx.user_lang)
        await self._log_interaction(ctx.user_id, intent, formatted)

        self._logger.info(
            "handle OK agent=%s user=%s intent=%s len=%d",
            self.agent_id,
            ctx.user_id,
            intent,
            len(formatted),
        )
        return AgentResponse(
            text=formatted,
            agent_id=self.agent_id,
            intent=intent,
            data={"agent_name": self.get_name()},
        )

    # ------------------------------------------------------------------
    # Helper methods (implementasi di base)
    # ------------------------------------------------------------------

    async def _call_llm(self, prompt: str, system_prompt: str) -> str:
        """Panggil OpenRouter dengan system + user prompt.

        Args:
            prompt: Pesan user / instruksi utama.
            system_prompt: System prompt agent.

        Returns:
            Teks jawaban model, atau string kosong jika gagal.
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            reply = await self._llm.chat(messages)
            self._logger.debug("LLM %s → %d chars", self.agent_id, len(reply))
            return reply
        except (OSError, ValueError, RuntimeError, KeyError) as exc:
            self._logger.warning("_call_llm gagal [%s]: %s", self.agent_id, exc)
            return ""

    async def _log_interaction(self, user_id: str, intent: str, response: str) -> None:
        """Simpan interaksi ke OtakAI long-term memory.

        Args:
            user_id: ID pelanggan.
            intent: Intent yang ditangani.
            response: Balasan final ke user.
        """
        try:
            await self._otak.simpan_memory(
                user_id,
                {
                    "content": f"[{self.agent_id}/{intent}] {response[:300]}",
                    "metadata": {"agent": self.agent_id, "intent": intent},
                },
            )
        except (OSError, ValueError, RuntimeError) as exc:
            self._logger.warning("_log_interaction gagal: %s", exc)

    async def _format_response(
        self,
        text: str,
        personality: dict[str, Any],
        user_lang: str = "id",
    ) -> str:
        """Terapkan brand voice via PersonalityEngine.

        Args:
            text: Respons mentah dari ``process``.
            personality: Config personality client.
            user_lang: Kode bahasa user.

        Returns:
            Teks dengan tone disesuaikan.
        """
        return await self._personality.adapt_tone(text, personality, user_lang=user_lang)

    def _validate_response(self, response: str) -> bool:
        """Validasi panjang & kata terlarang.

        Args:
            response: Teks respons mentah.

        Returns:
            True jika lolos validasi.
        """
        if not response or not response.strip():
            return False
        if len(response) < MIN_RESPONSE_LEN or len(response) > MAX_RESPONSE_LEN:
            return False
        lower = response.lower()
        if any(word in lower for word in FORBIDDEN_WORDS):
            self._logger.warning("forbidden word detected in response")
            return False
        return True

    # ------------------------------------------------------------------
    # Properties (akses metadata subclass)
    # ------------------------------------------------------------------

    @property
    def agent_name(self) -> str:
        """Alias property — delegasi ke ``get_name()``."""
        return self.get_name()

    @property
    def agent_description(self) -> str:
        """Deskripsi agent dari class attribute."""
        return self.description

    @property
    def agent_capabilities(self) -> list[str]:
        """Capabilities — delegasi ke ``get_capabilities()``."""
        return self.get_capabilities()

    @property
    def agent_priority(self) -> int:
        """Prioritas conflict resolution."""
        return self.priority

    @staticmethod
    def resolve_conflict(candidates: list[BaseAgent], intent: str) -> BaseAgent | None:
        """Pilih agent dengan priority tertinggi yang bisa handle intent.

        Args:
            candidates: Daftar agent kandidat.
            intent: Intent routing.

        Returns:
            Agent terpilih atau None.
        """
        eligible = [a for a in candidates if a.can_handle(intent)]
        if not eligible:
            return None
        chosen = max(eligible, key=lambda a: a.priority)
        logger.info("resolve_conflict intent=%s → %s (p=%s)", intent, chosen.agent_id, chosen.priority)
        return chosen
