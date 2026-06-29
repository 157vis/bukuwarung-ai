"""Orchestrator — koordinator multi-agent untuk WhatsApp CS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from agents.base_agent import AgentContext, BaseAgent
from config import get_settings
from core.otak_ai import OtakAI
from core.personality import PersonalityEngine
from core.semantic_router import RouteResult, SemanticRouter

logger = logging.getLogger(__name__)

# Intent confidence di bawah ini → minta klarifikasi
CLARIFY_THRESHOLD = 0.45
MAX_CLARIFY_ATTEMPTS = 2

ANGRY_KEYWORDS = frozenset(
    {
        "marah",
        "kecewa",
        "menyesal",
        "bodoh",
        "buruk",
        "licik",
        "penipu",
        "bohong",
        "sial",
        "jelek",
        "tidak puas",
        "komplain parah",
        "lapor polisi",
    }
)

CLARIFY_PROMPT = (
    "Maaf Bu/Pak, saya kurang paham maksudnya 🙏 "
    "Bisa dijelaskan lebih detail? (misalnya: mau pesan, tanya harga, atau bayar?)"
)

ESCALATE_PROMPT = (
    "Mohon maaf atas ketidaknyamanannya 🙏 "
    "Kami eskalasi ke tim CS manusia — akan menghubungi Anda segera. "
    "Terima kasih atas kesabarannya."
)

FALLBACK_ERROR = (
    "Maaf, ada kendala teknis sebentar. Tim CS kami siap bantu — silakan coba lagi ya 🙏"
)


@dataclass
class OrchestratorStats:
    """Statistik runtime orchestrator."""

    total_messages: int = 0
    total_response_ms: float = 0.0
    agent_usage: dict[str, int] = field(default_factory=dict)
    errors: int = 0
    clarifications: int = 0
    escalations: int = 0

    @property
    def avg_response_ms(self) -> float:
        if self.total_messages == 0:
            return 0.0
        return self.total_response_ms / self.total_messages

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_messages": self.total_messages,
            "avg_response_ms": round(self.avg_response_ms, 2),
            "agent_usage": dict(self.agent_usage),
            "errors": self.errors,
            "clarifications": self.clarifications,
            "escalations": self.escalations,
        }


class Orchestrator:
    """Main coordinator — routing, agent execution, personality, memory."""

    def __init__(
        self,
        otak_ai: OtakAI,
        router: SemanticRouter,
        personality: PersonalityEngine,
        agents_dict: dict[str, BaseAgent],
    ) -> None:
        self._otak = otak_ai
        self._router = router
        self._personality = personality
        self._agents = agents_dict
        self._cs_agent = agents_dict.get("cs") or next(iter(agents_dict.values()))
        self._stats = OrchestratorStats()
        self._clarify_counts: dict[str, int] = {}
        self._last_agent_id: str = "cs"
        self._last_intent: str = ""

    @property
    def stats(self) -> OrchestratorStats:
        return self._stats

    async def handle_message(self, user_id: str, message: str, client_id: str) -> str:
        """Pipeline lengkap 8 langkah — return teks balasan final.

        Args:
            user_id: ID pelanggan (nomor WA).
            message: Pesan masuk.
            client_id: ID toko / tenant.

        Returns:
            Respons final siap kirim ke WhatsApp.
        """
        t0 = time.perf_counter()
        text = (message or "").strip()
        agent_id = "cs"

        try:
            # 1. Terima message (sudah di argumen)

            # 2. Detect language
            user_lang = await self._personality.detect_language(text)

            # Sentimen marah → eskalasi human (edge case)
            if self._is_angry(text):
                self._stats.escalations += 1
                self._clarify_counts.pop(user_id, None)
                final = await self._personality.adapt_tone(
                    ESCALATE_PROMPT,
                    await self._personality.get_personality(client_id),
                    user_lang=user_lang,
                )
                await self._save_interaction(user_id, text, final, "support", "escalate")
                self._last_agent_id = "support"
                self._last_intent = "escalate"
                self._record_stats("support", t0)
                return final

            # 3. Semantic routing
            otak_ctx = await self._otak.bangun_context(user_id, text)
            route = await self._router.route(text, context=otak_ctx)

            # Intent unclear → klarifikasi max 2x
            if route.confidence < CLARIFY_THRESHOLD:
                count = self._clarify_counts.get(user_id, 0) + 1
                self._clarify_counts[user_id] = count
                self._stats.clarifications += 1
                if count <= MAX_CLARIFY_ATTEMPTS:
                    personality = await self._personality.get_personality(client_id)
                    final = await self._personality.adapt_tone(
                        CLARIFY_PROMPT, personality, user_lang=user_lang
                    )
                    await self._save_interaction(user_id, text, final, "cs", "clarify")
                    self._last_agent_id = "cs"
                    self._last_intent = "clarify"
                    self._record_stats("cs", t0)
                    return final
                # Setelah 2x → fallback CS, reset counter
                self._clarify_counts.pop(user_id, None)
                route = RouteResult("cs", "clarify_fallback", 0.5, "max clarify → cs")

            else:
                self._clarify_counts.pop(user_id, None)

            # 4. Personality config + agent selection
            personality = await self._personality.get_personality(client_id)
            agent = self._resolve_agent(route)
            agent_id = agent.agent_id

            owners = list(get_settings().owner_phone_set)
            is_owner = user_id in get_settings().owner_phone_set

            ctx = AgentContext(
                client_id=client_id,
                user_id=user_id,
                message=text,
                otak_context=otak_ctx,
                personality=personality,
                user_lang=user_lang,
                metadata={
                    "intent": route.intent,
                    "route": route.reason,
                    "confidence": route.confidence,
                    "is_owner": is_owner,
                    "owners": owners,
                },
            )

            # 5. Agent process
            raw = await self._safe_process(agent, ctx)

            # 6. Adapt tone
            final = await self._personality.adapt_tone(raw, personality, user_lang=user_lang)

            # 7. Simpan ke memory
            await self._save_interaction(user_id, text, final, agent_id, route.intent)

            # 8. Return
            self._last_agent_id = agent_id
            self._last_intent = route.intent
            self._record_stats(agent_id, t0)
            logger.info(
                "handle_message user=%s agent=%s intent=%s conf=%.2f ms=%.0f",
                user_id,
                agent_id,
                route.intent,
                route.confidence,
                (time.perf_counter() - t0) * 1000,
            )
            return final

        except Exception as exc:
            self._stats.errors += 1
            logger.exception("handle_message error user=%s: %s", user_id, exc)
            try:
                personality = await self._personality.get_personality(client_id)
            except Exception:
                personality = {"profile_key": "ramah_warm"}
            user_lang = "id"
            try:
                user_lang = await self._personality.detect_language(text)
            except Exception:
                pass
            final = await self._personality.adapt_tone(
                FALLBACK_ERROR, personality, user_lang=user_lang
            )
            await self._save_interaction(user_id, text, final, "cs", "error")
            self._last_agent_id = "cs"
            self._last_intent = "error"
            self._record_stats("cs", t0)
            return final

    async def process(
        self,
        *,
        client_id: str,
        user_id: str,
        message: str,
    ) -> OrchestratorResult:
        """Adapter kompatibel dengan API lama."""
        text = await self.handle_message(user_id, message, client_id)
        return OrchestratorResult(
            text=text,
            agent_id=self._last_agent_id,
            intent=self._last_intent,
            data={"route_confidence": 0.0},
        )

    def _resolve_agent(self, route: RouteResult) -> BaseAgent:
        agent = self._agents.get(route.agent)
        if agent and agent.can_handle(route.intent):
            return agent
        resolved = BaseAgent.resolve_conflict(list(self._agents.values()), route.intent)
        return resolved or self._cs_agent

    async def _safe_process(self, agent: BaseAgent, ctx: AgentContext) -> str:
        """Jalankan agent.process dengan fallback ke CS jika error."""
        try:
            raw = await agent.process(ctx.message, ctx, ctx.personality)
            if agent._validate_response(raw):
                return raw
            logger.warning("invalid response dari %s — fallback CS", agent.agent_id)
        except Exception as exc:
            logger.exception("agent %s error: %s", agent.agent_id, exc)
            self._stats.errors += 1

        try:
            raw = await self._cs_agent.process(ctx.message, ctx, ctx.personality)
            if self._cs_agent._validate_response(raw):
                return raw
        except Exception:
            logger.exception("CS fallback juga gagal")

        return FALLBACK_ERROR

    async def _save_interaction(
        self,
        user_id: str,
        user_msg: str,
        response: str,
        agent_id: str,
        intent: str,
    ) -> None:
        try:
            await self._otak.simpan_memory(
                user_id,
                {
                    "content": f"User: {user_msg[:200]} | Agent({agent_id}/{intent}): {response[:300]}",
                    "metadata": {"agent": agent_id, "intent": intent},
                },
            )
        except (OSError, ValueError, RuntimeError) as exc:
            logger.warning("simpan_memory gagal: %s", exc)

    def _record_stats(self, agent_id: str, t0: float) -> None:
        self._stats.total_messages += 1
        self._stats.total_response_ms += (time.perf_counter() - t0) * 1000
        self._stats.agent_usage[agent_id] = self._stats.agent_usage.get(agent_id, 0) + 1

    @staticmethod
    def _is_angry(text: str) -> bool:
        lower = text.lower()
        return any(kw in lower for kw in ANGRY_KEYWORDS)


@dataclass
class OrchestratorResult:
    """Hasil handle untuk kompatibilitas webhook lama."""

    text: str
    agent_id: str
    intent: str = ""
    data: dict[str, Any] = field(default_factory=dict)


# Alias backward-compatible
AgentOrchestrator = Orchestrator
