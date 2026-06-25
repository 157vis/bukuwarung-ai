import streamlit as st
from supabase import create_client
from brand import LOGIN_BRAND_HTML


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
    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )
    
    if st.session_state.get("user"):
        st.session_state["show_login"] = False
        return True

    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital@0;1&family=Caveat:wght@400;600&display=swap" rel="stylesheet">
    <style>
        .stApp { background: #f8fafc; }
        .block-container { max-width: 480px; padding-top: 3rem; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:2rem;">
        <h1 style="font-family:'Fraunces',serif; font-style:italic;">{LOGIN_BRAND_HTML}</h1>
        <p style="font-family:'Caveat',cursive; font-size:1.3rem; color:#8B5A3C;">Masuk untuk mengakses dashboard bisnis Anda</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← Kembali ke Beranda", type="secondary"):
        st.session_state.pop("show_login", None)
        st.rerun()
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if getattr(res, "user", None):
                    st.session_state["user"] = _normalize_user(res.user)
                    st.session_state["access_token"] = getattr(res.session, "access_token", None)
                    st.session_state["show_login"] = False
                    st.rerun()
                else:
                    st.error("Email atau password salah.")
            except Exception as e:
                st.error(f"Gagal masuk: {str(e)[:100]}")

    st.caption("Belum punya akun? Pendaftaran client baru dilakukan oleh Admin Laris.AI.")
    return False

def get_current_user():
    return st.session_state.get("user")

def logout():
    st.session_state.pop("user", None)
    st.session_state.pop("access_token", None)
    st.session_state.pop("show_login", None)
    st.rerun()