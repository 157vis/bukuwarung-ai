"""Otak AI — long-term memory, semantic search, learning dari feedback."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

import httpx

from utils.embeddings import EmbeddingClient, cosine_similarity

logger = logging.getLogger(__name__)

TABLE_MEMORIES = "otak_memories"
TABLE_CHAT = "wa_messages"
STATUS_ACTIVE = "active"
STATUS_REVIEW = "review"
STATUS_DELETED = "deleted"


class MemoryRecord(TypedDict, total=False):
    """Format satu baris memory pelanggan."""

    id: str
    user_id: str
    content: str
    embedding: list[float]
    timestamp: str
    feedback_score: float
    weight: float
    status: str
    metadata: dict[str, Any]


class OtakAI:
    """Otak sistem: memory jangka panjang, semantic search, belajar dari feedback.

    Attributes:
        supabase_client: Client Supabase (sync — dibungkus asyncio.to_thread).
        embedding_client: Client async untuk generate embedding teks.
    """

    def __init__(
        self,
        supabase_client: Any,
        embedding_client: EmbeddingClient,
        *,
        table_name: str = TABLE_MEMORIES,
        chat_table: str = TABLE_CHAT,
        products_path: Any | None = None,
    ) -> None:
        """Inisialisasi Otak AI.

        Args:
            supabase_client: Instance supabase.Client.
            embedding_client: Objek dengan method async ``embed(text)``.
            table_name: Nama tabel memory di Supabase.
            chat_table: Nama tabel riwayat chat (opsional).
            products_path: Path ke products.json untuk context (opsional).
        """
        self._db = supabase_client
        self._embed = embedding_client
        self._table = table_name
        self._chat_table = chat_table
        self._products_path = products_path
        self._local_fallback: dict[str, list[MemoryRecord]] = {}
        self._use_local_only = False

    # ------------------------------------------------------------------
    # Long-term memory
    # ------------------------------------------------------------------

    async def simpan_memory(self, pelanggan_id: str, data: dict[str, Any]) -> MemoryRecord:
        """Simpan memory pelanggan ke Supabase (atau fallback lokal).

        Args:
            pelanggan_id: ID unik pelanggan / user.
            data: Minimal berisi ``content``; opsional ``metadata``, ``feedback_score``.

        Returns:
            Record memory yang tersimpan.

        Raises:
            ValueError: Jika ``content`` kosong.
        """
        content = str(data.get("content") or "").strip()
        if not content:
            raise ValueError("content wajib diisi untuk simpan_memory")

        embedding = await self._generate_embedding(content)
        now = datetime.now(timezone.utc).isoformat()
        record: MemoryRecord = {
            "id": str(uuid.uuid4()),
            "user_id": pelanggan_id,
            "content": content,
            "embedding": embedding,
            "timestamp": now,
            "feedback_score": float(data.get("feedback_score") or 0.0),
            "weight": float(data.get("weight") or 1.0),
            "status": STATUS_ACTIVE,
            "metadata": dict(data.get("metadata") or {}),
        }

        row = {**record, "embedding": record["embedding"]}

        try:
            result = await asyncio.to_thread(
                lambda: self._db.table(self._table).insert(row).execute()
            )
            rows = result.data or []
            if rows:
                saved = self._normalize_row(rows[0])
                logger.info("Memory tersimpan user=%s id=%s", pelanggan_id, saved.get("id"))
                return saved
        except (OSError, ValueError, KeyError, AttributeError) as exc:
            logger.error("simpan_memory Supabase gagal: %s — fallback lokal", exc)
            self._use_local_only = True

        self._local_fallback.setdefault(pelanggan_id, []).append(record)
        logger.info("Memory lokal user=%s id=%s", pelanggan_id, record["id"])
        return record

    async def ambil_memory(self, pelanggan_id: str) -> list[MemoryRecord]:
        """Ambil semua memory aktif untuk pelanggan.

        Args:
            pelanggan_id: ID pelanggan.

        Returns:
            Daftar memory (terbaru dulu).
        """
        if self._use_local_only:
            return [
                m for m in self._local_fallback.get(pelanggan_id, [])
                if m.get("status") != STATUS_DELETED
            ]

        try:
            result = await asyncio.to_thread(
                lambda: (
                    self._db.table(self._table)
                    .select("*")
                    .eq("user_id", pelanggan_id)
                    .neq("status", STATUS_DELETED)
                    .order("timestamp", desc=True)
                    .execute()
                )
            )
            rows = [self._normalize_row(r) for r in (result.data or [])]
            logger.info("ambil_memory user=%s count=%d", pelanggan_id, len(rows))
            return rows
        except (OSError, ValueError, KeyError, AttributeError, httpx.HTTPError) as exc:
            logger.error("ambil_memory gagal: %s — fallback lokal", exc)
            self._use_local_only = True
            return self._local_fallback.get(pelanggan_id, [])

    async def update_memory(self, memory_id: str, data: dict[str, Any]) -> MemoryRecord | None:
        """Update memory yang sudah ada.

        Args:
            memory_id: UUID memory.
            data: Field yang diupdate (content, metadata, feedback_score, dll.).

        Returns:
            Record terbaru atau None jika tidak ditemukan.
        """
        patch: dict[str, Any] = {}
        if "content" in data:
            content = str(data["content"]).strip()
            patch["content"] = content
            patch["embedding"] = await self._generate_embedding(content)
        for key in ("metadata", "feedback_score", "weight", "status"):
            if key in data:
                patch[key] = data[key]

        if not patch:
            return None

        try:
            result = await asyncio.to_thread(
                lambda: (
                    self._db.table(self._table)
                    .update(patch)
                    .eq("id", memory_id)
                    .execute()
                )
            )
            if result.data:
                logger.info("update_memory id=%s", memory_id)
                return self._normalize_row(result.data[0])
        except (OSError, ValueError, KeyError, AttributeError) as exc:
            logger.error("update_memory gagal: %s", exc)

        for memories in self._local_fallback.values():
            for mem in memories:
                if mem.get("id") == memory_id:
                    mem.update(patch)
                    if "embedding" in patch:
                        mem["embedding"] = patch["embedding"]
                    return mem
        return None

    # ------------------------------------------------------------------
    # Semantic search
    # ------------------------------------------------------------------

    async def cari(
        self,
        query: str,
        *,
        pelanggan_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Cari memory relevan dengan cosine similarity pada embedding.

        Args:
            query: Teks pencarian.
            pelanggan_id: Filter per user (opsional).
            top_k: Jumlah hasil teratas.

        Returns:
            List dict dengan keys memory + ``similarity`` (float).
        """
        query_vec = await self._generate_embedding(query)

        if pelanggan_id:
            pool = await self.ambil_memory(pelanggan_id)
        else:
            pool = []
            if self._use_local_only:
                for mems in self._local_fallback.values():
                    pool.extend(m for m in mems if m.get("status") != STATUS_DELETED)
            else:
                try:
                    result = await asyncio.to_thread(
                        lambda: (
                            self._db.table(self._table)
                            .select("*")
                            .neq("status", STATUS_DELETED)
                            .limit(500)
                            .execute()
                        )
                    )
                    pool = [self._normalize_row(r) for r in (result.data or [])]
                except (OSError, ValueError, KeyError, AttributeError) as exc:
                    logger.error("cari pool gagal: %s", exc)
                    pool = []

        scored: list[dict[str, Any]] = []
        for mem in pool:
            if mem.get("status") == STATUS_DELETED:
                continue
            emb = mem.get("embedding") or []
            sim = self._cosine_similarity(query_vec, emb)
            weight = float(mem.get("weight") or 1.0)
            scored.append({**mem, "similarity": sim * weight})

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        hits = scored[:top_k]
        logger.info("cari query=%r hits=%d", query[:60], len(hits))
        return hits

    # ------------------------------------------------------------------
    # Learning from feedback
    # ------------------------------------------------------------------

    async def terima_feedback(
        self,
        memory_id: str,
        rating: float,
        komentar: str = "",
    ) -> MemoryRecord | None:
        """Terima feedback user; boost atau tandai untuk review.

        Args:
            memory_id: ID memory.
            rating: Skor -1.0 s/d 1.0 (negatif = buruk, positif = bagus).
            komentar: Komentar opsional.

        Returns:
            Memory terupdate atau None.
        """
        rating = max(-1.0, min(1.0, float(rating)))
        patch: dict[str, Any] = {
            "feedback_score": rating,
            "metadata": {"komentar": komentar, "feedback_at": datetime.now(timezone.utc).isoformat()},
        }

        if rating >= 0.5:
            # Feedback positif → boost weight
            existing = await self._get_memory_by_id(memory_id)
            if existing:
                patch["weight"] = float(existing.get("weight") or 1.0) + 0.2 * rating
                patch["status"] = STATUS_ACTIVE
                logger.info("feedback positif memory=%s weight→%.2f", memory_id, patch["weight"])
        elif rating <= -0.3:
            # Feedback negatif → review atau hapus
            patch["status"] = STATUS_REVIEW if rating > -0.8 else STATUS_DELETED
            patch["weight"] = max(0.1, float((await self._get_memory_by_id(memory_id) or {}).get("weight") or 1.0) - 0.3)
            logger.warning("feedback negatif memory=%s status=%s", memory_id, patch["status"])

        return await self.update_memory(memory_id, patch)

    # ------------------------------------------------------------------
    # Contextual understanding
    # ------------------------------------------------------------------

    async def bangun_context(
        self,
        user_id: str,
        current_message: str,
        *,
        top_k: int = 5,
    ) -> str:
        """Rakit context lengkap untuk prompt LLM.

        Args:
            user_id: ID pelanggan.
            current_message: Pesan terbaru dari user.
            top_k: Jumlah memory relevan.

        Returns:
            String context siap sisip ke system/user prompt.
        """
        parts: list[str] = []

        relevan = await self.cari(current_message, pelanggan_id=user_id, top_k=top_k)
        if relevan:
            parts.append("=== MEMORY RELEVAN ===")
            for i, mem in enumerate(relevan, 1):
                parts.append(
                    f"{i}. [{mem.get('similarity', 0):.2f}] {mem.get('content', '')}"
                )

        riwayat = await self._ambil_riwayat_chat(user_id, limit=8)
        if riwayat:
            parts.append("\n=== RIWAYAT CHAT TERAKHIR ===")
            for msg in riwayat:
                role = msg.get("role", "user")
                parts.append(f"- {role}: {msg.get('content', '')[:200]}")

        produk = self._ambil_produk_terkait(current_message)
        if produk:
            parts.append("\n=== PRODUK TERKAIT ===")
            for p in produk:
                parts.append(f"- {p.get('name')}: Rp {p.get('price', 0):,}")

        parts.append(f"\n=== PESAN SAAT INI ===\n{current_message}")

        context = "\n".join(parts)
        logger.info("bangun_context user=%s len=%d", user_id, len(context))
        return context

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector untuk teks."""
        return await self._embed.embed(text)

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Cosine similarity wrapper."""
        return cosine_similarity(vec1, vec2)

    async def _get_memory_by_id(self, memory_id: str) -> MemoryRecord | None:
        try:
            result = await asyncio.to_thread(
                lambda: (
                    self._db.table(self._table)
                    .select("*")
                    .eq("id", memory_id)
                    .limit(1)
                    .execute()
                )
            )
            if result.data:
                return self._normalize_row(result.data[0])
        except (OSError, ValueError, KeyError, AttributeError):
            pass
        for memories in self._local_fallback.values():
            for mem in memories:
                if mem.get("id") == memory_id:
                    return mem
        return None

    async def _ambil_riwayat_chat(self, user_id: str, limit: int = 8) -> list[dict[str, Any]]:
        try:
            result = await asyncio.to_thread(
                lambda: (
                    self._db.table(self._chat_table)
                    .select("role, content, created_at")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(limit)
                    .execute()
                )
            )
            rows = result.data or []
            return list(reversed(rows))
        except (OSError, ValueError, KeyError, AttributeError) as exc:
            logger.debug("riwayat chat tidak tersedia: %s", exc)
            return []

    def _ambil_produk_terkait(self, message: str) -> list[dict[str, Any]]:
        """Cocokkan kata kunci pesan ke products.json lokal."""
        if not self._products_path:
            from config import PROJECT_ROOT
            path = PROJECT_ROOT / "data" / "products.json"
        else:
            path = self._products_path

        try:
            import json
            if not path.is_file():
                return []
            catalog = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(catalog, list):
                return []
            lower = message.lower()
            hits = [p for p in catalog if str(p.get("name", "")).lower() in lower]
            return hits[:5]
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            logger.debug("produk terkait gagal: %s", exc)
            return []

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> MemoryRecord:
        emb = row.get("embedding")
        if isinstance(emb, str):
            import json
            try:
                emb = json.loads(emb)
            except json.JSONDecodeError:
                emb = []
        return MemoryRecord(
            id=str(row.get("id", "")),
            user_id=str(row.get("user_id", "")),
            content=str(row.get("content", "")),
            embedding=[float(x) for x in (emb or [])],
            timestamp=str(row.get("timestamp") or row.get("created_at") or ""),
            feedback_score=float(row.get("feedback_score") or 0),
            weight=float(row.get("weight") or 1.0),
            status=str(row.get("status") or STATUS_ACTIVE),
            metadata=dict(row.get("metadata") or {}),
        )
