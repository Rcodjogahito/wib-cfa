"""
WIB CFA — Authentication helpers.
No password required — email + first name is the identifier.

Session persistence: st.context.cookies (read, synchronous) + hidden JS
component (write/clear). Zero new dependencies, works on Streamlit Cloud.

Cookie timing note: st.context.cookies reads the cookies from the HTTP
request that established the WebSocket session. It does NOT update mid-
session on st.rerun(). Writing cookies via JS (st.components.v1.html)
takes effect in the browser immediately, but the updated value is only
visible to st.context.cookies on the NEXT full page load (new HTTP GET).
This means:
  - Login: session_state carries the auth within the session; cookie
    carries it across server restarts / browser tab closures.
  - Logout: we suppress cookie-based restore via a session_state flag
    because st.context.cookies still holds the old cookie value until
    the browser makes a new HTTP request.
"""

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
    """Inject a JS snippet that sets a persistent auth cookie in the browser."""
    _components.html(
        f"""<script>
        document.cookie = "{_COOKIE}={user_id}; max-age={_MAX_AGE}; path=/; SameSite=Strict";
        </script>""",
        height=1,
    )


def _erase_cookie() -> None:
    """Inject a JS snippet that expires the auth cookie."""
    _components.html(
        f"""<script>
        document.cookie = "{_COOKIE}=; max-age=0; path=/; SameSite=Strict";
        </script>""",
        height=1,
    )


def _read_cookie() -> str | None:
    """Read the auth cookie synchronously from the HTTP request context."""
    try:
        return st.context.cookies.get(_COOKIE)
    except Exception:
        return None


# ── Session helpers ───────────────────────────────────────────────────────────

def _load_session(user: dict) -> None:
    st.session_state["user_id"] = user["id"]
    st.session_state["user_email"] = user["email"]
    st.session_state["user_first_name"] = user["first_name"]
    st.session_state["diagnostic_done"] = bool(user.get("diagnostic_done", False))
    st.session_state["diagnostic_score"] = user.get("diagnostic_score")


def _try_restore_from_cookie() -> bool:
    """Check browser cookie and restore session if valid. Returns True if restored.

    Skips restore if the user explicitly logged out this session — needed because
    st.context.cookies still holds the old HTTP-request value after logout until
    the browser makes a new GET request.
    """
    uid = _read_cookie()
    if not uid:
        return False

    # Logout guard: if this uid was explicitly logged out in this session,
    # don't restore it (the JS erase hasn't been seen by st.context.cookies yet).
    if uid == st.session_state.get("_logged_out_uid"):
        return False

    db = get_db()
    user = db.get_user_by_id(uid)
    if not user:
        return False
    _load_session(user)
    _write_cookie(uid)  # reset 90-day timer on every successful restore
    return True


# ── Public API ────────────────────────────────────────────────────────────────

def require_auth() -> bool:
    """Return True if authenticated; show login form and return False otherwise.

    Check order:
    1. session_state (fast path — already authenticated in this server process)
    2. browser cookie (auto-restore after server restart / tab refresh)
    3. Show login form
    """
    if st.session_state.get("user_id"):
        return True
    if _try_restore_from_cookie():
        return True
    _render_login_form()
    return False


def _render_login_form() -> None:
    st.markdown(
        """
        <div style="max-width:440px; margin:3rem auto;">
            <div style="text-align:center; margin-bottom:2rem;">
                <span style="font-family:'Playfair Display',serif; font-size:3rem;
                             font-weight:700; color:#0B2545; letter-spacing:3px;">WIB</span><br>
                <span style="color:#555; font-size:1rem;">Who Wants to Be an Investment Banker?</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        st.subheader("Sign in / Register")
        st.caption("Enter your email and first name. No password required.")
        email = st.text_input("Email address", placeholder="your@email.com")
        first_name = st.text_input("First name", placeholder="Alex")
        submitted = st.form_submit_button("Enter WIB", use_container_width=True)

    if submitted:
        if not email or "@" not in email:
            st.error("Please enter a valid email address.")
            return
        if not first_name.strip():
            st.error("Please enter your first name.")
            return
        db = get_db()
        user = db.get_or_create_user(email.strip().lower(), first_name.strip())
        _load_session(user)
        st.session_state.pop("_logged_out_uid", None)  # clear any prior logout guard
        _write_cookie(user["id"])  # persist across server restarts
        st.rerun()


def logout() -> None:
    uid = st.session_state.get("user_id", "")
    _erase_cookie()
    for key in ["user_id", "user_email", "user_first_name", "diagnostic_done", "diagnostic_score"]:
        st.session_state.pop(key, None)
    # Prevent _try_restore_from_cookie from immediately re-logging in using
    # the stale st.context.cookies value (which won't reflect the JS erase
    # until the browser makes a new HTTP request).
    if uid:
        st.session_state["_logged_out_uid"] = uid
    st.rerun()


def get_current_user() -> dict:
    return {
        "id": st.session_state.get("user_id"),
        "email": st.session_state.get("user_email"),
        "first_name": st.session_state.get("user_first_name"),
        "diagnostic_done": st.session_state.get("diagnostic_done", False),
        "diagnostic_score": st.session_state.get("diagnostic_score"),
    }
