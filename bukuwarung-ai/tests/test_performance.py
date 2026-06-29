"""Performance tests — response time & token budget."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents import build_agents
from core.personality import PersonalityEngine
from core.semantic_router import SemanticRouter
from orchestrator import Orchestrator
from utils.openrouter import TokenUsage

MAX_RESPONSE_SEC = 5.0
MAX_TOKENS_PER_MESSAGE_MOCK = 0  # mock LLM = 0 tokens; live tests documented separately

PERF_MESSAGES = [
    "halo",
    "harga kopi berapa?",
    "pesan indomie 3",
    "mau bayar transfer",
    "komplain barang rusak",
    "laporan omzet",
    "Sugeng enjang arep pesen kopi",
    "Kumaha damang hoyong mesen",
]


class _OfflineDB:
    def table(self, name: str):
        raise ConnectionError("offline")


@pytest.fixture
def perf_stack():
    otak = MagicMock()
    otak.bangun_context = AsyncMock(return_value="")
    otak.simpan_memory = AsyncMock()
    personality = PersonalityEngine(_OfflineDB())
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="")
    llm.complete = AsyncMock(return_value='{"agent":"cs","confidence":0.8,"reason":"x"}')
    llm.last_usage = TokenUsage()
    llm.session_usage = TokenUsage()
    router = SemanticRouter(llm)
    agents = build_agents(otak, personality, llm)
    return Orchestrator(otak, router, personality, agents), llm


@pytest.mark.asyncio
@pytest.mark.parametrize("message", PERF_MESSAGES)
async def test_response_time_under_5_seconds(perf_stack, message: str) -> None:
    orch, _ = perf_stack
    t0 = time.perf_counter()
    reply = await orch.handle_message("62811", message, "toko_perf")
    elapsed = time.perf_counter() - t0
    assert reply.strip()
    assert elapsed < MAX_RESPONSE_SEC, f"{message!r} took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_batch_average_response_time(perf_stack) -> None:
    orch, _ = perf_stack
    times: list[float] = []
    for msg in PERF_MESSAGES:
        t0 = time.perf_counter()
        await orch.handle_message("62811", msg, "toko_perf")
        times.append(time.perf_counter() - t0)
    avg = sum(times) / len(times)
    assert avg < 2.0, f"Average {avg:.2f}s exceeds 2s target for mock stack"
    assert orch.stats.avg_response_ms < 2000


@pytest.mark.asyncio
async def test_token_usage_tracking_mock(perf_stack) -> None:
    """Dengan mock LLM, token usage = 0 (rule-based path)."""
    orch, llm = perf_stack
    await orch.handle_message("62811", "halo", "toko1")
    assert llm.session_usage.total_tokens == MAX_TOKENS_PER_MESSAGE_MOCK


def test_token_usage_dataclass() -> None:
    total = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    acc = TokenUsage()
    acc.add(total)
    assert acc.total_tokens == 30
