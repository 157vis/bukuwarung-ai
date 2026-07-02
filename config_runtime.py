"""Runtime config helper for Streamlit + environment fallback.

Railway/Cloudflare deployments often provide secrets via environment variables
instead of `.streamlit/secrets.toml`. This helper keeps both modes working.
"""

from __future__ import annotations

import os

import streamlit as st

try:
    from streamlit.errors import StreamlitSecretNotFoundError
except Exception:  # pragma: no cover - older Streamlit compatibility
    StreamlitSecretNotFoundError = Exception  # type: ignore[assignment]


def get_secret(name: str, default: str | None = None) -> str | None:
    """Read from Streamlit secrets first, then environment variable fallback."""
    value = None
    try:
        value = st.secrets.get(name)
    except (KeyError, FileNotFoundError, StreamlitSecretNotFoundError, AttributeError):
        value = None
    if value not in (None, ""):
        return str(value)
    env_value = os.getenv(name)
    if env_value not in (None, ""):
        return env_value
    return default


def require_secret(name: str) -> str:
    """Read required secret; raise clear error if missing."""
    value = get_secret(name)
    if value in (None, ""):
        raise RuntimeError(
            f"Missing required config: {name}. Set it in Streamlit secrets or environment variables."
        )
    return value
