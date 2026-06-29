"""Unit tests Orchestrator — pipeline, edge cases, stats."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents.base_agent import AgentContext, BaseAgent
from core.semantic_router import RouteResult
from orchestrator import Orchestrator, CLARIFY_THRESHOLD


class DummyAgent(BaseAgent):
    agent_id = "dummy"
    name = "Dummy"
    capabilities = ["test"]
    priority = 50

    def __init__(self, otak, personality, llm, *, reply: str = "jawaban dummy", fail: bool = False):
        super().__init__(otak, personality, llm)
        self._reply = reply
        self._fail = fail

    async def process(self, message: str, context: AgentContext, personality: dict[str, Any]) -> str:
        if self._fail:
            raise RuntimeError("boom")
        return self._reply

    def get_name(self) -> str:
        return self.name

    def get_capabilities(self) -> list[str]:
        return list(self.capabilities)

    def can_handle(self, intent: str) -> bool:
        return intent in ("dummy", "sales", "order", "payment", "support", "admin", "cs", "greeting")


class CSAgentStub(DummyAgent):
    agent_id = "cs"
    name = "CS"

    def can_handle(self, intent: str) -> bool:
        return True


@pytest.fixture
def deps():
    otak = MagicMock()
    otak.bangun_context = AsyncMock(return_value="ctx")
    otak.simpan_memory = AsyncMock()
    personality = MagicMock()
    personality.detect_language = AsyncMock(return_value="id")
    personality.get_personality = AsyncMock(return_value={"profile_key": "ramah_warm"})
    personality.adapt_tone = AsyncMock(side_effect=lambda t, p, **kw: f"[tone]{t}")
    llm = MagicMock()
    return otak, personality, llm


@pytest.fixture
def router():
    r = MagicMock()
    r.route = AsyncMock(return_value=RouteResult("sales", "sales", 0.9, "test"))
    return r


class SalesAgentStub(DummyAgent):
    agent_id = "sales"
    name = "Sales"


@pytest.fixture
def orch(deps, router):
    otak, personality, llm = deps
    agents = {
        "cs": CSAgentStub(otak, personality, llm, reply="balasan cs"),
        "sales": SalesAgentStub(otak, personality, llm, reply="balasan sales"),
    }
    return Orchestrator(otak, router, personality, agents)


@pytest.mark.asyncio
async def test_handle_message_happy_path(orch, deps):
    text = await orch.handle_message("62811", "harga kopi", "toko1")
    assert "balasan sales" in text
    assert orch.stats.total_messages == 1
    assert orch.stats.agent_usage.get("sales") == 1
    deps[0].simpan_memory.assert_awaited()


@pytest.mark.asyncio
async def test_angry_escalation(orch, router):
    router.route = AsyncMock()  # tidak dipanggil jika marah
    text = await orch.handle_message("62811", "saya sangat marah!", "toko1")
    assert "eskalasi" in text.lower()
    assert orch.stats.escalations == 1
    router.route.assert_not_awaited()


@pytest.mark.asyncio
async def test_clarify_then_fallback(deps, router):
    otak, personality, llm = deps
    router.route = AsyncMock(
        return_value=RouteResult("cs", "unclear", CLARIFY_THRESHOLD - 0.1, "low conf")
    )
    agents = {"cs": CSAgentStub(otak, personality, llm)}
    orch = Orchestrator(otak, router, personality, agents)

    t1 = await orch.handle_message("u1", "hm", "toko1")
    assert "kurang paham" in t1.lower()
    t2 = await orch.handle_message("u1", "hm lagi", "toko1")
    assert "kurang paham" in t2.lower()
    t3 = await orch.handle_message("u1", "hm lagi lagi", "toko1")
    assert orch.stats.clarifications >= 2


@pytest.mark.asyncio
async def test_agent_error_fallback_cs(deps, router):
    otak, personality, llm = deps
    agents = {
        "cs": CSAgentStub(otak, personality, llm, reply="cs fallback ok"),
        "sales": SalesAgentStub(otak, personality, llm, fail=True),
    }
    router.route = AsyncMock(return_value=RouteResult("sales", "sales", 0.9, "test"))
    orch = Orchestrator(otak, router, personality, agents)
    text = await orch.handle_message("62811", "promo", "toko1")
    assert "cs fallback" in text
    assert orch.stats.errors >= 1


@pytest.mark.asyncio
async def test_process_compat(orch):
    result = await orch.process(client_id="toko1", user_id="62811", message="halo")
    assert result.text
    assert result.agent_id
