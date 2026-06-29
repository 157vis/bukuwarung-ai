"""Unit tests untuk OtakAI."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.otak_ai import OtakAI, STATUS_ACTIVE, STATUS_DELETED, STATUS_REVIEW


class MockEmbed:
    """Embedding deterministik untuk test."""

    async def embed(self, text: str) -> list[float]:
        base = float(len(text) % 10) / 10.0 or 0.1
        return [base + i * 0.01 for i in range(8)]


class FailingDB:
    """Supabase mock yang selalu gagal → trigger fallback lokal."""

    def table(self, name: str) -> Any:
        raise ConnectionError("supabase down")


class RLSBlockedDB:
    """Simulasi error RLS Supabase saat insert."""

    def table(self, name: str) -> Any:
        chain = MagicMock()
        chain.insert.return_value.execute.side_effect = Exception(
            "new row violates row-level security policy for table otak_memories"
        )
        chain.select.return_value.eq.return_value.neq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        return chain


@pytest.fixture
def otak_local() -> OtakAI:
    return OtakAI(FailingDB(), MockEmbed())


@pytest.mark.asyncio
async def test_simpan_memory_rls_fallback() -> None:
    """RLS Supabase tidak boleh menggagalkan pipeline webhook."""
    otak = OtakAI(RLSBlockedDB(), MockEmbed())
    saved = await otak.simpan_memory("toko_rafih:62811", {"content": "User: halo"})
    assert saved["content"].startswith("User:")
    assert otak._use_local_only is True


@pytest.mark.asyncio
async def test_simpan_dan_ambil_memory(otak_local: OtakAI) -> None:
    """Kasus 1: simpan dan retrieve memory pelanggan."""
    saved = await otak_local.simpan_memory("62811", {"content": "Pelanggan suka kopi hitam"})
    assert saved["user_id"] == "62811"
    assert "kopi" in saved["content"]
    assert len(saved["embedding"]) > 0

    rows = await otak_local.ambil_memory("62811")
    assert len(rows) == 1
    assert rows[0]["id"] == saved["id"]


@pytest.mark.asyncio
async def test_cari_semantic_ranking(otak_local: OtakAI) -> None:
    """Kasus 2: cari memory relevan dengan similarity."""
    await otak_local.simpan_memory("u1", {"content": "Stok kopi menipis"})
    await otak_local.simpan_memory("u1", {"content": "Pelanggan pesan indomie goreng"})

    hits = await otak_local.cari("kopi", pelanggan_id="u1", top_k=2)
    assert len(hits) >= 1
    assert "similarity" in hits[0]
    assert hits[0]["similarity"] >= hits[-1]["similarity"]


@pytest.mark.asyncio
async def test_feedback_positif_boost_weight(otak_local: OtakAI) -> None:
    """Kasus 3: feedback positif menaikkan weight."""
    mem = await otak_local.simpan_memory("u2", {"content": "Alamat kirim Jl. Merdeka 5"})
    updated = await otak_local.terima_feedback(mem["id"], rating=0.9, komentar="tepat")
    assert updated is not None
    assert updated["weight"] > 1.0
    assert updated["status"] == STATUS_ACTIVE


@pytest.mark.asyncio
async def test_feedback_negatif_mark_review(otak_local: OtakAI) -> None:
    """Kasus 4: feedback negatif → review atau delete."""
    mem = await otak_local.simpan_memory("u3", {"content": "Info salah tentang harga"})
    updated = await otak_local.terima_feedback(mem["id"], rating=-0.5)
    assert updated is not None
    assert updated["status"] in (STATUS_REVIEW, STATUS_DELETED)


@pytest.mark.asyncio
async def test_bangun_context_lengkap(otak_local: OtakAI) -> None:
    """Kasus 5: bangun context untuk LLM."""
    await otak_local.simpan_memory("u4", {"content": "Pelanggan langganan kopi setiap pagi"})
    ctx = await otak_local.bangun_context("u4", "Mau pesan kopi 2 liter")
    assert "PESAN SAAT INI" in ctx
    assert "kopi" in ctx.lower()


def test_cosine_similarity_identical() -> None:
    """Helper: vektor identik similarity = 1."""
    otak = OtakAI(MagicMock(), MockEmbed())
    v = [0.1, 0.2, 0.3]
    assert otak._cosine_similarity(v, v) == pytest.approx(1.0, abs=0.01)
