"""Semantic intent router — arahkan pesan ke agent yang tepat."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Literal

from utils.openrouter import OpenRouterClient

logger = logging.getLogger(__name__)

AgentName = Literal["cs", "sales", "order", "payment", "support", "admin", "greeting"]

INTENT_RULES: list[tuple[AgentName, list[str]]] = [
    ("greeting", ["halo", "hai", "hi", "pagi", "siang", "malam", "test", "ping"]),
    ("order", ["pesan", "order", "beli", "jual", "mau ambil", "catat", "pesen", "mesen"]),
    ("payment", ["bayar", "transfer", "qris", "pembayaran", "lunas", "tagihan", "invoice"]),
    ("sales", ["rekomendasi", "saran", "promo", "diskon", "produk apa", "best seller", "murah", "stok", "harga"]),
    ("support", ["error", "gagal", "tidak bisa", "bantuan teknis", "bug", "masalah app", "komplain", "kecewa"]),
    ("admin", ["laporan", "rekap", "omzet", "admin", "dashboard", "summary", "piutang"]),
    ("cs", ["jam buka", "lokasi", "alamat", "kirim ke", "ongkir", "tanya", "info"]),
]


@dataclass
class RouteResult:
    """Hasil routing."""

    agent: AgentName
    intent: str
    confidence: float
    reason: str


class SemanticRouter:
    """Router intent: rules cepat → LLM fallback."""

    _CACHE_MAX = 256

    def __init__(self, llm: OpenRouterClient | None = None) -> None:
        self._llm = llm or OpenRouterClient()
        self._route_cache: dict[str, RouteResult] = {}

    async def route(self, message: str, *, context: str = "") -> RouteResult:
        """Tentukan agent terbaik untuk pesan user.

        Args:
            message: Pesan masuk.
            context: Context dari OtakAI (opsional).

        Returns:
            RouteResult dengan agent, intent, confidence.
        """
        text = (message or "").strip()
        if not text:
            return RouteResult("cs", "empty", 0.5, "pesan kosong")

        cache_key = text.lower()[:200]
        if cache_key in self._route_cache:
            cached = self._route_cache[cache_key]
            logger.debug("route cache hit → %s", cached.agent)
            return cached

        ruled = self._rule_route(text)
        if ruled and ruled.confidence >= 0.70:
            logger.info("route rule → %s (%.2f)", ruled.agent, ruled.confidence)
            self._store_cache(cache_key, ruled)
            return ruled

        llm_result = await self._llm_route(text, context)
        if llm_result and (not ruled or llm_result.confidence > ruled.confidence):
            logger.info("route llm → %s (%.2f)", llm_result.agent, llm_result.confidence)
            self._store_cache(cache_key, llm_result)
            return llm_result

        result = ruled or RouteResult("cs", "default", 0.4, "fallback cs")
        self._store_cache(cache_key, result)
        return result

    def _store_cache(self, key: str, result: RouteResult) -> None:
        if len(self._route_cache) >= self._CACHE_MAX:
            self._route_cache.pop(next(iter(self._route_cache)))
        self._route_cache[key] = result

    def _rule_route(self, text: str) -> RouteResult | None:
        lower = text.lower()
        best: RouteResult | None = None

        for agent, keywords in INTENT_RULES:
            hits = sum(1 for kw in keywords if kw in lower)
            if hits == 0:
                continue
            conf = min(0.95, 0.60 + hits * 0.15)
            candidate = RouteResult(agent, agent, conf, f"keyword x{hits}")
            if not best or candidate.confidence > best.confidence:
                best = candidate

        if re.search(r"\bkomplain\b", lower):
            return RouteResult("support", "support", 0.92, "komplain eksplisit")

        if re.search(r"\b(pesan|pesen|mesen|order|beli|jual)\b", lower) and re.search(r"\d", lower):
            return RouteResult("order", "order", 0.9, "order + angka")

        return best

    async def _llm_route(self, text: str, context: str) -> RouteResult | None:
        prompt = (
            "Klasifikasi pesan WhatsApp UMKM. Balas HANYA JSON:\n"
            '{"agent":"cs|sales|order|payment|support|admin|greeting","confidence":0.0-1.0,"reason":"..."}\n\n'
            f"Context:\n{context[:500]}\n\nPesan: {text[:400]}"
        )
        try:
            raw = await self._llm.complete(prompt, model=None)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```\w*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            agent = str(data.get("agent", "cs")).lower()
            if agent not in ("cs", "sales", "order", "payment", "support", "admin", "greeting"):
                agent = "cs"
            return RouteResult(
                agent,  # type: ignore[arg-type]
                agent,
                float(data.get("confidence") or 0.7),
                str(data.get("reason") or "llm"),
            )
        except (json.JSONDecodeError, ValueError, RuntimeError, KeyError) as exc:
            logger.warning("llm route gagal: %s", exc)
            return None
