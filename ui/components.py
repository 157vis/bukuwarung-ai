"""Komponen UI — kartu, hero, ikon Dasher-style."""

from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

from brand import APP_NAME, APP_TAGLINE_DASHBOARD


def _render(html_block: str) -> None:
    """Render blok HTML mentah. Pakai ``st.html`` (Streamlit >= 1.32) bila ada
    agar tidak dibungkus <p> oleh Markdown (penyebab tag <div> bocor jadi
    teks di browser). Fallback ke ``st.markdown(unsafe_allow_html=True)``.
    """
    try:
        st.html(html_block)
        return
    except AttributeError:
        pass
    st.markdown(html_block, unsafe_allow_html=True)

_LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "assets" / "dasher" / "logo-icon.svg"

# Ikon per-tone untuk stat_card_row (Tabler Icons)
_TONE_ICON = {
    "success": ("ti-cash", "bg-success-darker text-success-lighter"),
    "warning": ("ti-shopping-cart", "bg-warning-darker text-warning-lighter"),
    "danger": ("ti-arrow-down-right", "bg-danger-darker text-danger-lighter"),
    "info": ("ti-chart-bar", "bg-info-darker text-info-lighter"),
    "primary": ("ti-star", "bg-primary-darker text-primary-lighter"),
    "purple": ("ti-bolt", "bg-primary-darker text-primary-lighter"),
}


def _logo_data_uri() -> str:
    if not _LOGO_PATH.is_file():
        return ""
    raw = _LOGO_PATH.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def sidebar_brand() -> None:
    logo = _logo_data_uri()
    img = (
        f'<img src="{logo}" alt="" width="30" height="30" style="border-radius:8px;" />'
        if logo
        else ""
    )
    _render(
        f"""
        <div class="brand-logo">
            <div class="d-flex align-items-center gap-2">
                {img}
                <span class="fw-bold fs-4 site-logo-text">{html.escape(APP_NAME)}</span>
            </div>
            <small class="text-muted d-block mt-1 site-logo-text">{html.escape(APP_TAGLINE_DASHBOARD)}</small>
        </div>
        """
    )


def hero_welcome(*, user_name: str, subtitle: str | None = None) -> None:
    """Hero card ala Dasher — gradient + sapaan."""
    name = html.escape((user_name or "Bos").split("@")[0].title())
    sub = html.escape(subtitle or APP_TAGLINE_DASHBOARD)
    _render(
        f"""
        <div class="bg-gradient-mixed rounded-3 mb-4 p-4 p-lg-5 d-flex align-items-center justify-content-between flex-wrap gap-3">
            <div>
                <h1 class="fs-2 mb-1 fw-bold" style="color:#1c252e;">👋 Halo, {name}</h1>
                <p class="mb-1" style="color:#1c252e;">{sub}</p>
                <p class="mb-0" style="color:#637381; font-size:0.92rem;">
                    Pantau omzet, stok, dan keputusan AI dari satu tempat.
                </p>
            </div>
            <div class="d-none d-md-block">
                <span class="laris-page-badge" style="background:rgba(255,255,255,0.55);color:#007867;">Live Dashboard</span>
            </div>
        </div>
        """
    )


def stat_card_row(metrics: list[tuple[str, str, str]]) -> None:
    """(label, nilai, tone) — tone: success|warning|danger|info|primary|purple"""
    if not metrics:
        return
    cards = []
    for label, value, tone in metrics:
        icon, klass = _TONE_ICON.get(tone, _TONE_ICON["primary"])
        cards.append(
            f"""
            <div class="col">
              <div class="card card-lg h-100 border-0 shadow-none"
                   style="border:1px solid var(--ds-gray-200); border-radius:1rem;">
                <div class="card-body d-flex flex-column gap-3">
                  <div class="d-flex align-items-center gap-3">
                    <div class="laris-card-icon {klass}">
                      <i class="ti {icon}"></i>
                    </div>
                    <span class="fw-medium text-muted">{html.escape(label)}</span>
                  </div>
                  <div class="fs-3 fw-bold lh-1">{html.escape(value)}</div>
                </div>
              </div>
            </div>
            """
        )
    n = len(metrics)
    html_block = (
        f'<div class="row row-cols-1 row-cols-md-2 row-cols-xl-{n} g-4 mb-4">'
        f'{"".join(cards)}</div>'
    )
    _render(html_block)


def section_card(title: str, subtitle: str = "", icon: str = "") -> None:
    """Header kartu bergaya Dasher."""
    ic = f'<i class="ti {html.escape(icon)} me-2 text-primary"></i>' if icon else ""
    _render(
        f"""
        <div class="card card-lg mb-3" style="border:1px solid var(--ds-gray-200);border-radius:1rem;">
          <div class="card-body pb-2">
            <h4 class="mb-1">{ic}{html.escape(title)}</h4>
            <p class="text-muted mb-0 small">{html.escape(subtitle)}</p>
          </div>
        </div>
        """
    )


def info_pill(text: str, tone: str = "info") -> None:
    bg = {
        "info": "bg-info-subtle text-info-emphasis",
        "success": "bg-success-subtle text-success-emphasis",
        "warning": "bg-warning-subtle text-warning-emphasis",
        "danger": "bg-danger-subtle text-danger-emphasis",
    }.get(tone, "bg-info-subtle text-info-emphasis")
    _render(
        f'<span class="badge {bg} px-3 py-2 rounded-3">{html.escape(text)}</span>'
    )


def empty_state(icon: str, title: str, hint: str = "") -> None:
    hint_html = f'<p class="text-muted">{html.escape(hint)}</p>' if hint else ""
    _render(
        f"""
        <div class="card card-lg text-center py-5"
             style="border:1px dashed var(--ds-gray-300); border-radius:1rem; background:#fcfdfd;">
          <div class="card-body">
            <i class="ti {html.escape(icon)} fs-1 text-muted"></i>
            <h5 class="mt-3">{html.escape(title)}</h5>
            {hint_html}
          </div>
        </div>
        """
    )