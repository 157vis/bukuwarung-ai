"""Tema laris.AI — shell visual Dasher (fungsi tetap Streamlit)."""

from __future__ import annotations

from ui.dasher_assets import inject_dasher_styles


def inject_dashboard_theme() -> None:
    inject_dasher_styles(login=False)


def inject_login_theme() -> None:
    inject_dasher_styles(login=True)
