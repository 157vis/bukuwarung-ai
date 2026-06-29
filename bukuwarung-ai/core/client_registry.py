"""Registry multi-client — satu deploy Railway, banyak toko UMKM."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT, get_settings

logger = logging.getLogger(__name__)

TABLE_CLIENTS = "clients"
CLIENTS_JSON = PROJECT_ROOT / "data" / "clients.json"
CLIENTS_EXAMPLE = PROJECT_ROOT / "data" / "clients.example.json"


@dataclass
class ClientConfig:
    """Konfigurasi satu tenant / toko."""

    client_id: str
    name: str
    fonnte_token: str = ""
    owner_phones: list[str] = field(default_factory=list)
    profile_key: str = "ramah_warm"
    products: list[dict[str, Any]] = field(default_factory=list)
    payment_methods: list[dict[str, Any]] = field(default_factory=list)
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def owner_phone_set(self) -> frozenset[str]:
        return frozenset("".join(c for c in p if c.isdigit()) for p in self.owner_phones if p)

    def memory_scope(self, user_id: str) -> str:
        """Kunci memory terisolasi per toko + pelanggan."""
        phone = "".join(c for c in user_id if c.isdigit())
        return f"{self.client_id}:{phone}"


class ClientRegistry:
    """Muat & cache config client dari Supabase atau data/clients.json."""

    def __init__(self, db: Any | None = None) -> None:
        self._db = db
        self._cache: dict[str, ClientConfig] = {}
        self._token_index: dict[str, str] = {}

    async def get(self, client_id: str) -> ClientConfig | None:
        if client_id in self._cache:
            return self._cache[client_id]

        cfg = await self._load_from_db(client_id) or self._load_from_json(client_id)
        if cfg:
            self._index(cfg)
        return cfg

    async def get_by_fonnte_token(self, token: str) -> ClientConfig | None:
        token = (token or "").strip()
        if not token:
            return None
        if token in self._token_index:
            return await self.get(self._token_index[token])

        await self._warm_json_cache()
        if token in self._token_index:
            return await self.get(self._token_index[token])

        if self._db:
            try:
                result = await asyncio.to_thread(
                    lambda: (
                        self._db.table(TABLE_CLIENTS)
                        .select("*")
                        .eq("fonnte_token", token)
                        .eq("is_active", True)
                        .limit(1)
                        .execute()
                    )
                )
                rows = result.data or []
                if rows:
                    cfg = self._from_row(rows[0])
                    self._index(cfg)
                    return cfg
            except Exception as exc:
                logger.warning("get_by_fonnte_token gagal: %s", exc)
        return None

    async def list_active(self) -> list[ClientConfig]:
        await self._warm_json_cache()
        if self._db and get_settings().is_supabase_live:
            try:
                result = await asyncio.to_thread(
                    lambda: (
                        self._db.table(TABLE_CLIENTS)
                        .select("*")
                        .eq("is_active", True)
                        .execute()
                    )
                )
                for row in result.data or []:
                    self._index(self._from_row(row))
            except Exception as exc:
                logger.warning("list_active supabase gagal: %s", exc)
        return [c for c in self._cache.values() if c.is_active]

    async def _load_from_db(self, client_id: str) -> ClientConfig | None:
        if not self._db or not get_settings().is_supabase_live:
            return None
        try:
            result = await asyncio.to_thread(
                lambda: (
                    self._db.table(TABLE_CLIENTS)
                    .select("*")
                    .eq("client_id", client_id)
                    .limit(1)
                    .execute()
                )
            )
            rows = result.data or []
            return self._from_row(rows[0]) if rows else None
        except Exception as exc:
            logger.warning("load client %s dari DB gagal: %s", client_id, exc)
            return None

    def _load_from_json(self, client_id: str) -> ClientConfig | None:
        data = self._read_json_file()
        raw = data.get(client_id)
        if not raw:
            return None
        return self._from_dict(client_id, raw)

    async def _warm_json_cache(self) -> None:
        for client_id, raw in self._read_json_file().items():
            if client_id not in self._cache:
                self._index(self._from_dict(client_id, raw))

    def _read_json_file(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for path in (CLIENTS_EXAMPLE, CLIENTS_JSON):
            try:
                if path.is_file():
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        merged.update(data)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("baca clients json gagal %s: %s", path.name, exc)
        return merged

    def _index(self, cfg: ClientConfig) -> None:
        self._cache[cfg.client_id] = cfg
        if cfg.fonnte_token:
            self._token_index[cfg.fonnte_token] = cfg.client_id

    @staticmethod
    def _from_row(row: dict[str, Any]) -> ClientConfig:
        owners = row.get("owner_phones") or []
        if isinstance(owners, str):
            owners = [p.strip() for p in owners.split(",") if p.strip()]
        return ClientConfig(
            client_id=str(row["client_id"]),
            name=str(row.get("name") or row["client_id"]),
            fonnte_token=str(row.get("fonnte_token") or ""),
            owner_phones=list(owners),
            profile_key=str(row.get("profile_key") or "ramah_warm"),
            products=list(row.get("products") or []),
            payment_methods=list(row.get("payment_methods") or []),
            is_active=bool(row.get("is_active", True)),
            metadata=dict(row.get("metadata") or {}),
        )

    @staticmethod
    def _from_dict(client_id: str, raw: dict[str, Any]) -> ClientConfig:
        return ClientConfig(
            client_id=client_id,
            name=str(raw.get("name") or client_id),
            fonnte_token=str(raw.get("fonnte_token") or ""),
            owner_phones=list(raw.get("owner_phones") or []),
            profile_key=str(raw.get("profile_key") or "ramah_warm"),
            products=list(raw.get("products") or []),
            payment_methods=list(raw.get("payment_methods") or []),
            is_active=bool(raw.get("is_active", True)),
            metadata=dict(raw.get("metadata") or {}),
        )


_registry: ClientRegistry | None = None


def get_client_registry(db: Any | None = None) -> ClientRegistry:
    global _registry
    if _registry is None:
        _registry = ClientRegistry(db)
    return _registry
