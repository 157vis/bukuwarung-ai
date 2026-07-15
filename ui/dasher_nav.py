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
    """Apakah sidebar sedang terbuka? Default False (hidden, seperti Cursor)."""
    return st.session_state.get(SIDEBAR_OPEN_KEY, False)


def set_sidebar_open(open_: bool) -> None:
    st.session_state[SIDEBAR_OPEN_KEY] = bool(open_)


def render_sidebar_toggle_strip() -> None:
    """Render icon strip kecil di paling kiri layar (seperti Cursor IDE).
    Selalu visible. Klik icon untuk toggle sidebar buka/tutup.
    Icon strip adalah container tipis dengan beberapa icon menu sebagai
    hint visual saja (tidak berfungsi, hanya dekoratif).
    """
    # CSS + HTML untuk icon strip
    st.markdown(
        """
        <style>
        .laris-icon-strip {
            position: fixed;
            top: 0;
            left: 0;
            width: 48px;
            height: 100vh;
            background: linear-gradient(180deg, #1c252e 0%, #141a21 100%);
            z-index: 999995;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 0.6rem;
            gap: 0.4rem;
            box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
        }
        .laris-icon-strip .strip-icon {
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255, 255, 255, 0.65);
            font-size: 1.05rem;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.15s ease, color 0.15s ease;
        }
        .laris-icon-strip .strip-icon:hover {
            background: rgba(124, 58, 237, 0.25);
            color: #fff;
        }
        .laris-icon-strip .strip-icon.active {
            background: linear-gradient(135deg, #7c3aed, #6366f1);
            color: #fff;
        }
        </style>
        <div class="laris-icon-strip">
            <div class="strip-icon active" title="Toggle Sidebar (Ctrl+B)" id="laris_strip_toggle">☰</div>
            <div class="strip-divider" style="width:24px;height:1px;background:rgba(255,255,255,0.1);margin:0.25rem 0;"></div>
            <div class="strip-icon" title="Ruang Komando">🧠</div>
            <div class="strip-icon" title="Ringkasan">📊</div>
            <div class="strip-icon" title="Catat Transaksi">✏️</div>
            <div class="strip-icon" title="Buku Kas">💰</div>
            <div class="strip-icon" title="Laporan KUR">📈</div>
            <div class="strip-icon" title="Gudang">🏬</div>
            <div class="strip-icon" title="Pengaturan">⚙️</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_toggle_button() -> None:
    """Tombol ☰ kecil yang SELALU visible (overlay di konten).
    Klik untuk toggle sidebar buka/tutup. Posisi: top-left, di luar
    icon strip (jadi di kanan icon strip 48px).

    Default: sidebar TERTUTUP (seperti Cursor IDE). User klik tombol
    atau icon strip untuk membuka.
    """
    sidebar_open = is_sidebar_open()
    btn_label = "✕" if sidebar_open else "☰"
    btn_title = "Tutup sidebar" if sidebar_open else "Buka sidebar"

    # Inject tombol via JS agar benar-benar overlay di body
    import streamlit.components.v1 as components

    # Bangun HTML/JS sebagai plain string
    html_js = (
        "<script>"
        "(function() {"
        "  var existing = document.getElementById('laris-sidebar-toggle-btn');"
        "  if (existing) existing.remove();"
        "  var btn = document.createElement('button');"
        "  btn.id = 'laris-sidebar-toggle-btn';"
        "  btn.innerHTML = '" + btn_label + "';"
        "  btn.title = '" + btn_title + "';"
        "  btn.setAttribute('aria-label', btn.title);"
        "  btn.style.cssText = '"
        "    position: fixed !important;"
        "    top: 0.65rem !important;"
        "    left: 60px !important;"
        "    z-index: 999998 !important;"
        "    width: 36px !important;"
        "    height: 36px !important;"
        "    background: linear-gradient(135deg, #7c3aed, #6366f1) !important;"
        "    color: #fff !important;"
        "    border: none !important;"
        "    border-radius: 8px !important;"
        "    font-size: 1rem !important;"
        "    font-weight: 700 !important;"
        "    cursor: pointer !important;"
        "    box-shadow: 0 4px 14px rgba(124, 58, 237, 0.4) !important;"
        "    transition: transform 0.15s ease, box-shadow 0.15s ease !important;"
        "    display: flex !important;"
        "    align-items: center !important;"
        "    justify-content: center !important;"
        "    line-height: 1 !important;"
        "    padding: 0 !important;"
        "    margin: 0 !important;"
        "  ';"
        "  btn.onmouseenter = function() {"
        "    btn.style.transform = 'translateY(-2px)';"
        "    btn.style.boxShadow = '0 6px 20px rgba(124, 58, 237, 0.55)';"
        "  };"
        "  btn.onmouseleave = function() {"
        "    btn.style.transform = 'translateY(0)';"
        "    btn.style.boxShadow = '0 4px 14px rgba(124, 58, 237, 0.4)';"
        "  };"
        "  btn.onclick = function() {"
        "    var evt = new CustomEvent('laris_toggle_sidebar', {bubbles: true});"
        "    document.dispatchEvent(evt);"
        "  };"
        "  document.body.appendChild(btn);"
        "})();"
        "</script>"
    )

    components.html(html_js, height=0)

    # Hidden Streamlit button yang handle click untuk toggle state
    if st.button(
        btn_label,
        key=f"_hidden_toggle_{'close' if sidebar_open else 'open'}",
        help=btn_title,
    ):
        set_sidebar_open(not sidebar_open)
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