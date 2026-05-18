"""
WIB CFA — Study Notes page.
Browse course summaries by topic with key formulas and examples.
"""

import streamlit as st

from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
from src.content.study_notes import STUDY_NOTES
from src.styles import inject_styles, render_page_header, render_sidebar_brand, render_sidebar_user

st.set_page_config(page_title="Study Notes — WIB CFA", page_icon="📖", layout="wide", initial_sidebar_state="collapsed")
inject_styles()

with st.sidebar:
    render_sidebar_brand()
    st.divider()
    if st.session_state.get("user_id"):
        render_sidebar_user(get_current_user()["username"])
        st.divider()
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/1_Study.py", label="Study Notes", icon="📖")
    st.page_link("pages/2_Quiz.py", label="Quiz", icon="🎯")
    st.page_link("pages/3_Flashcards.py", label="Flashcards", icon="🃏")
    st.page_link("pages/4_Progress.py", label="Progress", icon="📈")
    st.page_link("pages/5_Exam_Simulator.py", label="Exam Simulator", icon="⏱️")
    st.divider()
    if st.session_state.get("user_id"):
        if st.button("Sign out", use_container_width=True):
            logout()

if not require_auth():
    st.stop()

render_page_header(
    "Study Notes",
    "CFA Level I — Summaries & key formulas",
    help_text="""
**Study Notes**

Concise summaries of all 10 CFA Level I topics — your revision reference.

**How to use:**
- Use the **topic selector** to switch between subjects
- **Content tab**: key concepts, definitions, formulas
- **Exam Tips tab**: what the CFA exam specifically tests on this topic, common traps, high-frequency formulas
- Click **"Practice this topic →"** at the bottom to launch an adaptive quiz focused on the selected topic

**10 topics covered:**
Ethics · Quant Methods · Economics · FSA · Corporate Issuers · Equity · Fixed Income · Derivatives · Alternatives · Portfolio Management
""",
)

# ── Topic selector ────────────────────────────────────────────────────────────

selected_topic = st.selectbox("Choose a topic", CFA_TOPICS, key="study_topic")

# ── Render notes ──────────────────────────────────────────────────────────────

note = STUDY_NOTES.get(selected_topic)

if not note:
    st.warning(f"No study notes available for **{selected_topic}** at the moment.")
    st.stop()

st.markdown(f'<div class="section-header">{selected_topic}</div>', unsafe_allow_html=True)

# Overview
if note.get("overview"):
    st.markdown(note["overview"])

st.markdown("---")

# Tab layout
tab_content, tab_tips = st.tabs(["Content", "Exam Tips"])

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
        st.markdown("#### Key Points")
        for tip in exam_tips:
            st.markdown(
                f'<div class="wib-card" style="padding:0.7rem 1rem;margin-bottom:0.5rem;">'
                f'{tip}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No exam tips available for this topic.")

st.markdown("---")

# CTA: go to quiz pre-filtered on this topic
st.markdown(
    f'<div class="wib-card"><b>Ready to test your knowledge?</b><br>'
    f'Start a quiz on <em>{selected_topic}</em></div>',
    unsafe_allow_html=True,
)
if st.button(f"🎯  Quiz — {selected_topic}", use_container_width=True, type="primary"):
    st.session_state["quiz_preselect_topic"] = selected_topic
    st.switch_page("pages/2_Quiz.py")
