"""
WIB CFA — Flashcards page.
Topic filter, flip animation, Leitner scoring (knew it / study more).
"""

import random
import time

import streamlit as st

from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
from src.database import get_db
from src.styles import inject_styles, render_page_header, render_sidebar_brand

st.set_page_config(page_title="Flashcards — WIB CFA", page_icon="🃏", layout="wide", initial_sidebar_state="collapsed")
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

user = get_current_user()
db = get_db()
state = st.session_state

render_page_header("Flashcards", "Leitner spaced-repetition system")

# ── Setup ─────────────────────────────────────────────────────────────────────

col1, col2 = st.columns([1, 1])
with col1:
    topic_filter = st.selectbox("Topic", ["All"] + CFA_TOPICS, key="fc_topic")
with col2:
    mode = st.selectbox("Mode", ["Révision libre", "Mode Leitner (adaptatif)"], key="fc_mode")
st.caption("Les changements de topic/mode s'appliquent à la prochaine session.")

if st.button("Nouvelle session", use_container_width=True, type="secondary"):
    for k in ["fc_cards", "fc_idx", "fc_flipped", "fc_knew", "fc_study",
              "fc_saved", "fc_session_start", "fc_topic_saved", "fc_outcomes"]:
        state.pop(k, None)
    st.rerun()

# Load Leitner state from DB if not already in session
if "fc_study_ids" not in state:
    state["fc_study_ids"] = db.load_leitner_ids(user["id"])

# Load cards if needed
if "fc_cards" not in state:
    state["fc_session_start"] = time.time()
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
    state["fc_outcomes"] = {}  # {card_id: True/False} for this session

cards = state["fc_cards"]
idx = state["fc_idx"]
total = len(cards)

if idx >= total:
    # Session complete — save to DB once
    knew = state["fc_knew"]
    study = state["fc_study"]
    pct = round(knew / total * 100) if total else 0

    if not state.get("fc_saved"):
        duration = int(time.time() - state.get("fc_session_start", time.time()))
        outcomes = state.get("fc_outcomes", {})
        topic_results: dict = {}
        for c in cards:
            t = c["topic"]
            topic_results.setdefault(t, {"correct": 0, "total": 0})
            topic_results[t]["total"] += 1
            if outcomes.get(c["id"]) is True:
                topic_results[t]["correct"] += 1

        domain_scores = {t: round(v["correct"] / v["total"] * 100, 1)
                         for t, v in topic_results.items()}
        fc_topic = state.get("fc_topic_saved", "All")
        db.save_session(
            user_id=user["id"],
            session_type="flashcard",
            topic=fc_topic,
            total=total,
            correct=knew,
            duration_sec=duration,
            domain_scores=domain_scores,
        )
        for t, v in topic_results.items():
            db.update_progress(user["id"], t, v["correct"], v["total"])
        state["fc_saved"] = True

    st.markdown(
        f'<div class="pass-banner">Session terminée — {pct}% ({knew}/{total} su)</div>'
        if pct >= 70 else
        f'<div class="fail-banner">Session terminée — {pct}% ({knew}/{total} su)</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**{knew}** cartes sues · **{study}** à retravailler")
    btn1, btn2 = st.columns(2)
    if btn1.button("Recommencer", use_container_width=True):
        for k in ["fc_cards", "fc_idx", "fc_flipped", "fc_knew", "fc_study",
                  "fc_saved", "fc_session_start", "fc_topic_saved", "fc_outcomes"]:
            state.pop(k, None)
        st.rerun()
    if btn2.button("Voir la progression", use_container_width=True):
        st.switch_page("pages/4_Progress.py")
    st.stop()

card = cards[idx]
flipped = state["fc_flipped"]

# Track the topic filter used for this session (for save_session)
state["fc_topic_saved"] = topic_filter

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
    fc1, fc2 = st.columns([3, 1])
    if fc1.button("Révéler", use_container_width=True):
        state["fc_flipped"] = True
        st.rerun()
    if fc2.button("Passer →", use_container_width=True):
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        st.rerun()
else:
    st.markdown(
        f'<div class="flashcard-back">'
        f'<div style="font-size:1.2rem;font-weight:700;color:#0B2545;margin-bottom:0.8rem;">'
        f'{card["concept_en"]}</div>'
        f'<div style="margin-bottom:0.6rem;">{"<b>[EN]</b> " if card.get("definition_fr") else ""}{card["definition_en"]}</div>'
        + (f'<div style="color:#555;"><b>[FR]</b> {card["definition_fr"]}</div>' if card.get("definition_fr") else "")
        + (f'<div style="margin-top:0.8rem;color:#1A7F4B;font-style:italic;">'
           f'<b>Example:</b> {card["example_en"]}</div>' if card.get("example_en") else "")
        + (f'<div class="formula-box">{card["formula"]}</div>' if card.get("formula") else "")
        + f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    col_knew, col_study, col_skip = st.columns(3)
    if col_knew.button("Je savais", use_container_width=True):
        state["fc_knew"] += 1
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        state.setdefault("fc_outcomes", {})[card["id"]] = True
        study_ids = set(state.get("fc_study_ids", []))
        study_ids.discard(card["id"])
        state["fc_study_ids"] = list(study_ids)
        db.save_leitner_ids(user["id"], state["fc_study_ids"])
        st.rerun()
    if col_study.button("À retravailler", use_container_width=True):
        state["fc_study"] += 1
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        state.setdefault("fc_outcomes", {})[card["id"]] = False
        study_ids = set(state.get("fc_study_ids", []))
        study_ids.add(card["id"])
        state["fc_study_ids"] = list(study_ids)
        db.save_leitner_ids(user["id"], state["fc_study_ids"])
        st.rerun()
    if col_skip.button("Passer →", use_container_width=True):
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        st.rerun()

# ── Stats bar ─────────────────────────────────────────────────────────────────
st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric("Sues", state["fc_knew"])
c2.metric("À retravailler", state["fc_study"])
c3.metric("Restantes", total - idx)
