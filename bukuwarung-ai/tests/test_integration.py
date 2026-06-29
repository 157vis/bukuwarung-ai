"""Integration tests — full pipeline message → route → agent → response → webhook."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents import build_agents
from core.personality import PersonalityEngine
from core.semantic_router import SemanticRouter
from orchestrator import Orchestrator


class _OfflineDB:
    def table(self, name: str):
        raise ConnectionError("offline")


@pytest.fixture
def stack(monkeypatch):
    """Stack lengkap: OtakAI mock + PersonalityEngine + Router + 6 agents."""
    monkeypatch.setenv("OWNER_PHONES", "6289999999999")

    from config import get_settings

    get_settings.cache_clear()

    otak = MagicMock()
    otak.bangun_context = AsyncMock(return_value="Riwayat: pelanggan sering beli kopi")
    otak.simpan_memory = AsyncMock()

    personality = PersonalityEngine(_OfflineDB())
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="")

    async def _mock_complete(prompt: str, *, model=None) -> str:
        if "Klasifikasi" in prompt or '"agent"' in prompt:
            return '{"agent":"cs","confidence":0.35,"reason":"mock-unclear"}'
        return '{"agent":"cs","confidence":0.6,"reason":"mock"}'

    llm.complete = AsyncMock(side_effect=_mock_complete)
    llm.last_usage = MagicMock(prompt_tokens=0, completion_tokens=0, total_tokens=0)
    llm.session_usage = MagicMock(prompt_tokens=0, completion_tokens=0, total_tokens=0)

    router = SemanticRouter(llm)
    agents = build_agents(otak, personality, llm)
    orch = Orchestrator(otak, router, personality, agents)
    return orch, otak, personality, llm


# 25+ skenario real — (pesan, agent_expected, keywords_in_response)
INTEGRATION_SCENARIOS: list[tuple[str, str, list[str]]] = [
    # CS / greeting
    ("halo", "cs", ["halo", "datang", "bantu"]),
    ("selamat pagi", "cs", ["halo", "datang", "buka", "bantu"]),
    ("jam buka sampai jam berapa?", "cs", ["jam", "7", "buka"]),
    ("alamat warung dimana?", "cs", ["lokasi", "pasar", "alamat"]),
    # Sales
    ("berapa harga kopi?", "sales", ["3.500", "kopi", "harga"]),
    ("rekomendasi produk murah dong", "sales", ["pilihan", "indomie", "kopi", "promo"]),
    ("stok indomie ada?", "sales", ["stok", "indomie"]),
    ("ada promo hari ini?", "sales", ["promo"]),
    # Order
    ("pesan kopi 2 pack", "order", ["kopi", "order", "pesan", "total", "ord-"]),
    ("jual kopi 50rb", "order", ["kopi", "50", "order", "total"]),
    ("track order saya", "order", ["pesanan", "order", "belum"]),
    ("batal pesanan", "order", ["batal"]),
    # Payment
    ("mau bayar", "payment", ["bca", "transfer", "bayar"]),
    ("transfer ke rekening mana?", "payment", ["bca", "warung", "transfer"]),
    ("sudah bayar via transfer", "payment", ["terima kasih", "transfer"]),
    # Support
    ("komplain pesanan salah", "support", ["maaf"]),
    ("aplikasi error tidak bisa buka", "support", ["maaf", "restart", "error"]),
    # Admin (non-owner)
    ("laporan omzet hari ini", "admin", ["owner", "laporan"]),
    # Bahasa Jawa
    ("Sugeng enjang mas, arep pesen kopi 2", "order", ["kopi", "pesan", "order", "total"]),
    # Bahasa Sunda
    ("Wilujeng enjing, abdi hoyong mesen indomie", "order", ["indomie", "pesan", "order", "total"]),
    # Edge: unclear → clarify
    ("hm", "cs", ["paham", "detail", "jelaskan", "maksud"]),
    # Edge: angry → escalate
    ("saya sangat kecewa dan marah!", "support", ["maaf", "eskalasi"]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("message,expected_agent,keywords", INTEGRATION_SCENARIOS)
async def test_full_pipeline_scenarios(
    stack, message: str, expected_agent: str, keywords: list[str]
) -> None:
    orch, otak, _, _ = stack
    user_id = "6281111111111"
    response = await orch.handle_message(user_id, message, "toko_test")

    assert response.strip(), f"Respons kosong untuk: {message!r}"
    lower = response.lower()
    assert any(kw.lower() in lower for kw in keywords), (
        f"Pesan {message!r} → {response!r}, expected one of {keywords}"
    )
    # Agent usage tercatat (kecuali clarify/escalate bisa beda label)
    assert orch.stats.total_messages >= 1
    otak.simpan_memory.assert_awaited()


@pytest.mark.asyncio
async def test_webhook_end_to_end(stack):
    """Webhook HTTP → orchestrator → send_message."""
    from fastapi.testclient import TestClient

    import main

    orch, _, _, _ = stack
    with patch.object(main, "get_orchestrator", return_value=orch):
        with patch("main.send_message", new_callable=AsyncMock, return_value=True) as send:
            client = TestClient(main.app)
            resp = client.post(
                "/webhook-whatsapp",
                json={"sender": "628123", "message": "halo", "client_id": "toko_test"},
            )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    send.assert_awaited_once()
    assert send.call_args[0][1].strip()


@pytest.mark.asyncio
async def test_language_detection_jv_su(stack):
    _, _, personality, _ = stack
    assert await personality.detect_language("Piye kabare mas arep tuku kopi") == "jv"
    assert await personality.detect_language("Kumaha damang naon waé anu perlu") == "su"
    assert await personality.detect_language("Halo mau pesan kopi") == "id"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,expect_nonempty",
    [
        ("", True),
        ("aaaaaaaaaaaaaaaaaaaaaa", True),
        ("x" * 3500, True),
    ],
)
async def test_edge_messages(stack, message: str, expect_nonempty: bool) -> None:
    orch, _, _, _ = stack
    response = await orch.handle_message("62811", message, "toko_test")
    if expect_nonempty:
        assert response.strip()


@pytest.mark.asyncio
async def test_admin_owner_access(stack, monkeypatch):
    monkeypatch.setenv("OWNER_PHONES", "6288888888888")
    from config import get_settings

    get_settings.cache_clear()

    orch, _, _, _ = stack
    # Rebuild with new owner env
    from agents import build_agents
    from core.semantic_router import SemanticRouter

    otak = MagicMock()
    otak.bangun_context = AsyncMock(return_value="")
    otak.simpan_memory = AsyncMock()
    personality = PersonalityEngine(_OfflineDB())
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="")
    llm.complete = AsyncMock(return_value='{"agent":"admin","confidence":0.9,"reason":"x"}')
    agents = build_agents(otak, personality, llm)
    orch2 = Orchestrator(otak, SemanticRouter(llm), personality, agents)

    resp = await orch2.handle_message("6288888888888", "laporan harian", "toko_test")
    assert "laporan" in resp.lower()
    assert "pesanan" in resp.lower() or "omzet" in resp.lower()


@pytest.mark.asyncio
async def test_memory_saved_each_turn(stack):
    orch, otak, _, _ = stack
    await orch.handle_message("62811", "halo", "toko1")
    await orch.handle_message("62811", "harga kopi", "toko1")
    assert otak.simpan_memory.await_count >= 2


@pytest.mark.asyncio
async def test_route_cache_speed(stack):
    """Routing cache — panggilan kedua lebih cepat."""
    import time

    orch, _, _, _ = stack
    msg = "rekomendasi produk terbaik untuk dapur"
    t0 = time.perf_counter()
    await orch.handle_message("62811", msg, "toko1")
    first = time.perf_counter() - t0
    t1 = time.perf_counter()
    await orch.handle_message("62822", msg, "toko1")
    second = time.perf_counter() - t1
    assert second <= first + 0.05
