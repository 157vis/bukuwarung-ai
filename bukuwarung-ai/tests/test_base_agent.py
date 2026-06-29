"""Unit tests untuk BaseAgent (menggunakan concrete stub)."""

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


class StubAgent(BaseAgent):
    agent_id = "stub"
    name = "Stub Agent"
    description = "For testing"
    capabilities = ["test"]
    priority = 80

    def __init__(self, otak, personality, llm, *, reply: str = "Halo dari stub") -> None:
        super().__init__(otak, personality, llm)
        self._reply = reply

    async def process(self, message: str, context: AgentContext, personality: dict[str, Any]) -> str:
        return f"{self._reply}: {message}"

    def get_name(self) -> str:
        return self.name

    def get_capabilities(self) -> list[str]:
        return list(self.capabilities)

    def can_handle(self, intent: str) -> bool:
        return intent in ("stub", "cs", "greeting")


@pytest.fixture
def deps():
    otak = MagicMock()
    otak.simpan_memory = AsyncMock()
    personality = MagicMock()
    personality.adapt_tone = AsyncMock(side_effect=lambda t, p, **kw: f"[tone]{t}")
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="LLM jawaban")
    return otak, personality, llm


@pytest.fixture
def ctx() -> AgentContext:
    return AgentContext(
        client_id="toko1",
        user_id="62811",
        message="halo",
        personality={"profile_key": "ramah_warm"},
        user_lang="id",
        metadata={"intent": "stub"},
    )


@pytest.mark.asyncio
async def test_process_and_handle(deps, ctx: AgentContext) -> None:
    otak, personality, llm = deps
    agent = StubAgent(otak, personality, llm)
    resp = await agent.handle(ctx)
    assert "Halo dari stub" in resp.text
    assert resp.agent_id == "stub"
    otak.simpan_memory.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_llm(deps) -> None:
    otak, personality, llm = deps
    agent = StubAgent(otak, personality, llm)
    out = await agent._call_llm("user msg", "system msg")
    assert out == "LLM jawaban"
    llm.chat.assert_awaited_once()


def test_validate_response(deps) -> None:
    agent = StubAgent(*deps)
    assert agent._validate_response("Jawaban valid")
    assert not agent._validate_response("")
    assert not agent._validate_response("x" * 5000)
    assert not agent._validate_response("jangan sebut password di sini")


def test_resolve_conflict(deps) -> None:
    a = StubAgent(*deps, reply="a")
    b = StubAgent(*deps, reply="b")
    b.priority = 90
    chosen = BaseAgent.resolve_conflict([a, b], "stub")
    assert chosen is b


@pytest.mark.asyncio
async def test_can_handle_skip(deps, ctx: AgentContext) -> None:
    agent = StubAgent(*deps)
    ctx.metadata["intent"] = "payment"
    resp = await agent.handle(ctx)
    assert resp.data.get("skipped") is True
    assert resp.text == ""
