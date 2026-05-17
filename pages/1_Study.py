"""
WIB CFA — Study Notes page.
Browse course summaries by topic with key formulas and examples.
"""

import streamlit as st

from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
from src.content.study_notes import STUDY_NOTES
from src.styles import inject_styles, render_page_header, render_sidebar_brand

st.set_page_config(page_title="Study Notes — WIB CFA", page_icon="📖", layout="wide", initial_sidebar_state="collapsed")
inject_styles()

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
    st.page_link("streamlit_app.py", label="Accueil", icon="🏠")
    st.page_link("pages/1_Study.py", label="Fiches de cours", icon="📖")
    st.page_link("pages/2_Quiz.py", label="Quiz", icon="🎯")
    st.page_link("pages/3_Flashcards.py", label="Flashcards", icon="🃏")
    st.page_link("pages/4_Progress.py", label="Progression", icon="📈")
    st.page_link("pages/5_Exam_Simulator.py", label="Simulateur d'examen", icon="⏱️")
    st.divider()
    if st.session_state.get("user_id"):
        if st.button("Déconnexion", use_container_width=True):
            logout()

if not require_auth():
    st.stop()

render_page_header("Fiches de cours", "CFA Niveau I — Résumés & formules clés")

# ── Topic selector ────────────────────────────────────────────────────────────

selected_topic = st.selectbox("Choisir un topic", CFA_TOPICS, key="study_topic")

# ── Render notes ──────────────────────────────────────────────────────────────

note = STUDY_NOTES.get(selected_topic)

if not note:
    st.warning(f"Aucune fiche disponible pour **{selected_topic}** pour le moment.")
    st.stop()

st.markdown(f'<div class="section-header">{selected_topic}</div>', unsafe_allow_html=True)

# Overview
if note.get("overview"):
    st.markdown(note["overview"])

st.markdown("---")

# Tab layout
tab_content, tab_tips = st.tabs(["Contenu", "Conseils d'examen"])

with tab_content:
    for section in note.get("sections", []):
        st.markdown(f"### {section['title']}")
        body = section.get("content") or section.get("body", "")
        st.markdown(body)
        if section.get("example"):
            with st.expander("Exemple"):
                st.markdown(section["example"])
        st.markdown("")

with tab_tips:
    exam_tips = note.get("exam_tips") or note.get("key_points", [])
    if exam_tips:
        st.markdown("#### Points clés")
        for tip in exam_tips:
            st.markdown(
                f'<div class="wib-card" style="padding:0.7rem 1rem;margin-bottom:0.5rem;">'
                f'{tip}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Aucun exam tip disponible pour ce topic.")

st.markdown("---")

# CTA: go to quiz pre-filtered on this topic
st.markdown(
    f'<div class="wib-card"><b>Prêt à tester vos connaissances ?</b><br>'
    f'Lancez un quiz sur <em>{selected_topic}</em></div>',
    unsafe_allow_html=True,
)
if st.button(f"🎯  Quiz — {selected_topic}", use_container_width=True, type="primary"):
    st.session_state["quiz_preselect_topic"] = selected_topic
    st.switch_page("pages/2_Quiz.py")
