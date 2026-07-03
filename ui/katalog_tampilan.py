"""Katalog tampilan UI — tempat TERPUSAT untuk atur warna/teks UI.

Kenapa file ini ada:
  - Anda ingin "edit tampilan UI yang mudah".
  - Daripada nyebar warna di CSS, semua warna & label dasbor dikumpulkan di sini.
  - Tinggal ubah konstanta di bawah, lalu deploy. Tidak perlu sentuh CSS.

Cara pakai:
  from ui.katalog_tampilan import WARNA, LABEL, TAMPILAN
  st.markdown(TAMPILAN["card_aksi"].format(judul="...", isi="..."), unsafe_allow_html=True)
"""

from __future__ import annotations

from dataclasses import dataclass


# =============================================================================
# WARNA — ganti di sini untuk ubah keseluruhan dasbor.
# =============================================================================
@dataclass(frozen=True)
class PaletWarna:
    primer: str = "#00a76f"        # hijau Dasher (tombol utama, badge aktif)
    primer_gelap: str = "#008f5f"   # hover tombol
    latar: str = "#f9fafb"          # latar body
    kartu: str = "#ffffff"          # kartu
    batas: str = "#dfe3e8"          # garis batas
    teks: str = "#141a21"           # teks utama
    teks_muted: str = "#637381"     # teks sekunder
    sukses: str = "#00a76f"
    bahaya: str = "#d93025"
    info: str = "#00b8d4"
    ungu: str = "#7c4dff"


WARNA = PaletWarna()


# =============================================================================
# LABEL — teks yang tampil di sidebar, topbar, dan tombol.
# Ganti di sini kalau ingin Bahasa Indonesia diubah / ditambah English, dll.
# =============================================================================
@dataclass(frozen=True)
class LabelDasbor:
    app_name: str = "laris.AI"
    app_tagline: str = "Partner Bisnis UMKM"
    sidebar_brand_caption: str = "Partner Bisnis UMKM"
    section_operasional: str = "Operasional"
    section_inventori: str = "Inventori"
    section_sistem: str = "Sistem"
    topbar_pengguna: str = "Pengguna"
    tombol_keluar: str = "Keluar"
    tombol_kembali_beranda: str = "← Kembali ke Beranda"
    pesan_kosong_transaksi: str = "Belum ada transaksi"
    hint_transaksi_pertama: str = (
        "Catat transaksi pertama Anda lewat menu 'Catat Transaksi' atau lewat WhatsApp."
    )


LABEL = LabelDasbor()


# =============================================================================
# TAMPILAN — snippet HTML/CSS siap pakai.
# Setiap key adalah blok visual yang tinggal di-format() dengan parameter.
# =============================================================================
TAMPILAN: dict[str, str] = {
    "card_aksi": """
        <div class="card card-lg h-100" style="border:1px solid {w.batas};border-radius:1rem;">
          <div class="card-body">
            <h5 class="mb-1">{judul}</h5>
            <p class="text-muted mb-2">{isi}</p>
            {tombol}
          </div>
        </div>
    """,
    "pengingat": """
        <div class="alert alert-info" role="alert" style="border-radius:0.75rem;">
          {pesan}
        </div>
    """,
    "chip_status": """
        <span class="badge" style="background:{warna_bg};color:{warna_teks};
                                   padding:0.4rem 0.8rem;border-radius:999px;">
          {label}
        </span>
    """,
    "stat_tile": """
        <div class="card card-lg h-100" style="border:1px solid {w.batas};border-radius:1rem;">
          <div class="card-body">
            <small class="text-muted">{label}</small>
            <div class="fs-3 fw-bold mt-1">{nilai}</div>
          </div>
        </div>
    """,
}


def stat_tile(label: str, nilai: str, warna_teks: str | None = None) -> str:
    """Snippet kartu statistik kecil — tinggal di st.markdown(...)."""
    color = warna_teks or WARNA.teks
    return (
        f'<div class="card card-lg h-100" style="border:1px solid {WARNA.batas};'
        f'border-radius:1rem;">'
        f'<div class="card-body">'
        f'<small class="text-muted">{label}</small>'
        f'<div class="fs-3 fw-bold mt-1" style="color:{color};">{nilai}</div>'
        f"</div></div>"
    )


def chip(label: str, *, tone: str = "info") -> str:
    """Chip warna-warni. tone: success | warning | danger | info | primary."""
    palette = {
        "success": ("#c8fad6", "#007867"),
        "warning": ("#fff5cf", "#7a5901"),
        "danger": ("#ffe9d6", "#b71d18"),
        "info": ("#cff9fc", "#016678"),
        "primary": ("#ede4ff", "#491e8c"),
    }
    bg, fg = palette.get(tone, palette["info"])
    return (
        f'<span class="badge" style="background:{bg};color:{fg};'
        f'padding:0.4rem 0.8rem;border-radius:999px;font-weight:600;">'
        f"{label}</span>"
    )
