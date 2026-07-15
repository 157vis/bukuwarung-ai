"""Definisi menu dashboard — tanpa impor silang ke modul UI lain.

Struktur menu (9 item):

  OPERASIONAL (semua user):
    1. Ruang Komando     - Approval AI
    2. Ringkasan         - Dashboard metrics
    3. Catat Transaksi   - Form input
    4. Buku Kas          - Tabel transaksi
    5. Laporan KUR       - Laporan bank

  INVENTORI (semua user, Tambah Gudang khusus admin):
    6. Tambah Gudang     - Form input gudang (ADMIN ONLY)
    7. Gudang            - Daftar produk per client (semua user, read-only)

  SISTEM:
    8. Pengaturan Bot    - Konfigurasi Fonnte (ADMIN ONLY)
    9. Pengaturan        - Keluar + Chat Admin (semua user)
"""

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
    "is_admin_only",
]


@dataclass(frozen=True)
class LarisMenuItem:
    key: str
    label: str
    icon: str           # emoji icon untuk sidebar (modern look)
    tabler_icon: str    # Tabler icon class
    dasher_section: str # "Operasional" | "Inventori" | "Sistem"
    description: str
    admin_only: bool = False


LARIS_MENUS: tuple[LarisMenuItem, ...] = (
    # === OPERASIONAL (semua user) ===
    LarisMenuItem(
        "Ruang Komando",
        "Ruang Komando",
        "🧠",
        "ti-layout-dashboard",
        "Operasional",
        "Keputusan AI menunggu persetujuan.",
    ),
    LarisMenuItem(
        "Ringkasan",
        "Ringkasan",
        "📊",
        "ti-chart-bar",
        "Operasional",
        "Metrik bisnis & Laris Score.",
    ),
    LarisMenuItem(
        "Catat Transaksi",
        "Catat Transaksi",
        "✏️",
        "ti-pencil-plus",
        "Operasional",
        "Input pemasukan / pengeluaran.",
    ),
    LarisMenuItem(
        "Buku Kas",
        "Buku Kas",
        "💰",
        "ti-cash",
        "Operasional",
        "Daftar transaksi & saldo.",
    ),
    LarisMenuItem(
        "Laporan KUR",
        "Laporan KUR",
        "📈",
        "ti-report-analytics",
        "Operasional",
        "Ringkasan untuk pengajuan KUR.",
    ),

    # === INVENTORI ===
    LarisMenuItem(
        "Tambah Gudang",
        "Tambah Gudang",
        "🏬",
        "ti-building-warehouse",
        "Inventori",
        "Tambah gudang baru (admin only).",
        admin_only=True,
    ),
    LarisMenuItem(
        "Gudang",
        "Gudang",
        "📦",
        "ti-box",
        "Inventori",
        "Daftar produk per client.",
    ),

    # === SISTEM ===
    LarisMenuItem(
        "Pengaturan Bot",
        "Pengaturan Bot",
        "🤖",
        "ti-robot",
        "Sistem",
        "Konfigurasi Fonnte & webhook WA (admin only).",
        admin_only=True,
    ),
    LarisMenuItem(
        "Pengaturan",
        "Pengaturan",
        "⚙️",
        "ti-settings",
        "Sistem",
        "Keluar & hubungi admin.",
    ),
)


def get_menu_item(menu_key: str) -> LarisMenuItem | None:
    for item in LARIS_MENUS:
        if item.key == menu_key:
            return item
    return None


def is_admin_only(menu_key: str) -> bool:
    """Cek apakah menu ini hanya untuk admin."""
    item = get_menu_item(menu_key)
    return bool(item and item.admin_only)


def build_menu_keys(
    *, warehouse_enabled: bool, is_admin: bool = False
) -> list[str]:
    """Bangun daftar menu keys yang visible untuk user.

    Args:
        warehouse_enabled: apakah fitur warehouse aktif
        is_admin: apakah user adalah super admin
    """
    keys: list[str] = []
    for item in LARIS_MENUS:
        # Admin-only menu: skip kalau bukan admin
        if item.admin_only and not is_admin:
            continue
        # Gudang (read-only): butuh warehouse enabled
        if item.key == "Gudang" and not warehouse_enabled:
            continue
        keys.append(item.key)
    return keys


def display_label(menu_key: str) -> str:
    item = get_menu_item(menu_key)
    if item:
        return item.label
    return menu_key
