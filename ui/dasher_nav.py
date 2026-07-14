"""Sidebar Dasher-style — menu, logo, dan tombol logout."""

from __future__ import annotations

import html

import streamlit as st

from brand import APP_NAME
from ui.components import sidebar_brand
from ui.constants import MENU_SESSION_KEY, SIDEBAR_OPEN_KEY
from ui.menus import build_menu_keys, get_menu_item


def init_menu(default_key: str) -> None:
    if MENU_SESSION_KEY not in st.session_state:
        st.session_state[MENU_SESSION_KEY] = default_key


def is_sidebar_open() -> bool:
    """Apakah sidebar sedang terbuka? Default True (visible)."""
    return st.session_state.get(SIDEBAR_OPEN_KEY, True)


def toggle_sidebar() -> None:
    """Toggle state sidebar (open <-> closed)."""
    st.session_state[SIDEBAR_OPEN_KEY] = not is_sidebar_open()


def render_open_sidebar_button() -> None:
    """Tombol floating '>' di kiri atas yang HANYA muncul saat sidebar
    tertutup. Klik untuk membuka kembali sidebar.
    """
    if is_sidebar_open():
        return  # sidebar sudah terbuka, tombol tidak perlu
    # Render floating button di pojok kiri atas
    st.markdown(
        """
        <style>
        .laris-open-sidebar-btn {
            position: fixed;
            top: 0.6rem;
            left: 0.4rem;
            z-index: 999999;
            background: linear-gradient(135deg, #7c3aed, #6366f1);
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 0.7rem;
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .laris-open-sidebar-btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(124, 58, 237, 0.5);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button("☰", key="open_sidebar_btn", help="Buka sidebar (Ctrl+B)"):
        toggle_sidebar()
        st.rerun()


def get_active_menu(*, warehouse_enabled: bool) -> str:
    keys = build_menu_keys(warehouse_enabled=warehouse_enabled)
    current = st.session_state.get(MENU_SESSION_KEY, keys[0] if keys else "Ringkasan")
    if current not in keys:
        current = keys[0] if keys else "Ringkasan"
        st.session_state[MENU_SESSION_KEY] = current
    return current


def _section_label(text: str) -> str:
    return (
        '<div class="nav-heading px-3 mt-3 mb-1">'
        f'<small class="text-uppercase fw-bold text-muted">{html.escape(text)}</small>'
        "</div>"
    )


def render_sidebar_nav(*, warehouse_enabled: bool, user_email: str | None) -> str:
    keys = build_menu_keys(warehouse_enabled=warehouse_enabled)
    init_menu(keys[0])
    current = get_active_menu(warehouse_enabled=warehouse_enabled)

    sidebar_brand()

    # Tombol close sidebar (X) di kanan atas sidebar
    close_col, _spacer = st.sidebar.columns([1, 0.1])
    with close_col:
        if st.button(
            "✕ Tutup",
            key="close_sidebar_btn",
            help="Tutup sidebar (klik ☰ di kiri atas untuk buka lagi)",
            use_container_width=False,
        ):
            toggle_sidebar()
            st.rerun()

    # Section utama
    st.sidebar.markdown(_section_label("Operasional"), unsafe_allow_html=True)
    main_keys = ["Ruang Komando", "Ringkasan", "Catat Transaksi", "Buku Kas", "Laporan KUR"]
    for key in main_keys:
        if key not in keys:
            continue
        _render_menu_button(key, current)

    # Section Inventori (jika ada)
    if warehouse_enabled and "Gudang" in keys:
        st.sidebar.markdown(_section_label("Inventori"), unsafe_allow_html=True)
        _render_menu_button("Gudang", current)

    # Section Sistem
    st.sidebar.markdown(_section_label("Sistem"), unsafe_allow_html=True)
    _render_menu_button("⚙️ Pengaturan Bot", current)

    st.sidebar.markdown("<hr class='my-3'>", unsafe_allow_html=True)

    user_label = html.escape(user_email or "")
    st.sidebar.markdown(
        f'<div class="px-3 mb-2"><small class="text-muted">Pengguna</small><br>'
        f'<span class="fw-semibold">{user_label or "—"}</span></div>',
        unsafe_allow_html=True,
    )
    if st.sidebar.button(
        "Keluar",
        key="sidebar_logout",
        use_container_width=True,
        type="secondary",
    ):
        from login import logout

        logout()
        st.rerun()

    return current


def _render_menu_button(key: str, current: str) -> None:
    item = get_menu_item(key)
    if not item:
        return
    is_active = key == current
    # Tampilkan emoji icon di depan label untuk look yang lebih modern
    # (Streamlit button tidak support icon, jadi pakai emoji di label)
    display = f"{item.icon}  {item.label}"
    # PENTING: gunakan key unik per menu agar Streamlit tidak bingung saat
    # `type` (primary/secondary) berubah antara halaman aktif/non-aktif.
    btn_key = f"nav_{key}"
    if st.sidebar.button(
        display,
        key=btn_key,
        use_container_width=True,
        type="primary" if is_active else "secondary",
        help=f"Buka menu {item.label}",
    ):
        st.session_state[MENU_SESSION_KEY] = key
        st.toast(f"➡️ Pindah ke {item.label}", icon="✅")
        st.rerun()


def render_topbar(*, page_title: str, user_email: str | None, show_menu: bool) -> None:
    email = html.escape(user_email or "")
    title = html.escape(page_title)
    st.markdown(
        f"""
        <div class="laris-dasher-topbar d-flex align-items-center justify-content-between flex-wrap gap-3">
            <div class="d-flex align-items-center gap-3">
                <span class="laris-page-badge">Menu</span>
                <div>
                    <h2 class="mb-0">{title}</h2>
                    <small class="text-muted">{APP_NAME} · dashboard UMKM</small>
                </div>
            </div>
            <div class="laris-user-chip d-none d-md-flex align-items-center gap-2">
                <i class="ti ti-user-circle fs-3 text-primary"></i>
                <div class="lh-sm">
                    <small class="d-block text-muted">Pengguna</small>
                    <strong class="fs-6">{email or "—"}</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, _c2, c3 = st.columns([1, 8, 2])
    with c1:
        if st.button("☰", key="dasher_toggle_sidebar", help="Tampilkan / sembunyikan menu"):
            st.session_state.show_menu = not st.session_state.get("show_menu", True)
            st.rerun()
    with c3:
        if st.button("Keluar", key="topbar_logout", use_container_width=True):
            from login import logout

            logout()
            st.rerun()