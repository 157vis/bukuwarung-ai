"""Personality engine — brand voice & tone adaptation per client UMKM."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx

from config import PROJECT_ROOT

logger = logging.getLogger(__name__)

LanguageCode = Literal["id", "jv", "su", "mixed"]
ProfileKey = Literal[
    "ramah_warm",
    "formal_pro",
    "santai_kids",
    "sunda_asli",
    "jawa_ngoko",
    "jawa_krama",
]

TABLE_BRAND = "brand_voices"
DEFAULT_PROFILE: ProfileKey = "ramah_warm"

# ---------------------------------------------------------------------------
# 6 personality templates (lengkap + contoh response)
# ---------------------------------------------------------------------------

PERSONALITY_PROFILES: dict[str, dict[str, Any]] = {
    "ramah_warm": {
        "label": "Ramah & Hangat",
        "greeting_style": "hangat",
        "emoji_usage": 2,
        "formality_level": 1,
        "language_mix": "id",
        "greeting": "Hai Kak! 😊 Senang bisa bantu hari ini~",
        "closing": "Kalau ada yang kurang jelas, chat aja ya! 🙏",
        "example_response": (
            "Hai Kak! 😊 Pesanan kopi 2 pack sudah kami catat ya. "
            "Totalnya Rp 7.000 — siap diambil kapan saja! 🙏"
        ),
        "tone_rules": ["pakai sapaan Kak/Bang", "emoji sedang", "kalimat pendek ramah"],
    },
    "formal_pro": {
        "label": "Formal Profesional",
        "greeting_style": "formal",
        "emoji_usage": 0,
        "formality_level": 3,
        "language_mix": "id",
        "greeting": "Selamat pagi. Terima kasih telah menghubungi kami.",
        "closing": "Apabila Bapak/Ibu memerlukan bantuan lebih lanjut, silakan sampaikan.",
        "example_response": (
            "Terima kasih atas pesanan Anda. Kami telah mencatat pembelian kopi sebanyak "
            "2 pack dengan total Rp 7.000. Pesanan dapat diambil sesuai kesepakatan."
        ),
        "tone_rules": ["tanpa emoji", "Bapak/Ibu", "bahasa baku"],
    },
    "santai_kids": {
        "label": "Santai & Fun",
        "greeting_style": "gaul",
        "emoji_usage": 3,
        "formality_level": 0,
        "language_mix": "id",
        "greeting": "Halo bestie! ✨ Lagi butuh apa nih?",
        "closing": "Gaskeun kalau mau order lagi ya 🔥",
        "example_response": (
            "Wih mantap! 🔥 Kopi 2 pack udah masuk list ya~ "
            "Total Rp 7.000. Tinggal ambil aja, gampang banget! 😎✨"
        ),
        "tone_rules": ["bahasa gaul", "emoji banyak", "enerjik"],
    },
    "sunda_asli": {
        "label": "Sunda Asli",
        "greeting_style": "lokal",
        "emoji_usage": 1,
        "formality_level": 1,
        "language_mix": "su",
        "greeting": "Wilujeng enjing! Kumaha damang?",
        "closing": "Mangga waé lamun aya nu kudu ditaroskeun deui.",
        "example_response": (
            "Hatur nuhun! Pesenan kopi 2 pack geus dicatet. "
            "Total Rp 7.000 — mangga dicandak waktos anu pas. 🙏"
        ),
        "tone_rules": ["campuran Sunda-Indonesia", "hatur nuhun", "mangga"],
    },
    "jawa_ngoko": {
        "label": "Jawa Ngoko",
        "greeting_style": "lokal",
        "emoji_usage": 1,
        "formality_level": 0,
        "language_mix": "jv",
        "greeting": "Halo mas! Piye kabare?",
        "closing": "Nek arep pesen maneh, kabari wae ya.",
        "example_response": (
            "Suwun mas! Pesenan kopi 2 pack wis tak catet. "
            "Total Rp 7.000 — monggo dijupuk kapan wae."
        ),
        "tone_rules": ["Jawa ngoko", "kowe/mas", "santai lokal"],
    },
    "jawa_krama": {
        "label": "Jawa Krama",
        "greeting_style": "sopan",
        "emoji_usage": 0,
        "formality_level": 3,
        "language_mix": "jv",
        "greeting": "Sugeng enjing. Kula panjenengan dumungi.",
        "closing": "Mangga, punapa dados kula biyantu malih.",
        "example_response": (
            "Matur nuwun sanget. Pesenan kopi 2 pack sampun kula cathet. "
            "Total Rp 7.000 — mangga dipun sedaya kados waktos ingkang pas."
        ),
        "tone_rules": ["Jawa krama", "kula/panjenengan", "sopan"],
    },
}

JAVA_KEYWORDS = ["piye", "opo", "kowe", "monggo", "matur", "sugeng", "nuwun", "inggih", "nggih", "kabare", "arep", "gawe", "mas", "mbak"]
SUNDA_KEYWORDS = ["kumaha", "naon", "abdi", "teh", "mah", "wilujeng", "hatur", "nuhun", "damang", "punten", "mangga", "sorangan"]

EMOJI_BY_LEVEL = {
    0: [],
    1: ["🙂"],
    2: ["😊", "🙏"],
    3: ["✨", "🔥", "😊", "🙏", "💪"],
}


class LLMClient(Protocol):
    """Protocol opsional untuk fallback deteksi bahasa."""

    async def complete(self, prompt: str) -> str:
        ...


class PersonalityEngine:
    """Engine kepribadian per-client — adaptasi tone & bahasa.

    Args:
        supabase_client: Client Supabase untuk brand_voices.
        llm_client: Client LLM opsional untuk deteksi bahasa.
    """

    def __init__(
        self,
        supabase_client: Any,
        llm_client: LLMClient | None = None,
        *,
        table_name: str = TABLE_BRAND,
        data_dir: Path | None = None,
    ) -> None:
        self._db = supabase_client
        self._llm = llm_client
        self._table = table_name
        self._data_dir = data_dir or (PROJECT_ROOT / "data")
        self._local_brands: dict[str, dict[str, Any]] = {}
        self._personality_cache: dict[str, dict[str, Any]] = {}
        self._phrases_jv = self._load_phrases("jawa_phrases.json")
        self._phrases_su = self._load_phrases("sunda_phrases.json")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_personality(self, client_id: str) -> dict[str, Any]:
        """Ambil konfigurasi personality client (cache + Supabase).

        Args:
            client_id: ID toko / tenant.

        Returns:
            Dict gabungan profile template + brand overrides.
        """
        if client_id in self._personality_cache:
            return self._personality_cache[client_id]

        brand = await self._load_brand_config(client_id)
        profile_key = str(brand.get("profile_key") or DEFAULT_PROFILE)
        if profile_key not in PERSONALITY_PROFILES:
            profile_key = DEFAULT_PROFILE

        merged = _merge_profile(client_id, profile_key, json.dumps(brand, sort_keys=True, default=str))
        self._personality_cache[client_id] = merged
        return merged

    async def adapt_tone(
        self,
        base_response: str,
        personality: dict[str, Any],
        user_lang: str | None = None,
    ) -> str:
        """Modifikasi respons sesuai personality & bahasa user.

        Args:
            base_response: Teks dasar dari agent.
            personality: Config dari ``get_personality``.
            user_lang: Kode bahasa user (id/jv/su/mixed); auto jika None.

        Returns:
            Respons dengan tone disesuaikan.
        """
        text = (base_response or "").strip()
        if not text:
            return text

        lang = user_lang or personality.get("detected_lang") or "id"
        profile_key = personality.get("profile_key", DEFAULT_PROFILE)

        # Prefix greeting ringan (hanya jika respons belum ada sapaan)
        if not self._has_greeting(text):
            greeting = str(personality.get("greeting") or "")
            if greeting:
                text = f"{greeting}\n\n{text}"

        # Formality
        level = int(personality.get("formality_level", 1))
        text = self._apply_formality(text, level, profile_key)

        # Emoji
        emoji_level = int(personality.get("emoji_usage", 1))
        text = self._apply_emoji(text, emoji_level)

        # Language mix (Jawa / Sunda)
        text = self._apply_language_mix(text, profile_key, lang)

        # Closing
        closing = str(personality.get("closing") or "")
        if closing and closing not in text:
            text = f"{text}\n\n{closing}"

        logger.info(
            "adapt_tone client=%s profile=%s lang=%s",
            personality.get("client_id", "?"),
            profile_key,
            lang,
        )
        return text.strip()

    async def detect_language(self, text: str) -> LanguageCode:
        """Deteksi bahasa user: keyword cepat + LLM fallback.

        Args:
            text: Pesan user.

        Returns:
            ``id``, ``jv``, ``su``, atau ``mixed``.
        """
        t = (text or "").lower()
        if not t.strip():
            return "id"

        jv_hits = sum(1 for kw in JAVA_KEYWORDS if kw in t)
        su_hits = sum(1 for kw in SUNDA_KEYWORDS if kw in t)

        if jv_hits and su_hits:
            result: LanguageCode = "mixed"
        elif jv_hits >= 2 or (jv_hits >= 1 and jv_hits > su_hits):
            result = "jv"
        elif su_hits >= 2 or (su_hits >= 1 and su_hits > jv_hits):
            result = "su"
        elif jv_hits == 1 or su_hits == 1:
            result = "jv" if jv_hits else "su"
        else:
            result = await self._llm_detect_language(t)

        logger.info("detect_language text=%r → %s", text[:50], result)
        return result

    # ------------------------------------------------------------------
    # Brand config
    # ------------------------------------------------------------------

    async def _load_brand_config(self, client_id: str) -> dict[str, Any]:
        """Muat brand voice dari Supabase; fallback default UMKM."""
        if client_id in self._local_brands:
            return self._local_brands[client_id]

        try:
            result = await asyncio.to_thread(
                lambda: (
                    self._db.table(self._table)
                    .select("*")
                    .eq("client_id", client_id)
                    .limit(1)
                    .execute()
                )
            )
            rows = result.data or []
            if rows:
                cfg = dict(rows[0])
                cfg["client_id"] = client_id
                return cfg
        except (OSError, ValueError, KeyError, AttributeError, httpx.HTTPError) as exc:
            logger.warning("_load_brand_config gagal client=%s: %s", client_id, exc)

        default = {
            "client_id": client_id,
            "profile_key": DEFAULT_PROFILE,
            "greeting_style": "hangat",
            "emoji_usage": 2,
            "formality_level": 1,
            "language_mix": "id",
            "custom_overrides": {},
        }
        logger.info("brand default untuk client=%s", client_id)
        return default

    def set_local_brand(self, client_id: str, config: dict[str, Any]) -> None:
        """Set brand config lokal (testing / offline USB)."""
        self._local_brands[client_id] = config
        self._personality_cache.pop(client_id, None)

    # ------------------------------------------------------------------
    # Tone helpers
    # ------------------------------------------------------------------

    def _apply_emoji(self, response: str, level: int) -> str:
        """Tambah atau kurangi emoji sesuai level 0-3."""
        level = max(0, min(3, level))
        if level == 0:
            return re.sub(
                r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+",
                "",
                response,
            ).strip()

        emojis = EMOJI_BY_LEVEL.get(level, ["😊"])
        if not re.search(r"[\U0001F300-\U0001FAFF]", response):
            response = f"{response} {emojis[0]}"
        if level >= 3 and len(emojis) > 1:
            response = f"{response} {emojis[1]}"
        return response

    def _apply_formality(self, response: str, level: int, profile_key: str) -> str:
        """Sesuaikan formality — ganti sapaan kasual/formal."""
        if level >= 3 or profile_key == "formal_pro":
            response = re.sub(r"\b(Kak|Bro|Bestie|Mas|Mbak)\b", "Bapak/Ibu", response, flags=re.I)
            response = response.replace("kamu", "Anda").replace("Kamu", "Anda")
            response = response.replace("udah", "sudah").replace("Udah", "Sudah")
        elif level <= 1 and profile_key == "santai_kids":
            response = response.replace("Anda", "kamu").replace("Bapak/Ibu", "Kak")
        return response

    def _apply_language_mix(self, text: str, profile_key: str, user_lang: str) -> str:
        """Campurkan frasa Jawa/Sunda sesuai profile."""
        if profile_key in ("jawa_ngoko", "jawa_krama") or user_lang == "jv":
            thanks = self._phrases_jv.get("thanks", ["Matur nuwun"])
            if profile_key == "jawa_ngoko":
                opener = "Suwun ya"
            else:
                opener = thanks[0] if thanks else "Matur nuwun"
            if opener.lower() not in text.lower():
                text = f"{opener}! {text}"

        if profile_key == "sunda_asli" or user_lang == "su":
            thanks = self._phrases_su.get("thanks", ["Hatur nuhun"])
            opener = thanks[0]
            if opener.lower() not in text.lower():
                text = f"{opener}! {text}"

        return text

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _llm_detect_language(self, text: str) -> LanguageCode:
        """Fallback LLM jika keyword tidak cukup."""
        if not self._llm:
            return "id"
        prompt = (
            "Deteksi bahasa pesan ini. Jawab HANYA satu kata: id, jv, su, atau mixed.\n"
            f"Pesan: {text[:300]}"
        )
        try:
            raw = (await self._llm.complete(prompt)).strip().lower()
            if raw in ("id", "jv", "su", "mixed"):
                return raw  # type: ignore[return-value]
        except (OSError, ValueError, AttributeError) as exc:
            logger.warning("LLM language detect gagal: %s", exc)
        return "id"

    def _load_phrases(self, filename: str) -> dict[str, Any]:
        path = self._data_dir / filename
        try:
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("load phrases %s gagal: %s", filename, exc)
        return {}

    @staticmethod
    def _has_greeting(text: str) -> bool:
        lower = text.lower()
        markers = ("halo", "hai", "selamat", "sugeng", "wilujeng", "pagi", "siang", "kak")
        return any(m in lower[:40] for m in markers)


@lru_cache(maxsize=128)
def _merge_profile(client_id: str, profile_key: str, brand_json: str) -> dict[str, Any]:
    """Gabungkan template personality dengan brand config (cached)."""
    brand = json.loads(brand_json) if isinstance(brand_json, str) else brand_json
    template = dict(PERSONALITY_PROFILES.get(profile_key, PERSONALITY_PROFILES[DEFAULT_PROFILE]))
    overrides = dict(brand.get("custom_overrides") or {})
    return {
        **template,
        "client_id": client_id,
        "profile_key": profile_key,
        "greeting_style": brand.get("greeting_style") or template.get("greeting_style"),
        "emoji_usage": brand.get("emoji_usage", template.get("emoji_usage", 2)),
        "formality_level": brand.get("formality_level", template.get("formality_level", 1)),
        "language_mix": brand.get("language_mix") or template.get("language_mix", "id"),
        **overrides,
    }
