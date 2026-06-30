import base64
import json
import time

import streamlit as st
from supabase import create_client

from brand import LOGIN_BRAND_HTML
from log_config import get_logger
from ui.laris_theme import inject_login_theme

logger = get_logger(__name__)


def _client():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def _decode_exp(token: str) -> int:
    """Baca klaim exp dari JWT (tanpa verifikasi tanda tangan) untuk cek kedaluwarsa. 0 jika gagal."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return int(data.get("exp", 0))
    except (json.JSONDecodeError, ValueError, IndexError, TypeError):
        return 0


def _clear_session():
    for key in ("user", "access_token", "refresh_token"):
        st.session_state.pop(key, None)


def ensure_valid_session() -> bool:
    """Pastikan sesi login valid. Refresh token bila hampir kedaluwarsa.

    Return True jika user tetap login (valid/berhasil refresh), False jika harus login ulang.
    Hemat: hanya memanggil server saat token mendekati kedaluwarsa (cek exp offline).
    """
    if not st.session_state.get("user"):
        return False
    token = st.session_state.get("access_token")
    if not token:
        # Tanpa JWT, RLS Supabase memblokir baca data — paksa refresh/login ulang.
        refresh = st.session_state.get("refresh_token")
        if not refresh:
            _clear_session()
            return False
        try:
            res = _client().auth.refresh_session(refresh)
            session = getattr(res, "session", None)
            if session and getattr(session, "access_token", None):
                st.session_state["access_token"] = session.access_token
                st.session_state["refresh_token"] = getattr(session, "refresh_token", refresh)
                if getattr(res, "user", None):
                    st.session_state["user"] = _normalize_user(res.user)
                return True
        except (OSError, ValueError, KeyError, AttributeError) as exc:
            logger.warning("ensure_valid_session (no token): %s", exc)
        _clear_session()
        return False

    exp = _decode_exp(token)
    # Masih valid > 60 detik -> tidak perlu panggil server.
    if exp and (exp - time.time()) > 60:
        return True

    refresh = st.session_state.get("refresh_token")
    if not refresh:
        _clear_session()
        return False

    try:
        res = _client().auth.refresh_session(refresh)
        session = getattr(res, "session", None)
        if session and getattr(session, "access_token", None):
            st.session_state["access_token"] = session.access_token
            st.session_state["refresh_token"] = getattr(session, "refresh_token", refresh)
            if getattr(res, "user", None):
                st.session_state["user"] = _normalize_user(res.user)
            return True
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        logger.warning("ensure_valid_session refresh: %s", exc)

    _clear_session()
    return False


def _normalize_user(user):
    if user is None:
        return None
    if isinstance(user, dict):
        return user

    if hasattr(user, "model_dump"):
        try:
            return user.model_dump()
        except Exception:
            pass

    if hasattr(user, "dict"):
        try:
            return user.dict()
        except Exception:
            pass

    normalized = {
        "id": getattr(user, "id", None),
        "email": getattr(user, "email", None),
    }
    nested = getattr(user, "user", None)
    if nested is not None:
        if isinstance(nested, dict):
            normalized["id"] = normalized["id"] or nested.get("id")
            normalized["email"] = normalized["email"] or nested.get("email")
        else:
            normalized["id"] = normalized["id"] or getattr(nested, "id", None)
            normalized["email"] = normalized["email"] or getattr(nested, "email", None)
    return normalized


def show_login_page():
    """Halaman login/register multi-tenant"""
    supabase = _client()
    
    if st.session_state.get("user"):
        st.session_state["show_login"] = False
        return True

    inject_login_theme()
    st.markdown('<div class="laris-dasher-login">', unsafe_allow_html=True)
    logo_uri = ""
    try:
        from ui.components import _logo_data_uri

        logo_uri = _logo_data_uri()
    except Exception:
        pass
    img = f'<img src="{logo_uri}" width="32" height="32" alt="" style="border-radius:8px;" />' if logo_uri else ""

    st.markdown(
        f"""
        <div class="laris-login-brand">
            <div class="d-inline-flex align-items-center gap-2 justify-content-center fs-2 fw-bold mb-3">
                {img}<span>{LOGIN_BRAND_HTML}</span>
            </div>
            <h1 class="fs-3 mb-1 fw-bold" style="color:#1c252e;">Selamat Datang Kembali</h1>
            <p class="text-muted mb-0">Masuk untuk mengakses dashboard bisnis Anda</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("← Kembali ke Beranda", type="secondary"):
        st.session_state.pop("show_login", None)
        st.rerun()

    st.markdown(
        '<div class="card card-lg" style="border:1px solid var(--ds-gray-200);border-radius:1rem;">'
        '<div class="card-body p-4">',
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk", use_container_width=True, type="primary"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if getattr(res, "user", None):
                    st.session_state["user"] = _normalize_user(res.user)
                    st.session_state["access_token"] = getattr(res.session, "access_token", None)
                    st.session_state["refresh_token"] = getattr(res.session, "refresh_token", None)
                    st.session_state["show_login"] = False
                    st.rerun()
                else:
                    st.error("Email atau password salah.")
            except Exception as e:
                st.error(f"Gagal masuk: {str(e)[:100]}")
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.caption("Belum punya akun? Pendaftaran client baru dilakukan oleh Admin laris.AI.")
    st.markdown("</div>", unsafe_allow_html=True)
    return False

def get_current_user():
    return st.session_state.get("user")

def logout():
    # Invalidasi token di server auth, lalu bersihkan sesi lokal.
    try:
        _client().auth.sign_out()
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        logger.warning("logout sign_out: %s", exc)
    _clear_session()
    st.session_state.pop("show_login", None)
    st.rerun()