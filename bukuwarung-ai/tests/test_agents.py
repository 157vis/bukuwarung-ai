"""Tests 6 specialist agents — 5 kasus per agent, mock DB & LLM."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agents import build_agents
from agents.admin_agent import AdminAgent
from agents.base_agent import AgentContext
from agents.cs_agent import CSAgent
from agents.data_access import OrderStore
from agents.order_agent import OrderAgent
from agents.payment_agent import PaymentAgent
from agents.sales_agent import SalesAgent
from agents.support_agent import SupportAgent


@pytest.fixture
def deps():
    otak = MagicMock()
    otak.simpan_memory = AsyncMock()
    personality = MagicMock()
    personality.adapt_tone = AsyncMock(side_effect=lambda t, p, **kw: t)
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="")
    return otak, personality, llm


@pytest.fixture
def agents(deps):
    return build_agents(*deps)


def _ctx(
    message: str,
    *,
    intent: str,
    is_owner: bool = False,
) -> AgentContext:
    return AgentContext(
        client_id="toko_test",
        user_id="62811",
        message=message,
        otak_context="",
        personality={"profile_key": "ramah_warm"},
        user_lang="id",
        metadata={"intent": intent, "is_owner": is_owner},
    )


# ---------------------------------------------------------------------------
# CSAgent — 5 kasus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,expect",
    [
        ("halo", "Selamat datang"),
        ("jam buka sampai jam berapa?", "7 pagi"),
        ("alamat warung dimana?", "Jl. Pasar"),
        ("berapa harga kopi?", "sales"),
        ("mau transfer", "pembayaran"),
    ],
)
async def test_cs_agent(agents, message: str, expect: str) -> None:
    resp = await agents["cs"].handle(_ctx(message, intent="cs"))
    assert expect.lower() in resp.text.lower()


def test_cs_capabilities(deps) -> None:
    agent = CSAgent(*deps)
    assert agent.get_capabilities() == ["sapaan", "info_umum", "jam_operasional", "lokasi"]
    assert agent.can_handle("greeting")


# ---------------------------------------------------------------------------
# SalesAgent — 5 kasus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,expect",
    [
        ("rekomendasi produk murah", "pilihan"),
        ("harga kopi berapa?", "3.500"),
        ("stok indomie ada?", "stok"),
        ("ada promo?", "promo"),
        ("info gula", "15.000"),
    ],
)
async def test_sales_agent(agents, message: str, expect: str) -> None:
    resp = await agents["sales"].handle(_ctx(message, intent="sales"))
    assert expect.lower() in resp.text.lower()


def test_sales_capabilities(deps) -> None:
    agent = SalesAgent(*deps)
    assert "rekomendasi_produk" in agent.get_capabilities()


# ---------------------------------------------------------------------------
# OrderAgent — 5 kasus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,check",
    [
        ("pesan kopi 2", lambda r: "order" in r.text.lower() or "kopi" in r.text.lower()),
        ("jual kopi 50rb", lambda r: r.data.get("amount") == 50000),
        ("track order", lambda r: "pesanan" in r.text.lower()),
        ("batal pesanan", lambda r: "batal" in r.text.lower()),
        ("pesan", lambda r: "sebut" in r.text.lower() or "produk" in r.text.lower()),
    ],
)
async def test_order_agent(agents, message: str, check) -> None:
    resp = await agents["order"].handle(_ctx(message, intent="order"))
    assert check(resp)


@pytest.mark.asyncio
async def test_order_store_create(deps) -> None:
    store = OrderStore()
    agent = OrderAgent(*deps, store)
    ctx = _ctx("pesan indomie 3", intent="order")
    resp = await agent.handle(ctx)
    assert resp.data.get("order_id", "").startswith("ORD-")


# ---------------------------------------------------------------------------
# PaymentAgent — 5 kasus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,expect",
    [
        ("mau bayar", "BCA"),
        ("transfer ke mana?", "Warung Berkah"),
        ("sudah bayar 78000", "terima kasih"),
        ("cek status pembayaran", "status"),
        ("bayar pakai gopay", "GoPay"),
    ],
)
async def test_payment_agent(agents, message: str, expect: str) -> None:
    resp = await agents["payment"].handle(_ctx(message, intent="payment"))
    assert expect.lower() in resp.text.lower()


# ---------------------------------------------------------------------------
# SupportAgent — 5 kasus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,expect",
    [
        ("komplain pesanan salah", "maaf"),
        ("aplikasi error", "restart"),
        ("saya kecewa", "maaf"),
        ("tolong bantu", "terkait"),
        ("ini penipuan!", "eskalasi"),
    ],
)
async def test_support_agent(agents, message: str, expect: str) -> None:
    resp = await agents["support"].handle(_ctx(message, intent="support"))
    assert expect.lower() in resp.text.lower()


def test_support_escalate(deps) -> None:
    agent = SupportAgent(*deps)
    assert agent.can_handle("komplain")


# ---------------------------------------------------------------------------
# AdminAgent — 5 kasus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message,is_owner,expect",
    [
        ("laporan harian", True, "laporan"),
        ("statistik omzet", True, "omzet"),
        ("best seller", True, "seller"),
        ("laporan harian", False, "owner"),
        ("contoh laporan", True, "laporan"),
    ],
)
async def test_admin_agent(agents, message: str, is_owner: bool, expect: str) -> None:
    resp = await agents["admin"].handle(_ctx(message, intent="admin", is_owner=is_owner))
    assert expect.lower() in resp.text.lower()


@pytest.mark.asyncio
async def test_admin_with_orders(deps) -> None:
    store = OrderStore()
    await store.create_order("owner1", [{"name": "kopi", "qty": 2, "price": 3500}], 7000)
    agent = AdminAgent(*deps, store)
    ctx = _ctx("laporan harian", intent="admin", is_owner=True)
    ctx.user_id = "owner1"
    resp = await agent.handle(ctx)
    assert "1" in resp.text or "pesanan" in resp.text.lower()
