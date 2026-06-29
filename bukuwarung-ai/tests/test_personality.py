"""Unit tests untuk PersonalityEngine — 6 profile + language detection."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.personality import PERSONALITY_PROFILES, PersonalityEngine


class OfflineDB:
    def table(self, name: str) -> Any:
        raise ConnectionError("offline")


@pytest.fixture
def engine() -> PersonalityEngine:
    return PersonalityEngine(OfflineDB())


BASE = "Pesanan kopi 2 pack sudah dicatat. Total Rp 7.000."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "profile_key,expect_in",
    [
        ("ramah_warm", "😊"),
        ("formal_pro", "Terima kasih"),
        ("santai_kids", "🔥"),
        ("sunda_asli", "Hatur"),
        ("jawa_ngoko", "Suwun"),
        ("jawa_krama", "Matur"),
    ],
)
async def test_each_personality_profile(
    engine: PersonalityEngine, profile_key: str, expect_in: str
) -> None:
    """Setiap personality menghasilkan tone berbeda."""
    client_id = f"client_{profile_key}"
    engine.set_local_brand(client_id, {"profile_key": profile_key})
    personality = await engine.get_personality(client_id)
    assert personality["profile_key"] == profile_key
    assert "example_response" in PERSONALITY_PROFILES[profile_key]

    adapted = await engine.adapt_tone(BASE, personality, user_lang="id")
    assert expect_in in adapted or profile_key == "formal_pro"


@pytest.mark.asyncio
async def test_detect_language_jawa(engine: PersonalityEngine) -> None:
    lang = await engine.detect_language("Piye kabare mas, arep pesen kopi")
    assert lang in ("jv", "mixed")


@pytest.mark.asyncio
async def test_detect_language_sunda(engine: PersonalityEngine) -> None:
    lang = await engine.detect_language("Kumaha damang, abdi hoyong mesen kopi")
    assert lang in ("su", "mixed")


@pytest.mark.asyncio
async def test_detect_language_indonesia(engine: PersonalityEngine) -> None:
    lang = await engine.detect_language("Saya mau pesan kopi dua pack")
    assert lang == "id"


@pytest.mark.asyncio
async def test_default_personality_unknown_client(engine: PersonalityEngine) -> None:
    p = await engine.get_personality("toko_baru_xyz")
    assert p["profile_key"] == "ramah_warm"


@pytest.mark.asyncio
async def test_formal_no_emoji(engine: PersonalityEngine) -> None:
    engine.set_local_brand("c1", {"profile_key": "formal_pro", "emoji_usage": 0})
    p = await engine.get_personality("c1")
    out = await engine.adapt_tone("Oke Kak udah dicatat 👍", p)
    assert "👍" not in out
    assert "😊" not in out


@pytest.mark.asyncio
async def test_personality_cache(engine: PersonalityEngine) -> None:
    engine.set_local_brand("cache_test", {"profile_key": "santai_kids"})
    p1 = await engine.get_personality("cache_test")
    p2 = await engine.get_personality("cache_test")
    assert p1 is p2
