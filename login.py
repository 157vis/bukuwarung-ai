import base64
import json
import time

import streamlit as st
from supabase import create_client

from brand import LOGIN_BRAND_HTML
from config_runtime import require_secret
from log_config import get_logger
from ui.laris_theme import inject_login_theme

logger = get_logger(__name__)


def _client():
    return create_client(require_secret("SUPABASE_URL"), require_secret("SUPABASE_KEY"))


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


def _render_html(html_block: str) -> None:
    """Render blok HTML mentah via st.html() agar tidak bocor jadi teks."""
    try:
        st.html(html_block)
        return
    except AttributeError:
        pass
    st.markdown(html_block, unsafe_allow_html=True)


def show_login_page():
    """Halaman login/register multi-tenant"""
    supabase = _client()

    if st.session_state.get("user"):
        st.session_state["show_login"] = False
        return True

    inject_login_theme()
    _render_html('<div class="laris-dasher-login">')
    logo_uri = ""
    try:
        from ui.components import _logo_data_uri

        logo_uri = _logo_data_uri()
    except Exception:
        pass
    img = f'<img src="{logo_uri}" width="32" height="32" alt="" style="border-radius:8px;" />' if logo_uri else ""

    _render_html(
        f"""
        <div class="laris-login-brand">
            <div class="d-inline-flex align-items-center gap-2 justify-content-center fs-2 fw-bold mb-3">
                {img}<span>{LOGIN_BRAND_HTML}</span>
            </div>
            <h1 class="fs-3 mb-1 fw-bold" style="color:#1c252e;">Selamat Datang Kembali</h1>
            <p class="text-muted mb-0">Masuk untuk mengakses dashboard bisnis Anda</p>
        </div>
        """
    )

    # Catatan menarik: 4 tips singkat bergaya kartu agar login terasa ramah.
    _render_html(
        """
        <div class="laris-login-tips mb-4" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.75rem;">
          <div class="laris-login-tip" style="background:#e8f5e9;border:1px solid #c8e6c9;border-radius:0.75rem;padding:0.75rem 1rem;">
            <div style="font-size:1.25rem;line-height:1;">📒</div>
            <div style="font-weight:700;font-size:0.9rem;color:#1c252e;margin-top:0.25rem;">Buku Kas Otomatis</div>
            <div style="font-size:0.78rem;color:#637381;margin-top:0.15rem;">Catat via WA, AI yang merapikan.</div>
          </div>
          <div class="laris-login-tip" style="background:#fff3e0;border:1px solid #ffe0b2;border-radius:0.75rem;padding:0.75rem 1rem;">
            <div style="font-size:1.25rem;line-height:1;">📦</div>
            <div style="font-weight:700;font-size:0.9rem;color:#1c252e;margin-top:0.25rem;">Stok Pintar</div>
            <div style="font-size:0.78rem;color:#637381;margin-top:0.15rem;">Notifikasi + saran restock.</div>
          </div>
          <div class="laris-login-tip" style="background:#e3f2fd;border:1px solid #bbdefb;border-radius:0.75rem;padding:0.75rem 1rem;">
            <div style="font-size:1.25rem;line-height:1;">📊</div>
            <div style="font-weight:700;font-size:0.9rem;color:#1c252e;margin-top:0.25rem;">Laris Score</div>
            <div style="font-size:0.78rem;color:#637381;margin-top:0.15rem;">Kesehatan usaha 0-100, real-time.</div>
          </div>
          <div class="laris-login-tip" style="background:#fce4ec;border:1px solid #f8bbd0;border-radius:0.75rem;padding:0.75rem 1rem;">
            <div style="font-size:1.25rem;line-height:1;">🛡️</div>
            <div style="font-weight:700;font-size:0.9rem;color:#1c252e;margin-top:0.25rem;">Multi-Tenant Aman</div>
            <div style="font-size:0.78rem;color:#637381;margin-top:0.15rem;">Data tiap toko terisolasi RLS.</div>
          </div>
        </div>
        <div class="laris-login-welcome-note mb-3" style="background:linear-gradient(94.82deg,#e8f5e9,#e3f2fd);border-radius:0.75rem;padding:0.85rem 1.15rem;font-size:0.92rem;color:#1c252e;">
          👋 <b>Halo, Owner!</b> Senang bertemu lagi. Dashboard Anda sudah menunggu —
          <span style="color:#007867;font-weight:600;">Laris Score</span>,
          <span style="color:#007867;font-weight:600;">Buku Kas</span>, dan
          <span style="color:#007867;font-weight:600;">Ruang Komando</span> siap dipakai.
        </div>
        """
    )

    if st.button("← Kembali ke Beranda", type="secondary"):
        st.session_state.pop("show_login", None)
        st.rerun()

    _render_html(
        '<div class="card card-lg" style="border:1px solid var(--ds-gray-200);border-radius:1rem;">'
        '<div class="card-body p-4">'
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
    _render_html("</div></div>")
    st.caption("Belum punya akun? Pendaftaran client baru dilakukan oleh Admin laris.AI.")
    _render_html(
        """
        <div class="laris-login-help mt-3" style="background:#fff8e1;border:1px solid #ffe082;border-radius:0.75rem;padding:0.75rem 1rem;font-size:0.9rem;display:flex;align-items:center;gap:0.6rem;">
          <span style="font-size:1.4rem;">💬</span>
          <span style="flex:1;color:#5d4037;">
            <b>Belum terdaftar?</b> Tim kami akan setup akun trial gratis via WhatsApp.
          </span>
          <a href="https://wa.me/6282112826851?text=Halo%20laris.AI%2C%20saya%20belum%20punya%20akun%2C%20mau%20daftar%20trial" target="_blank" rel="noopener" style="background:#25D366;color:#fff;text-decoration:none;padding:0.4rem 0.9rem;border-radius:0.5rem;font-weight:600;white-space:nowrap;">
            <i class="fab fa-whatsapp"></i> Daftar via WA
          </a>
        </div>
        """
    )
    _render_html("</div>")
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