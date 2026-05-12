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

# Tab layout: EN content | FR content
tab_en, tab_fr, tab_formulas = st.tabs(["Content (EN)", "Résumé (FR)", "Formulas & Key Points"])

with tab_en:
    for section in note.get("sections_en", []):
        st.markdown(f"### {section['title']}")
        st.markdown(section["body"])
        if section.get("example"):
            with st.expander("Example"):
                st.markdown(section["example"])

with tab_fr:
    for section in note.get("sections_fr", []):
        st.markdown(f"### {section['title']}")
        st.markdown(section["body"])
        if section.get("exemple"):
            with st.expander("Exemple"):
                st.markdown(section["exemple"])

with tab_formulas:
    formulas = note.get("formulas", [])
    if formulas:
        for f in formulas:
            st.markdown(f"**{f['name']}**")
            st.markdown(
                f'<div class="formula-box">{f["formula"]}</div>',
                unsafe_allow_html=True,
            )
            if f.get("note"):
                st.caption(f["note"])
            st.markdown("")
    else:
        st.info("Pas de formules spécifiques pour ce topic.")

    key_points = note.get("key_points", [])
    if key_points:
        st.markdown("---")
        st.markdown("#### Key Points to Remember")
        for pt in key_points:
            st.markdown(f"- {pt}")

st.markdown("---")

# CTA: go to quiz
st.markdown(
    f'<div class="wib-card"><b>Prêt à tester vos connaissances ?</b><br>'
    f'Lancez un quiz sur <em>{selected_topic}</em></div>',
    unsafe_allow_html=True,
)
st.page_link("pages/2_Quiz.py", label=f"Quiz — {selected_topic}", icon="🎯")
