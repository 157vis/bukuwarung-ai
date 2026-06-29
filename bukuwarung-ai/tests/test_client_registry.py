"""Tests client registry multi-tenant."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.client_registry import ClientRegistry


@pytest.fixture
def registry():
    return ClientRegistry(db=None)


@pytest.mark.asyncio
async def test_load_from_example_json(registry: ClientRegistry) -> None:
    cfg = await registry.get("toko_berkah")
    assert cfg is not None
    assert cfg.name == "Warung Berkah"
    assert len(cfg.products) >= 1
    assert cfg.profile_key == "ramah_warm"


@pytest.mark.asyncio
async def test_memory_scope(registry: ClientRegistry) -> None:
    cfg = await registry.get("toko_berkah")
    assert cfg is not None
    assert cfg.memory_scope("628123") == "toko_berkah:628123"


@pytest.mark.asyncio
async def test_list_active(registry: ClientRegistry) -> None:
    clients = await registry.list_active()
    assert len(clients) >= 2
    ids = {c.client_id for c in clients}
    assert "toko_berkah" in ids
    assert "toko_segar" in ids
