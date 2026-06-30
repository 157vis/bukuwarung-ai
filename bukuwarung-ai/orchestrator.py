"""Orchestrator — koordinator multi-agent untuk WhatsApp CS (Multi-Tenant)."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from agents.base_agent import AgentContext, BaseAgent
from config import get_settings
from core.client_registry import ClientConfig
from core.otak_ai import OtakAI
from core.personality import PersonalityEngine
from core.semantic_router import RouteResult, SemanticRouter
from core.tenant_bridge import get_tenant_core
from core.tenant_data import (
    TenantContext,
    build_tenant_context,
    format_products_for_prompt,
    normalize_phone,
)
from utils.supabase import get_supabase_admin

logger = logging.getLogger(__name__)

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

UNAUTHORIZED_CATAT = (
    "Maaf, nomor Anda tidak terdaftar sebagai pemilik toko ini. "
    "Hubungi admin untuk mendaftarkan nomor di Pengaturan Bot."
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
    """Main coordinator — routing CS & Catat per tenant (`user_id` dashboard)."""

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

    @property
    def _llm(self):
        return self._cs_agent._llm

    # ------------------------------------------------------------------
    # Multi-tenant entry points (webhook /webhook/csat & /webhook/catat)
    # ------------------------------------------------------------------

    async def route_cs_message(
        self,
        user_id: str,
        sender_phone: str,
        message: str,
    ) -> OrchestratorResult:
        """Route pesan CS pelanggan — `user_id` = UUID tenant (dashboard)."""
        tenant = await self._load_tenant_context(user_id)
        phone = normalize_phone(sender_phone)
        client_config = self._client_config_from_tenant(tenant)
        text = await self.handle_message(
            phone,
            message,
            user_id,
            client_config=client_config,
            tenant=tenant,
        )
        return OrchestratorResult(
            text=text,
            agent_id=self._last_agent_id,
            intent=self._last_intent,
            data={"channel": "csat", "tenant_user_id": user_id},
        )

    async def route_catat_message(
        self,
        user_id: str,
        sender_phone: str,
        message: str,
    ) -> OrchestratorResult:
        """Route perintah catat owner — `user_id` = UUID tenant (dashboard)."""
        tenant = await self._load_tenant_context(user_id)
        phone = normalize_phone(sender_phone)

        if tenant.authorized_owners and phone not in tenant.authorized_owners:
            logger.warning(
                "catat ditolak tenant=%s sender=%s bukan authorized owner",
                user_id,
                phone,
            )
            return OrchestratorResult(
                text=UNAUTHORIZED_CATAT,
                agent_id="admin",
                intent="unauthorized",
                data={"channel": "catat", "tenant_user_id": user_id},
            )

        saved, reply = await self.admin_ai_catat_transaksi(user_id, message)
        self._last_agent_id = "admin"
        self._last_intent = "catat" if saved else "catat_empty"
        return OrchestratorResult(
            text=reply,
            agent_id=self._last_agent_id,
            intent=self._last_intent,
            data={"channel": "catat", "tenant_user_id": user_id, "transactions": saved},
        )

    async def admin_ai_catat_transaksi(
        self,
        user_id: str,
        text: str,
    ) -> tuple[list[dict[str, Any]], str]:
        """Ekstrak transaksi via AI lalu simpan ke tenant yang benar (`save_transaction`)."""
        tenant = await self._load_tenant_context(user_id)
        raw = (text or "").strip()
        if not raw:
            return [], "Kirim perintah catat ya, contoh: _jual kopi 50rb_ atau _beli gula 20rb_"

        transactions = await self._extract_transactions(raw, tenant)
        if not transactions:
            return [], (
                f"Belum kebaca sebagai transaksi untuk *{tenant.display_name}*. "
                "Coba format: jual [produk] [nominal] atau beli [item] [nominal]."
            )

        core = get_tenant_core()
        saved: list[dict[str, Any]] = []
        for txn in transactions:
            txn_type = str(txn.get("type") or "Pemasukan")
            amount = int(txn.get("amount") or 0)
            if amount <= 0:
                continue
            category = str(txn.get("category") or "Umum")
            note = str(txn.get("note") or raw)[:200]
            is_prive = bool(txn.get("is_prive", False))
            try:
                await asyncio.to_thread(
                    core.save_transaction,
                    user_id,
                    txn_type,
                    category,
                    amount,
                    note,
                    is_prive,
                )
                saved.append(txn)
                logger.info(
                    "save_transaction tenant=%s type=%s amount=%s",
                    user_id,
                    txn_type,
                    amount,
                )
            except Exception as exc:
                logger.exception("save_transaction gagal tenant=%s: %s", user_id, exc)
                self._stats.errors += 1

        if not saved:
            return [], FALLBACK_ERROR

        lines = [
            f"✅ Tercatat: {t.get('type')} {t.get('category', '')} "
            f"Rp {int(t.get('amount', 0)):,}"
            for t in saved
        ]
        balance = await asyncio.to_thread(core.get_balance, user_id)
        footer = f"\n\nSaldo terkini *{tenant.display_name}*: Rp {int(balance):,}"
        return saved, "\n".join(lines) + footer

    # ------------------------------------------------------------------
    # Tenant helpers
    # ------------------------------------------------------------------

    async def _load_tenant_context(self, user_id: str) -> TenantContext:
        try:
            db = get_supabase_admin()
            return await build_tenant_context(db, user_id)
        except Exception as exc:
            logger.warning("load tenant context gagal user=%s: %s", user_id, exc)
            return TenantContext(user_id=str(user_id).strip())

    @staticmethod
    def _client_config_from_tenant(tenant: TenantContext) -> ClientConfig:
        owners = list(tenant.authorized_owners)
        return ClientConfig(
            client_id=tenant.user_id,
            name=tenant.display_name,
            owner_phones=owners,
            products=tenant.products,
            payment_methods=[],
            profile_key="ramah_warm",
        )

    def _cs_system_prompt(self, tenant: TenantContext) -> str:
        catalog = format_products_for_prompt(tenant.products)
        return (
            f"Kamu adalah CS WhatsApp untuk bisnis bernama *{tenant.display_name}*.\n"
            "Tugas: sapaan, info umum, bantu pelanggan tanya harga & produk.\n"
            "Jawab singkat, hangat, Bahasa Indonesia, maksimal 3 kalimat.\n"
            "HANYA sebut produk/harga dari katalog di bawah — jangan mengarang promo atau produk.\n\n"
            f"Katalog produk:\n{catalog}"
        )

    async def _extract_transactions(self, text: str, tenant: TenantContext) -> list[dict[str, Any]]:
        """Ekstrak transaksi — Groq via laris_core, fallback OpenRouter."""
        core = get_tenant_core()
        try:
            rows = await asyncio.to_thread(core.ai_extractor_agent, text)
            if rows:
                return rows
        except Exception as exc:
            logger.warning("ai_extractor_agent gagal tenant=%s: %s", tenant.user_id, exc)

        prompt = (
            f'Anda akuntan untuk bisnis "{tenant.display_name}". Teks owner: "{text}"\n\n'
            "Ekstrak HANYA jika user mencatat transaksi jual/beli dengan nominal.\n"
            'Balas JSON: {"transactions":[{"type":"Pemasukan|Pengeluaran","amount":angka,'
            '"category":"...","note":"..."}]}'
        )
        system = (
            f"Kamu asisten pencatat keuangan untuk {tenant.display_name}. "
            f"Produk di katalog:\n{format_products_for_prompt(tenant.products)}"
        )
        try:
            raw = await self._llm.chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=400,
            )
            return core._parse_transactions(raw)
        except Exception as exc:
            logger.error("extract transactions OpenRouter tenant=%s: %s", tenant.user_id, exc)
            return []

    # ------------------------------------------------------------------
    # Core pipeline (legacy + tenant-aware)
    # ------------------------------------------------------------------

    async def handle_message(
        self,
        user_id: str,
        message: str,
        client_id: str,
        *,
        client_config: ClientConfig | None = None,
        tenant: TenantContext | None = None,
    ) -> str:
        """Pipeline lengkap — `user_id` di sini = nomor WA pengirim (pelanggan/owner)."""
        t0 = time.perf_counter()
        text = (message or "").strip()
        agent_id = "cs"
        tenant_user_id = tenant.user_id if tenant else client_id
        mem_key = f"{tenant_user_id}:{normalize_phone(user_id)}"

        if tenant and not client_config:
            client_config = self._client_config_from_tenant(tenant)

        owners = list(client_config.owner_phone_set) if client_config else []
        is_owner = (
            normalize_phone(user_id) in client_config.owner_phone_set
            if client_config
            else False
        )

        if client_config:
            self._personality.set_local_brand(
                client_id,
                {"profile_key": client_config.profile_key, "client_id": client_id},
            )

        try:
            user_lang = await self._personality.detect_language(text)

            if self._is_angry(text):
                self._stats.escalations += 1
                self._clarify_counts.pop(mem_key, None)
                final = await self._personality.adapt_tone(
                    ESCALATE_PROMPT,
                    await self._personality.get_personality(client_id),
                    user_lang=user_lang,
                )
                await self._save_interaction(mem_key, text, final, "support", "escalate")
                self._last_agent_id = "support"
                self._last_intent = "escalate"
                self._record_stats("support", t0)
                return final

            otak_ctx = await self._otak.bangun_context(mem_key, text)
            if tenant:
                otak_ctx = (
                    f"Bisnis: {tenant.display_name}\n"
                    f"{format_products_for_prompt(tenant.products)}\n\n{otak_ctx}"
                )

            route = await self._router.route(text, context=otak_ctx)

            if route.confidence < CLARIFY_THRESHOLD:
                count = self._clarify_counts.get(mem_key, 0) + 1
                self._clarify_counts[mem_key] = count
                self._stats.clarifications += 1
                if count <= MAX_CLARIFY_ATTEMPTS:
                    personality = await self._personality.get_personality(client_id)
                    final = await self._personality.adapt_tone(
                        CLARIFY_PROMPT, personality, user_lang=user_lang
                    )
                    await self._save_interaction(mem_key, text, final, "cs", "clarify")
                    self._last_agent_id = "cs"
                    self._last_intent = "clarify"
                    self._record_stats("cs", t0)
                    return final
                self._clarify_counts.pop(mem_key, None)
                route = RouteResult("cs", "clarify_fallback", 0.5, "max clarify → cs")
            else:
                self._clarify_counts.pop(mem_key, None)

            personality = await self._personality.get_personality(client_id)
            agent = self._resolve_agent(route)
            agent_id = agent.agent_id

            meta: dict[str, Any] = {
                "intent": route.intent,
                "route": route.reason,
                "confidence": route.confidence,
                "is_owner": is_owner,
                "owners": owners,
                "tenant_user_id": tenant_user_id,
            }
            if tenant:
                meta["business_name"] = tenant.display_name
                meta["products"] = tenant.products
                meta["cs_system_prompt"] = self._cs_system_prompt(tenant)
            elif client_config:
                if client_config.products:
                    meta["products"] = client_config.products
                if client_config.payment_methods:
                    meta["payment_methods"] = client_config.payment_methods

            ctx = AgentContext(
                client_id=client_id,
                user_id=user_id,
                message=text,
                otak_context=otak_ctx,
                personality=personality,
                user_lang=user_lang,
                metadata=meta,
            )

            raw = await self._safe_process(agent, ctx, tenant=tenant)

            final = await self._personality.adapt_tone(raw, personality, user_lang=user_lang)
            await self._save_interaction(mem_key, text, final, agent_id, route.intent)

            self._last_agent_id = agent_id
            self._last_intent = route.intent
            self._record_stats(agent_id, t0)
            logger.info(
                "handle_message tenant=%s sender=%s agent=%s intent=%s conf=%.2f ms=%.0f",
                tenant_user_id,
                user_id,
                agent_id,
                route.intent,
                route.confidence,
                (time.perf_counter() - t0) * 1000,
            )
            return final

        except Exception as exc:
            self._stats.errors += 1
            logger.exception(
                "handle_message error tenant=%s sender=%s: %s",
                tenant_user_id,
                user_id,
                exc,
            )
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
            await self._save_interaction(mem_key, text, final, "cs", "error")
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
        client_config: ClientConfig | None = None,
        tenant_user_id: str | None = None,
    ) -> OrchestratorResult:
        """Adapter kompatibel dengan API webhook lama."""
        tenant = None
        tid = tenant_user_id or client_id
        if tid:
            tenant = await self._load_tenant_context(tid)
        text = await self.handle_message(
            user_id,
            message,
            client_id,
            client_config=client_config,
            tenant=tenant,
        )
        return OrchestratorResult(
            text=text,
            agent_id=self._last_agent_id,
            intent=self._last_intent,
            data={"route_confidence": 0.0, "tenant_user_id": tid},
        )

    def _resolve_agent(self, route: RouteResult) -> BaseAgent:
        agent = self._agents.get(route.agent)
        if agent and agent.can_handle(route.intent):
            return agent
        resolved = BaseAgent.resolve_conflict(list(self._agents.values()), route.intent)
        return resolved or self._cs_agent

    async def _safe_process(
        self,
        agent: BaseAgent,
        ctx: AgentContext,
        *,
        tenant: TenantContext | None = None,
    ) -> str:
        try:
            if agent.agent_id == "cs" and tenant:
                system = ctx.metadata.get("cs_system_prompt") or self._cs_system_prompt(tenant)
                reply = await agent._call_llm(ctx.message, system)
                if agent._validate_response(reply):
                    return reply

            raw = await agent.process(ctx.message, ctx, ctx.personality)
            if agent._validate_response(raw):
                return raw
            logger.warning("invalid response dari %s — fallback CS", agent.agent_id)
        except Exception as exc:
            logger.exception("agent %s error: %s", agent.agent_id, exc)
            self._stats.errors += 1

        try:
            if tenant:
                system = self._cs_system_prompt(tenant)
                reply = await self._cs_agent._call_llm(ctx.message, system)
                if self._cs_agent._validate_response(reply):
                    return reply
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
                    "content": (
                        f"User: {user_msg[:200]} | Agent({agent_id}/{intent}): {response[:300]}"
                    ),
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
    """Hasil handle untuk kompatibilitas webhook."""

    text: str
    agent_id: str
    intent: str = ""
    data: dict[str, Any] = field(default_factory=dict)


AgentOrchestrator = Orchestrator
