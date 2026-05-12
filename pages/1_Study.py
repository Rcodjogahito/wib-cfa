"""
WIB CFA — Study Notes page.
Browse course summaries by topic with key formulas and examples.
"""

import streamlit as st

from src.auth import CFA_TOPICS, get_current_user, require_auth
from src.content.study_notes import STUDY_NOTES
from src.styles import inject_styles, render_hero

st.set_page_config(page_title="Study Notes — WIB CFA", page_icon="📖", layout="wide")
inject_styles()

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

if not require_auth():
    st.stop()

render_hero("Study Notes")

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
tab_content, tab_tips = st.tabs(["Contenu", "Exam Tips"])

with tab_content:
    for section in note.get("sections", []):
        st.markdown(f"### {section['title']}")
        body = section.get("content") or section.get("body", "")
        st.markdown(body)
        if section.get("example"):
            with st.expander("Example"):
                st.markdown(section["example"])
        st.markdown("")

with tab_tips:
    exam_tips = note.get("exam_tips") or note.get("key_points", [])
    if exam_tips:
        st.markdown("#### Points clés pour l'examen")
        for tip in exam_tips:
            st.markdown(
                f'<div class="wib-card" style="padding:0.7rem 1rem;margin-bottom:0.5rem;">'
                f'{tip}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Aucun exam tip disponible pour ce topic.")

st.markdown("---")

# CTA: go to quiz
st.markdown(
    f'<div class="wib-card"><b>Prêt à tester vos connaissances ?</b><br>'
    f'Lancez un quiz sur <em>{selected_topic}</em></div>',
    unsafe_allow_html=True,
)
st.page_link("pages/2_Quiz.py", label=f"Quiz — {selected_topic}", icon="🎯")
