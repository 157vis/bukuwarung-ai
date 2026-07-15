"""Sidebar Dasher-style — menu, logo, dan tombol logout."""

from __future__ import annotations

import html

import streamlit as st

from brand import APP_NAME
from ui.components import sidebar_brand
from ui.constants import MENU_SESSION_KEY
from ui.menus import build_menu_keys, get_menu_item


def init_menu(default_key: str) -> None:
    if MENU_SESSION_KEY not in st.session_state:
        st.session_state[MENU_SESSION_KEY] = default_key


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

    st.sidebar.markdown(" ", unsafe_allow_html=True)

    user_label = html.escape(user_email or "")
    st.sidebar.markdown(
        f'<div class="laris-user-chip">'
        f'<small class="text-muted">Pengguna</small><br/>'
        f'<strong>{user_label or "—"}</strong>'
        '</div>',
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
    display = f"{item.icon} {item.label}"
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
