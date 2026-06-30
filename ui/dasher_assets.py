"""Muat CSS Dasher asli ke Streamlit."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).resolve().parent.parent / "static" / "assets" / "dasher"


@st.cache_data(show_spinner=False)
def _read_css(name: str) -> str:
    path = _ASSETS / name
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def inject_dasher_styles(*, login: bool = False) -> None:
    """Bootstrap 5 + Tabler + theme.css Dasher + override Streamlit."""
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.45.0/tabler-icons.min.css" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )
    theme = _read_css("theme.css")
    overrides = _read_css("streamlit-overrides.css")
    login_extra = ""
    if login:
        login_extra = ".stApp { background: var(--ds-body-bg,#f9fafb) !important; }"
    st.markdown(
        f"<style>{theme}\n{overrides}\n{login_extra}</style>",
        unsafe_allow_html=True,
    )
