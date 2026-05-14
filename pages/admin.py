"""
WIB CFA — Admin panel. Access restricted.
"""

import streamlit as st

st.set_page_config(page_title="WIB Admin", page_icon="📊", layout="wide")

import pandas as pd
from datetime import datetime

from src.auth import get_current_user, require_auth
from src.database import get_db
from src.styles import inject_styles, metric_card, render_hero

inject_styles()

_ADMIN_EMAIL = "sam"

# ── Auth gate — silent rejection for non-admin ────────────────────────────────

if not require_auth():
    st.stop()

user = get_current_user()
if user.get("email") != _ADMIN_EMAIL:
    st.stop()

db = get_db()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="font-family:\'Playfair Display\',serif;font-size:1.4rem;'
        'font-weight:700;color:#C9A84C;">WIB</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/1_Study.py", label="Study Notes", icon="📖")
    st.page_link("pages/2_Quiz.py", label="Quiz", icon="🎯")
    st.page_link("pages/3_Flashcards.py", label="Flashcards", icon="🃏")
    st.page_link("pages/4_Progress.py", label="Progress", icon="📈")
    st.page_link("pages/5_Exam_Simulator.py", label="Exam Simulator", icon="⏱️")
    st.divider()
    st.page_link("pages/admin.py", label="Admin", icon="🔐")

# ── Content ───────────────────────────────────────────────────────────────────

render_hero("Administration")

users = db.get_all_users()
total = len(users)

diag_done = sum(1 for u in users if u.get("diagnostic_done"))
with_activity = sum(1 for u in users if u.get("session_count", 0) > 0)

cols = st.columns(3)
cols[0].markdown(metric_card(str(total), "Utilisateurs inscrits"), unsafe_allow_html=True)
cols[1].markdown(metric_card(str(diag_done), "Diagnostics complétés"), unsafe_allow_html=True)
cols[2].markdown(metric_card(str(with_activity), "Utilisateurs actifs"), unsafe_allow_html=True)

st.divider()
st.subheader("Liste des utilisateurs")

rows = []
for u in users:
    created = u.get("created_at") or ""
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            created = dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    last_active = u.get("last_active") or ""
    if last_active:
        try:
            dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            last_active = dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    score = u.get("diagnostic_score")
    score_str = f"{score:.0f}%" if score is not None else "—"

    rows.append({
        "Pseudo": u.get("first_name") or u.get("email", ""),
        "Inscrit le": created or "—",
        "Diagnostic": "Oui" if u.get("diagnostic_done") else "Non",
        "Score diag.": score_str,
        "Sessions": u.get("session_count", 0),
        "Dernière activité": last_active or "—",
    })

df = pd.DataFrame(rows)
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Sessions": st.column_config.NumberColumn(format="%d"),
    },
)
