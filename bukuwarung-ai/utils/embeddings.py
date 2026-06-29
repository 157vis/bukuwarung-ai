"""Groq embeddings dengan fallback lokal (portable, tanpa GPU wajib)."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

GROQ_EMBED_URL = "https://api.groq.com/openai/v1/embeddings"
DEFAULT_EMBED_MODEL = "nomic-embed-text-v1.5"
LOCAL_DIM = 384


class EmbeddingClient(Protocol):
    """Protocol untuk client embedding (Groq atau mock)."""

    async def embed(self, text: str) -> list[float]:
        ...


class GroqEmbeddingClient:
    """Generate embeddings via Groq OpenAI-compatible API."""

    def __init__(self, api_key: str, model: str = DEFAULT_EMBED_MODEL) -> None:
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str) -> list[float]:
        """Return embedding vector; fallback lokal jika API gagal."""
        if not (text or "").strip():
            return _local_embedding("empty")

        if not self._api_key:
            logger.warning("GROQ_API_KEY kosong — pakai fallback lokal")
            return _local_embedding(text)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    GROQ_EMBED_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": self._model, "input": text},
                )
                resp.raise_for_status()
                payload = resp.json()
                vector = payload["data"][0]["embedding"]
                return [float(x) for x in vector]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            logger.warning("Groq embedding gagal (%s) — fallback lokal", exc)
            return _local_embedding(text)


def _local_embedding(text: str, dim: int = LOCAL_DIM) -> list[float]:
    """Fallback deterministik: hash → vektor ter-normalisasi (cosine-ready)."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = [digest[i % len(digest)] / 255.0 for i in range(dim)]
    norm = math.sqrt(sum(x * x for x in raw)) or 1.0
    return [x / norm for x in raw]


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Hitung cosine similarity antara dua vektor."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        # Pad/truncate ke panjang minimum untuk fallback campuran dimensi
        n = min(len(vec1), len(vec2))
        if n == 0:
            return 0.0
        vec1, vec2 = vec1[:n], vec2[:n]
    dot = sum(a * b for a, b in zip(vec1, vec2))
    n1 = math.sqrt(sum(a * a for a in vec1)) or 1.0
    n2 = math.sqrt(sum(b * b for b in vec2)) or 1.0
    return float(dot / (n1 * n2))
