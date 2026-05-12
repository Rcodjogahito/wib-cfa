"""
WIB CFA — Authentication helpers.
No password required — email + first name is the identifier.
"""

import streamlit as st
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


def require_auth() -> bool:
    """Return True if user is authenticated; show login form and return False otherwise."""
    if st.session_state.get("user_id"):
        return True
    _render_login_form()
    return False


def _render_login_form():
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
        st.session_state["user_id"] = user["id"]
        st.session_state["user_email"] = user["email"]
        st.session_state["user_first_name"] = user["first_name"]
        st.session_state["diagnostic_done"] = bool(user.get("diagnostic_done", False))
        st.session_state["diagnostic_score"] = user.get("diagnostic_score")
        st.rerun()


def logout():
    for key in ["user_id", "user_email", "user_first_name", "diagnostic_done", "diagnostic_score"]:
        st.session_state.pop(key, None)
    st.rerun()


def get_current_user() -> dict:
    return {
        "id": st.session_state.get("user_id"),
        "email": st.session_state.get("user_email"),
        "first_name": st.session_state.get("user_first_name"),
        "diagnostic_done": st.session_state.get("diagnostic_done", False),
        "diagnostic_score": st.session_state.get("diagnostic_score"),
    }
