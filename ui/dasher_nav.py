"""Sidebar Dasher-style — menu, logo, dan tombol logout.

Mengelompokkan menu per section (Operasional / Inventori / Sistem).
"""

from __future__ import annotations

import html

import streamlit as st

from brand import APP_NAME
from ui.components import sidebar_brand
from ui.constants import MENU_SESSION_KEY
from ui.menus import (
    LARIS_MENUS,
    build_menu_keys,
    get_menu_item,
    is_admin_only,
)


def init_menu(default_key: str) -> None:
    if MENU_SESSION_KEY not in st.session_state:
        st.session_state[MENU_SESSION_KEY] = default_key


def get_active_menu(*, warehouse_enabled: bool, is_admin: bool = False) -> str:
    keys = build_menu_keys(warehouse_enabled=warehouse_enabled, is_admin=is_admin)
    current = st.session_state.get(MENU_SESSION_KEY, keys[0] if keys else "Ruang Komando")
    if current not in keys:
        current = keys[0] if keys else "Ruang Komando"
        st.session_state[MENU_SESSION_KEY] = current
    return current


def _section_label(text: str) -> str:
    return (
        '<div class="nav-heading px-3 mt-3 mb-1">'
        f'<small class="text-uppercase fw-bold text-muted">{html.escape(text)}</small>'
        "</div>"
    )


def render_sidebar_nav(
    *, warehouse_enabled: bool, user_email: str | None, is_admin: bool = False
) -> str:
    """Render sidebar dengan grouping per section.

    Returns:
        Active menu key
    """
    keys = build_menu_keys(warehouse_enabled=warehouse_enabled, is_admin=is_admin)
    init_menu(keys[0])
    current = get_active_menu(
        warehouse_enabled=warehouse_enabled, is_admin=is_admin
    )

    sidebar_brand()

    # Group menu items by dasher_section
    sections: dict[str, list[str]] = {}
    for item in LARIS_MENUS:
        if item.key not in keys:
            continue
        sections.setdefault(item.dasher_section, []).append(item.key)

    # Render per section
    section_order = ["Operasional", "Inventori", "Sistem"]
    for section_name in section_order:
        section_keys = sections.get(section_name, [])
        if not section_keys:
            continue
        st.sidebar.markdown(_section_label(section_name), unsafe_allow_html=True)
        for key in section_keys:
            _render_menu_button(key, current)

    # User info + logout (di bawah, bukan menu)
    st.sidebar.markdown(" ", unsafe_allow_html=True)

    user_label = html.escape(user_email or "")
    st.sidebar.markdown(
        f'<div class="laris-user-chip">'
        f'<small class="text-muted">Pengguna</small><br/>'
        f'<strong>{user_label or "—"}</strong>'
        '</div>',
        unsafe_allow_html=True,
    )

    return current


def _render_menu_button(key: str, current: str) -> None:
    item = get_menu_item(key)
    if not item:
        return
    is_active = key == current
    # Tampilkan emoji + label, plus badge "(Admin)" untuk menu admin-only
    admin_badge = ""
    if item.admin_only:
        admin_badge = ' <span style="font-size:0.6rem;background:#fef3c7;color:#92400e;padding:1px 5px;border-radius:4px;font-weight:600;margin-left:4px;">ADMIN</span>'
    display = f"{item.icon} {item.label}{admin_badge}"
    btn_key = f"nav_{key}"
    if st.sidebar.button(
        display,
        key=btn_key,
        use_container_width=True,
        type="primary" if is_active else "secondary",
        help=item.description,
    ):
        st.session_state[MENU_SESSION_KEY] = key
        st.toast(f"➡️ Pindah ke {item.label}", icon="✅")
        st.rerun()


__all__ = [
    "init_menu",
    "get_active_menu",
    "render_sidebar_nav",
    "is_admin_only",
]
