"""
WIB CFA — Authentication helpers.
Login with pseudo + last 2 letters of surname — no password required.
The composite key (pseudo + suffix, both lowercased) uniquely identifies a user.

Session persistence: st.context.cookies (read, synchronous) + hidden JS
component (write/clear). Zero new dependencies, works on Streamlit Cloud.

Cookie timing note: st.context.cookies reads the cookies from the HTTP
request that established the WebSocket session. It does NOT update mid-
session on st.rerun(). Writing cookies via JS (st.components.v1.html)
takes effect in the browser immediately, but the updated value is only
visible to st.context.cookies on the NEXT full page load (new HTTP GET).
"""

from __future__ import annotations

import re as _re

import streamlit as st
import streamlit.components.v1 as _components

from src.database import get_db


CFA_TOPICS = [
    "Ethics & Professional Standards",
    "Quantitative Methods",
    "Economics",
    "Financial Statement Analysis",
    "Corporate Issuers",
    "Equity Investments",
    "Fixed Income",
    "Derivatives",
    "Alternative Investments",
    "Portfolio Management",
]

_COOKIE = "wib_uid"
_MAX_AGE = 60 * 60 * 24 * 90  # 90 days


# ── Cookie helpers ────────────────────────────────────────────────────────────

def _write_cookie(user_id: str) -> None:
    _components.html(
        f"""<script>
        document.cookie = "{_COOKIE}={user_id}; max-age={_MAX_AGE}; path=/; SameSite=Strict";
        </script>""",
        height=1,
    )


def _erase_cookie() -> None:
    _components.html(
        f"""<script>
        document.cookie = "{_COOKIE}=; max-age=0; path=/; SameSite=Strict";
        </script>""",
        height=1,
    )


def _read_cookie() -> str | None:
    try:
        return st.context.cookies.get(_COOKIE)
    except Exception:
        return None


# ── Session helpers ───────────────────────────────────────────────────────────

def _load_session(user: dict) -> None:
    st.session_state["user_id"] = user["id"]
    st.session_state["user_email"] = user.get("email", "")
    st.session_state["user_first_name"] = user.get("first_name", "")
    st.session_state["user_username"] = user.get("first_name") or user.get("email", "")
    st.session_state["diagnostic_done"] = bool(user.get("diagnostic_done", False))
    st.session_state["diagnostic_score"] = user.get("diagnostic_score")


def _try_restore_from_cookie() -> bool:
    uid = _read_cookie()
    if not uid:
        return False
    if uid == st.session_state.get("_logged_out_uid"):
        return False
    db = get_db()
    user = db.get_user_by_id(uid)
    if not user:
        return False
    _load_session(user)
    _write_cookie(uid)
    return True


# ── Public API ────────────────────────────────────────────────────────────────

def require_auth() -> bool:
    """Return True if authenticated; show login form and return False otherwise."""
    if st.session_state.get("user_id"):
        return True
    if _try_restore_from_cookie():
        return True
    _render_login_form()
    return False


def _render_login_form() -> None:
    # ── Branding ──────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="max-width:460px;margin:3rem auto 0;">
          <div style="text-align:center;margin-bottom:2.5rem;">
            <span style="font-family:'Cormorant Garamond',Georgia,serif;font-size:3.2rem;
                         font-weight:700;color:#0B2545;letter-spacing:4px;">WIB</span><br>
            <span style="color:#555;font-size:0.95rem;letter-spacing:0.02em;">
              CFA Level 1 — Your personal prep space
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Login form ────────────────────────────────────────────────────────────
    with st.form("login_form", border=True):
        st.markdown(
            '<p style="font-size:1.05rem;font-weight:600;color:#0B2545;margin-bottom:0.2rem;">'
            'Access your space</p>'
            '<p style="font-size:0.82rem;color:#666;margin-top:0;margin-bottom:1rem;">'
            'Your pseudo + the last 2 letters of your surname unlock your personal profile.</p>',
            unsafe_allow_html=True,
        )

        pseudo = st.text_input(
            "Pseudo",
            placeholder="e.g. AlexFinance, JeanDupont…",
            help="3–30 characters, letters / numbers / underscores",
        )
        suffix = st.text_input(
            "Last 2 letters of your surname",
            placeholder='e.g. "nt" for Dupont · "on" for Johnson',
            max_chars=2,
            help="Case-insensitive — only the last 2 letters of your family name",
        )

        submitted = st.form_submit_button(
            "Enter WIB →",
            use_container_width=True,
            type="primary",
        )

    # ── Validation & login ────────────────────────────────────────────────────
    if submitted:
        raw_pseudo = pseudo.strip()
        raw_suffix = suffix.strip()

        # Pseudo validation
        if len(raw_pseudo) < 3:
            st.error("Your pseudo must be at least 3 characters.")
            return
        if len(raw_pseudo) > 30:
            st.error("Your pseudo cannot exceed 30 characters.")
            return
        if not _re.match(r"^[A-Za-z0-9_À-ÿ]+$", raw_pseudo):
            st.error("Your pseudo can only contain letters, numbers and underscores (no spaces).")
            return

        # Suffix validation
        if len(raw_suffix) != 2:
            st.error("Please enter exactly 2 letters from your surname.")
            return
        if not _re.match(r"^[A-Za-zÀ-ÿ]{2}$", raw_suffix):
            st.error("The surname letters must be letters only (no numbers or symbols).")
            return

        # Build composite key (both lowercased)
        composite_key = raw_pseudo.lower() + raw_suffix.lower()
        db = get_db()
        user = db.get_or_create_user(composite_key, raw_pseudo)
        _load_session(user)
        st.session_state.pop("_logged_out_uid", None)
        _write_cookie(user["id"])
        st.rerun()


def logout() -> None:
    uid = st.session_state.get("user_id", "")
    _erase_cookie()
    for key in ["user_id", "user_email", "user_first_name", "user_username",
                "diagnostic_done", "diagnostic_score"]:
        st.session_state.pop(key, None)
    if uid:
        st.session_state["_logged_out_uid"] = uid
    st.rerun()


def get_current_user() -> dict:
    username = (
        st.session_state.get("user_username")
        or st.session_state.get("user_first_name")
        or st.session_state.get("user_email")
        or ""
    )
    return {
        "id": st.session_state.get("user_id"),
        "email": st.session_state.get("user_email"),
        "first_name": username,
        "username": username,
        "diagnostic_done": st.session_state.get("diagnostic_done", False),
        "diagnostic_score": st.session_state.get("diagnostic_score"),
    }
