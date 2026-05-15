"""
WIB CFA — Admin panel. Access restricted.
"""

import streamlit as st

st.set_page_config(page_title="WIB Admin", page_icon="📊", layout="wide")

import pandas as pd
from datetime import datetime

from src.auth import get_current_user, require_auth
from src.database import get_db
from src.styles import inject_styles, metric_card, render_page_header, render_sidebar_brand

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
    render_sidebar_brand()
    st.divider()
    if st.session_state.get("user_id"):
        st.markdown(
            f'<div style="font-size:0.82rem;font-weight:600;color:rgba(255,255,255,0.85);'
            f'letter-spacing:0.03em;">{get_current_user()["username"]}</div>',
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
    st.divider()
    if st.session_state.get("user_id"):
        from src.auth import logout
        if st.button("Sign out", use_container_width=True):
            logout()

# ── Content ───────────────────────────────────────────────────────────────────

render_page_header("Administration", "Platform analytics — restricted access")

import traceback as _tb
try:
    users = db.get_all_users()
except Exception as _e:
    st.error(f"**Erreur get_all_users() — {type(_e).__name__}:** `{_e}`")
    st.code(_tb.format_exc())
    st.stop()
total = len(users)

diag_done = sum(1 for u in users if u.get("diagnostic_done"))
with_activity = sum(1 for u in users if u.get("session_count", 0) > 0)

# ── User metrics ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Utilisateurs</div>', unsafe_allow_html=True)
cols = st.columns(3)
cols[0].markdown(metric_card(str(total), "Utilisateurs inscrits"), unsafe_allow_html=True)
cols[1].markdown(metric_card(str(diag_done), "Diagnostics complétés"), unsafe_allow_html=True)
cols[2].markdown(metric_card(str(with_activity), "Utilisateurs actifs"), unsafe_allow_html=True)

# ── Question bank metrics ─────────────────────────────────────────────────────
st.markdown('<div class="section-header" style="margin-top:1.5rem;">Banque de questions</div>',
            unsafe_allow_html=True)
try:
    q_stats = db.get_question_stats()
    q_total = q_stats["total"]
    by_src  = q_stats["by_source"]
    src_cols = st.columns(max(len(by_src) + 1, 2))
    src_cols[0].markdown(metric_card(f"{q_total:,}", "Total questions"), unsafe_allow_html=True)
    for i, (src, cnt) in enumerate(sorted(by_src.items()), start=1):
        if i < len(src_cols):
            src_cols[i].markdown(metric_card(f"{cnt:,}", src), unsafe_allow_html=True)
except Exception:
    st.info("Stats questions non disponibles.")

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
