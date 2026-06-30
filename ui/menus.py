"""Definisi menu dashboard — tanpa impor silang ke modul UI lain."""

from __future__ import annotations

from dataclasses import dataclass

from ui.constants import MENU_SESSION_KEY

__all__ = [
    "MENU_SESSION_KEY",
    "LarisMenuItem",
    "LARIS_MENUS",
    "get_menu_item",
    "build_menu_keys",
    "display_label",
]


@dataclass(frozen=True)
class LarisMenuItem:
    key: str
    label: str
    tabler_icon: str
    dasher_section: str
    description: str


LARIS_MENUS: tuple[LarisMenuItem, ...] = (
    LarisMenuItem(
        "Ruang Komando",
        "Ruang Komando",
        "ti-layout-dashboard",
        "Home",
        "Keputusan AI menunggu persetujuan.",
    ),
    LarisMenuItem(
        "Ringkasan",
        "Ringkasan",
        "ti-chart-bar",
        "Dashboard",
        "Metrik bisnis & Laris Score.",
    ),
    LarisMenuItem(
        "Catat Transaksi",
        "Catat Transaksi",
        "ti-pencil-plus",
        "Transaksi",
        "Input pemasukan / pengeluaran.",
    ),
    LarisMenuItem(
        "Buku Kas",
        "Buku Kas",
        "ti-cash",
        "Keuangan",
        "Daftar transaksi & saldo.",
    ),
    LarisMenuItem(
        "Laporan KUR",
        "Laporan KUR",
        "ti-report-analytics",
        "Laporan",
        "Ringkasan untuk KUR.",
    ),
    LarisMenuItem(
        "Gudang",
        "Gudang",
        "ti-building-warehouse",
        "Inventori",
        "Stok & gudang.",
    ),
    LarisMenuItem(
        "⚙️ Pengaturan Bot",
        "Pengaturan Bot",
        "ti-settings",
        "Settings",
        "Token Fonnte & webhook WA.",
    ),
)


def get_menu_item(menu_key: str) -> LarisMenuItem | None:
    for item in LARIS_MENUS:
        if item.key == menu_key:
            return item
    return None


def build_menu_keys(*, warehouse_enabled: bool) -> list[str]:
    keys: list[str] = []
    for item in LARIS_MENUS:
        if item.key == "Gudang" and not warehouse_enabled:
            continue
        keys.append(item.key)
    return keys


def display_label(menu_key: str) -> str:
    item = get_menu_item(menu_key)
    if item:
        return item.label
    return menu_key
