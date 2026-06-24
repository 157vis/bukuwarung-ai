"""Landing page marketing laris.AI — dari static/laris-landing.html."""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from brand import APP_NAME, LANDING_LOGO_HTML, LOGIN_QUERY

_LANDING_CANDIDATES = (
    Path(__file__).parent / "static" / "laris-landing.html",
    Path(__file__).parent / "Laris-AI.html",
)


def _landing_path() -> Path:
    for path in _LANDING_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("Landing HTML tidak ditemukan (static/laris-landing.html atau Laris-AI.html)")


def _load_landing_html() -> str:
    html = _landing_path().read_text(encoding="utf-8")

    html = html.replace("<title>Laris.AI —", f"<title>{APP_NAME} —")
    html = html.replace(
        '<i class="fas fa-rocket"></i> Laris.AI',
        f'<i class="fas fa-rocket"></i> {LANDING_LOGO_HTML}',
    )
    html = html.replace("© 2026 Laris.AI —", f"© 2026 {APP_NAME} —")

    dashboard_link = (
        f'<a href="{LOGIN_QUERY}" target="_parent" class="nav-dashboard">'
        f'<i class="fas fa-chart-line"></i> Dashboard</a>'
    )
    html = html.replace(
        '<div class="nav-links">\n                <a href="#fitur">Fitur</a>',
        f'<div class="nav-links">\n                {dashboard_link}\n                <a href="#fitur">Fitur</a>',
    )
    html = html.replace(
        '<div class="mobile-menu" id="mobileMenu">\n            <a href="#fitur"',
        f'<div class="mobile-menu" id="mobileMenu">\n            <a href="{LOGIN_QUERY}" target="_parent" class="mobile-link">'
        f'<i class="fas fa-chart-line"></i> Dashboard</a>\n            <a href="#fitur"',
    )

    # Agent Admin = modul buku kas di dashboard
    html = html.replace(
        "<h3>Agent Admin \"Dewi\" 🔵</h3>\n                            <div class=\"role\">Admin & Laporan</div>",
        "<h3>Agent Admin \"Dewi\" 🔵</h3>\n                            <div class=\"role\">Buku Kas & Laporan KUR</div>",
    )
    html = html.replace(
        "<li><i class=\"fas fa-check-circle\"></i> Rekap orderan harian</li>",
        "<li><i class=\"fas fa-check-circle\"></i> Buku kas & catat transaksi AI</li>",
    )
    html = html.replace(
        "<li><i class=\"fas fa-check-circle\"></i> Dashboard sederhana</li>",
        f'<li><i class="fas fa-check-circle"></i> Dashboard buku kas (<a href="{LOGIN_QUERY}" target="_parent" style="color:#1e40af;font-weight:700">masuk</a>)</li>',
    )
    html = html.replace(
        "<li><i class=\"fas fa-check-circle\"></i> Dashboard lengkap + analytics</li>",
        f'<li><i class="fas fa-check-circle"></i> Dashboard lengkap + Laris Score (<a href="{LOGIN_QUERY}" target="_parent" style="color:#1e40af;font-weight:700">masuk</a>)</li>',
    )

    nav_dash_css = """
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
    components.html(_load_landing_html(), height=7400, scrolling=True)
