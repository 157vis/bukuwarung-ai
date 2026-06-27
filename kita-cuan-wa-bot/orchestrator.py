"""Orchestrator multi-agent: Admin AI catat transaksi → Logistik AI update stok."""

from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import core

STOCK_THRESHOLD = int(os.environ.get("STOCK_THRESHOLD", "10"))
REORDER_QTY = int(os.environ.get("REORDER_QTY", "20"))


def orchestrate_transaction_created(
    user_id: str,
    raw_text: str,
    transactions: list[dict],
    *,
    stock_threshold: int | None = None,
    reorder_qty: int | None = None,
) -> str:
    """Setelah Admin AI menyimpan transaksi, jalankan Logistik AI untuk tiap penjualan.

    Return teks tambahan untuk balasan WA (bisa kosong).
    """
    threshold = stock_threshold if stock_threshold is not None else STOCK_THRESHOLD
    reorder = reorder_qty if reorder_qty is not None else REORDER_QTY
    notes: list[str] = []

    for txn in transactions or []:
        if str(txn.get("type") or "").lower() != "pemasukan":
            continue
        result = core.run_logistik_after_sale(
            user_id,
            txn,
            raw_text,
            stock_threshold=threshold,
            reorder_qty=reorder,
        )
        if result and result.get("message"):
            notes.append(result["message"])

    if not notes:
        return ""
    return "\n\n" + "\n\n".join(notes)
