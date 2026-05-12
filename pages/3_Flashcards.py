"""
WIB CFA — Flashcards page.
Topic filter, flip animation, Leitner scoring (knew it / study more).
"""

import random

import streamlit as st

from src.auth import CFA_TOPICS, require_auth
from src.database import get_db
from src.styles import inject_styles, render_hero

st.set_page_config(page_title="Flashcards — WIB CFA", page_icon="🃏", layout="wide")
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

db = get_db()
state = st.session_state

render_hero("Flashcards")

# ── Setup ─────────────────────────────────────────────────────────────────────

col1, col2, col3 = st.columns([2, 2, 2])
with col1:
    topic_filter = st.selectbox("Topic", ["All"] + CFA_TOPICS, key="fc_topic")
with col2:
    mode = st.selectbox("Mode", ["Révision libre", "Mode Leitner (adaptatif)"], key="fc_mode")
with col3:
    if st.button("Nouvelle session", use_container_width=True):
        for k in ["fc_cards", "fc_idx", "fc_flipped", "fc_knew", "fc_study"]:
            state.pop(k, None)
        st.rerun()

# Load cards if needed
if "fc_cards" not in state:
    topic = None if topic_filter == "All" else topic_filter
    cards = db.get_flashcards(topic=topic)
    if not cards:
        st.warning("Aucune flashcard disponible.")
        st.stop()
    if mode == "Mode Leitner (adaptatif)":
        # Put "study more" cards first if tracked
        study_ids = set(state.get("fc_study_ids", []))
        priority = [c for c in cards if c["id"] in study_ids]
        rest = [c for c in cards if c["id"] not in study_ids]
        random.shuffle(priority)
        random.shuffle(rest)
        cards = priority + rest
    else:
        random.shuffle(cards)
    state["fc_cards"] = cards
    state["fc_idx"] = 0
    state["fc_flipped"] = False
    state["fc_knew"] = 0
    state["fc_study"] = 0

cards = state["fc_cards"]
idx = state["fc_idx"]
total = len(cards)

if idx >= total:
    # Session complete
    knew = state["fc_knew"]
    study = state["fc_study"]
    pct = round(knew / total * 100) if total else 0
    st.markdown(
        f'<div class="pass-banner">Session terminée — {pct}% ({knew}/{total} su)</div>'
        if pct >= 70 else
        f'<div class="fail-banner">Session terminée — {pct}% ({knew}/{total} su)</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**{knew}** cartes sues · **{study}** à retravailler")
    if st.button("Recommencer", use_container_width=True):
        for k in ["fc_cards", "fc_idx", "fc_flipped", "fc_knew", "fc_study"]:
            state.pop(k, None)
        st.rerun()
    st.stop()

card = cards[idx]
flipped = state["fc_flipped"]

st.progress(idx / total, text=f"Carte {idx + 1} / {total}")
st.markdown(f'<span class="topic-badge">{card["topic"]}</span>', unsafe_allow_html=True)
st.markdown("")

# ── Card display ──────────────────────────────────────────────────────────────

if not flipped:
    st.markdown(
        f'<div class="flashcard-front">'
        f'<div><div class="concept">{card["concept_en"]}</div>'
        f'<div style="margin-top:0.8rem;color:rgba(255,255,255,0.65);font-size:0.9rem;">'
        f'Cliquez pour révéler la définition</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Révéler", use_container_width=True):
        state["fc_flipped"] = True
        st.rerun()
else:
    st.markdown(
        f'<div class="flashcard-back">'
        f'<div style="font-size:1.2rem;font-weight:700;color:#0B2545;margin-bottom:0.8rem;">'
        f'{card["concept_en"]}</div>'
        f'<div style="margin-bottom:0.6rem;"><b>[EN]</b> {card["definition_en"]}</div>'
        f'<div style="color:#555;"><b>[FR]</b> {card.get("definition_fr", "") or card["definition_en"]}</div>'
        + (f'<div style="margin-top:0.8rem;color:#1A7F4B;font-style:italic;">'
           f'<b>Example:</b> {card["example_en"]}</div>' if card.get("example_en") else "")
        + (f'<div class="formula-box">{card["formula"]}</div>' if card.get("formula") else "")
        + f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    col_knew, col_study = st.columns(2)
    if col_knew.button("Je savais", use_container_width=True):
        state["fc_knew"] += 1
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        # Remove from study-more list if present
        study_ids = set(state.get("fc_study_ids", []))
        study_ids.discard(card["id"])
        state["fc_study_ids"] = list(study_ids)
        st.rerun()
    if col_study.button("À retravailler", use_container_width=True):
        state["fc_study"] += 1
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        # Mark card for Leitner priority
        study_ids = set(state.get("fc_study_ids", []))
        study_ids.add(card["id"])
        state["fc_study_ids"] = list(study_ids)
        st.rerun()

# ── Stats bar ─────────────────────────────────────────────────────────────────
st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric("Sues", state["fc_knew"])
c2.metric("À retravailler", state["fc_study"])
c3.metric("Restantes", total - idx)
