"""Landing page marketing laris.AI — dari static/laris-landing.html."""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from brand import APP_NAME, APP_TAGLINE, LANDING_LOGO_HTML, LOGIN_QUERY, DEMO_QUERY

_LANDING_CANDIDATES = (
    Path(__file__).parent / "static" / "laris-landing.html",
    Path(__file__).parent / "Laris-AI.html",
)


def _landing_path():
    for path in _LANDING_CANDIDATES:
        if path.exists():
            return path
    return None


def _render_fallback_landing() -> None:
    """Landing sederhana berbasis Streamlit bila file HTML tidak tersedia."""
    st.markdown(
        f"""
        <div style="text-align:center;padding:3rem 1rem;">
            <h1 style="font-size:2.6rem;margin-bottom:0.5rem;">{APP_NAME}</h1>
            <p style="font-size:1.2rem;color:#94a3b8;">{APP_TAGLINE}</p>
            <p style="max-width:640px;margin:1.5rem auto;color:#cbd5e1;">
                Catat penjualan, stok, dan keuangan UMKM langsung dari WhatsApp dengan AI.
                Laporan KUR otomatis, dashboard real-time, dan asisten Multi-Agent.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("Masuk ke Dashboard", type="primary", use_container_width=True):
            st.session_state["show_login"] = True
            st.rerun()
        if st.button("Lihat Demo Publik", use_container_width=True):
            st.session_state["demo_mode"] = True
            st.rerun()


def _load_landing_html() -> str:
    html = _landing_path().read_text(encoding="utf-8")  # type: ignore[union-attr]

    html = html.replace("<title>Laris.AI —", f"<title>{APP_NAME} —")
    html = html.replace(
        '<i class="fas fa-rocket"></i> Laris.AI',
        f'<i class="fas fa-rocket"></i> {LANDING_LOGO_HTML}',
    )
    html = html.replace("© 2026 Laris.AI —", f"© 2026 {APP_NAME} —")

    demo_link = (
        f'<a href="{DEMO_QUERY}" target="_parent" class="nav-demo">'
        f'<i class="fas fa-eye"></i> Demo</a>'
    )
    dashboard_link = (
        f'<a href="{LOGIN_QUERY}" target="_parent" class="nav-dashboard">'
        f'<i class="fas fa-chart-line"></i> Dashboard</a>'
    )
    html = html.replace(
        '<div class="nav-links">\n                <a href="#fitur">Fitur</a>',
        f'<div class="nav-links">\n                {demo_link}\n                {dashboard_link}\n                <a href="#fitur">Fitur</a>',
    )
    html = html.replace(
        '<div class="mobile-menu" id="mobileMenu">\n            <a href="#fitur" class="mobile-link">',
        f'<div class="mobile-menu" id="mobileMenu">\n            <a href="{DEMO_QUERY}" target="_parent" class="mobile-link">'
        f'<i class="fas fa-eye"></i> Demo</a>\n            <a href="{LOGIN_QUERY}" target="_parent" class="mobile-link">'
        f'<i class="fas fa-chart-line"></i> Dashboard</a>\n            <a href="#fitur" class="mobile-link">',
    )

    nav_dash_css = """
        .nav-demo {
            background: rgba(255,255,255,0.12) !important;
            color: #1e40af !important;
            padding: 10px 18px !important;
            border-radius: 50px !important;
            font-weight: 700 !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 8px !important;
            border: 1px solid rgba(124,58,237,0.25) !important;
        }
        .nav-demo:hover { opacity: 0.92; transform: translateY(-1px); }
        .nav-demo::after { display: none !important; }
        .nav-dashboard {
            background: linear-gradient(135deg, #7c3aed, #1e40af) !important;
            color: #fff !important;
            padding: 10px 20px !important;
            border-radius: 50px !important;
            font-weight: 700 !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 8px !important;
        }
        .nav-dashboard:hover { opacity: 0.92; transform: translateY(-1px); }
        .nav-dashboard::after { display: none !important; }
    """
    html = html.replace("</style>", f"{nav_dash_css}\n    </style>")

    return html


def render_landing():
    """Tampilkan landing page full-screen."""
    if _landing_path() is None:
        _render_fallback_landing()
        return

    st.markdown(
        """
        <style>
            header[data-testid="stHeader"] { display: none !important; }
            .block-container { padding: 0 !important; max-width: 100% !important; }
            iframe { border: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    components.html(_load_landing_html(), height=1000, scrolling=True)
