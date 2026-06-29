"""Tests semantic router."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.semantic_router import SemanticRouter


class MockLLM:
    async def complete(self, prompt: str, *, model=None) -> str:
        return '{"agent":"cs","confidence":0.8,"reason":"mock"}'


@pytest.fixture
def router() -> SemanticRouter:
    return SemanticRouter(MockLLM())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,expected",
    [
        ("halo min", "greeting"),
        ("mau pesan kopi 2", "order"),
        ("sudah transfer 50000", "payment"),
        ("ada promo apa", "sales"),
        ("app error tidak bisa login", "support"),
        ("laporan omzet hari ini", "admin"),
        ("jam buka sampai jam berapa", "cs"),
    ],
)
async def test_rule_routing(router: SemanticRouter, message: str, expected: str) -> None:
    result = await router.route(message)
    assert result.agent == expected, f"{message!r} → {result.agent}, want {expected}"


@pytest.mark.asyncio
async def test_jual_beli_with_number(router: SemanticRouter) -> None:
    result = await router.route("jual kopi 35000")
    assert result.agent == "order"
    assert result.confidence >= 0.85
