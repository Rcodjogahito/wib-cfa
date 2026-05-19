"""
WIB CFA — Flashcards with true 5-box Leitner spaced repetition.
Box intervals: 1→now  2→+1d  3→+3d  4→+7d  5→+14d
"""

import random
import time
from datetime import datetime, timezone

import streamlit as st

from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
from src.database import get_db
from src.styles import inject_styles, render_page_header, render_sidebar_brand, render_sidebar_user

st.set_page_config(
    page_title="Flashcards — WIB CFA",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="expanded",
)
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

user = get_current_user()
db = get_db()
state = st.session_state

render_page_header(
    "Flashcards",
    "Leitner spaced repetition — 5 boxes",
    help_text="""
**Flashcards — Leitner Spaced Repetition**

Each card is sorted into one of 5 boxes based on how well you know it:

| Box | Colour | Next review |
|---|---|---|
| Box 1 | 🔴 | Every session (new / forgotten) |
| Box 2 | 🟠 | +1 day |
| Box 3 | 🟡 | +3 days |
| Box 4 | 🟢 | +7 days |
| Box 5 | 🟩 | +14 days (mastered) |

**Modes:**
- **Leitner mode** *(recommended)*: shows only cards due today — the most efficient way to study
- **Free review**: review all cards regardless of schedule

**Session flow:**
1. Read the concept on the front
2. Click **Reveal** to see the definition + example
3. **I knew it ✓** → card moves up one box
4. **Study more** → card goes back to Box 1
5. **Skip →** → skip without recording an answer

The header shows **●●●○○** — filled dots = current box level.
""",
)

_BOX_LABELS = {1: "Box 1 — Daily", 2: "Box 2 — 1 day", 3: "Box 3 — 3 days",
               4: "Box 4 — 7 days", 5: "Box 5 — 14 days (mastered)"}
_BOX_COLOR  = {1: "#C0392B", 2: "#E67E22", 3: "#F1C40F",
               4: "#27AE60", 5: "#1A7F4B"}


def _box_indicator(box: int) -> str:
    filled = "●" * box
    empty  = "○" * (5 - box)
    color  = _BOX_COLOR[box]
    return (
        f'<span style="color:{color};font-size:1.0rem;letter-spacing:0.15em;">'
        f'{filled}{empty}</span>'
        f'<span style="font-size:0.72rem;color:rgba(11,37,69,0.55);margin-left:0.5rem;">'
        f'{_BOX_LABELS[box]}</span>'
    )


def _clear_session():
    for k in ["fc_cards", "fc_idx", "fc_flipped", "fc_knew", "fc_study",
              "fc_saved", "fc_session_start", "fc_topic_saved", "fc_outcomes",
              "fc_leitner_states"]:
        state.pop(k, None)


# ── Setup ─────────────────────────────────────────────────────────────────────

col1, col2 = st.columns([1, 1])
with col1:
    topic_filter = st.selectbox("Topic", ["All"] + CFA_TOPICS, key="fc_topic")
with col2:
    mode = st.selectbox("Mode", ["Leitner mode (adaptive)", "Free review"], key="fc_mode")
st.caption("Topic/mode changes apply from the next session.")

# Show Leitner stats before starting
if mode == "Leitner mode (adaptive)" and "fc_cards" not in state:
    topic_arg = None if topic_filter == "All" else topic_filter
    all_cards = db.get_flashcards(topic=topic_arg) or []
    leitner_states = db.get_leitner_states(user["id"])
    now = datetime.now(timezone.utc)

    n_due = 0
    n_new = 0
    box_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for card in all_cards:
        cid = card["id"]
        if cid not in leitner_states:
            n_new += 1
        else:
            s = leitner_states[cid]
            box_counts[s["box"]] = box_counts.get(s["box"], 0) + 1
            try:
                nra = s["next_review_at"]
                if nra.endswith("Z"):
                    nra = nra[:-1] + "+00:00"
                next_rev = datetime.fromisoformat(nra)
                if next_rev.tzinfo is None:
                    next_rev = next_rev.replace(tzinfo=timezone.utc)
            except Exception:
                next_rev = now
            if s["box"] == 1 or next_rev <= now:
                n_due += 1

    total_seen = sum(box_counts.values())
    n_mastered = box_counts.get(5, 0)

    if total_seen > 0 or n_new > 0:
        st.markdown(
            f'<div style="background:var(--navy-50);border:1px solid rgba(12,29,58,0.10);'
            f'border-radius:var(--radius);padding:0.75rem 1rem;margin:0.5rem 0 0.75rem 0;'
            f'display:flex;gap:2rem;flex-wrap:wrap;">'
            f'<span style="font-size:0.84rem;"><b style="color:#C0392B;">{n_due}</b>'
            f'<span style="color:rgba(11,37,69,0.6);"> due now</span></span>'
            f'<span style="font-size:0.84rem;"><b style="color:var(--navy-800);">{n_new}</b>'
            f'<span style="color:rgba(11,37,69,0.6);"> new</span></span>'
            f'<span style="font-size:0.84rem;"><b style="color:#1A7F4B;">{n_mastered}</b>'
            f'<span style="color:rgba(11,37,69,0.6);"> mastered (box 5)</span></span>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.divider()
if st.button("New session", use_container_width=True, type="secondary"):
    _clear_session()
    st.rerun()

# ── Load cards for session ────────────────────────────────────────────────────

if "fc_cards" not in state:
    state["fc_session_start"] = time.time()
    topic_arg = None if topic_filter == "All" else topic_filter
    all_cards = db.get_flashcards(topic=topic_arg)
    if not all_cards:
        st.warning("No flashcards available.")
        st.stop()

    if mode == "Leitner mode (adaptive)":
        leitner_states = db.get_leitner_states(user["id"])
        now = datetime.now(timezone.utc)

        due_cards   = []   # (card, box, overdue_seconds)
        new_cards   = []   # never reviewed
        future_cards = []  # reviewed but not yet due

        for card in all_cards:
            cid = card["id"]
            if cid not in leitner_states:
                new_cards.append(card)
            else:
                s = leitner_states[cid]
                try:
                    nra = s["next_review_at"]
                    if nra.endswith("Z"):
                        nra = nra[:-1] + "+00:00"
                    next_rev = datetime.fromisoformat(nra)
                    if next_rev.tzinfo is None:
                        next_rev = next_rev.replace(tzinfo=timezone.utc)
                except Exception:
                    next_rev = now
                overdue = (now - next_rev).total_seconds()
                if s["box"] == 1 or overdue >= 0:
                    due_cards.append((card, s["box"], overdue))
                else:
                    future_cards.append(card)

        # Sort: box 1 first, then most overdue
        due_cards.sort(key=lambda x: (x[1], -x[2]))
        due_only = [c for c, _, _ in due_cards]
        random.shuffle(new_cards)

        # Session = due cards + new cards (future cards excluded)
        cards = due_only + new_cards

        if not cards:
            st.info(
                f"All {len(future_cards)} cards are up to date — nothing due yet. "
                "Come back later or switch to **Free review** to practice anyway."
            )
            st.stop()
    else:
        cards = all_cards[:]
        random.shuffle(cards)

    state["fc_cards"] = cards
    state["fc_leitner_states"] = db.get_leitner_states(user["id"])
    state["fc_idx"] = 0
    state["fc_flipped"] = False
    state["fc_knew"] = 0
    state["fc_study"] = 0
    state["fc_outcomes"] = {}

cards = state["fc_cards"]
idx   = state["fc_idx"]
total = len(cards)

# ── Session complete ──────────────────────────────────────────────────────────

if idx >= total:
    knew  = state["fc_knew"]
    study = state["fc_study"]
    pct   = round(knew / total * 100) if total else 0

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
        db.save_session(
            user_id=user["id"],
            session_type="flashcard",
            topic=topic_filter,
            total=total,
            correct=knew,
            duration_sec=duration,
            domain_scores=domain_scores,
        )
        for t, v in topic_results.items():
            db.update_progress(user["id"], t, v["correct"], v["total"])
        state["fc_saved"] = True

    banner_cls = "pass-banner" if pct >= 70 else "fail-banner"
    st.markdown(
        f'<div class="{banner_cls}">Session complete — {pct}% ({knew}/{total} known)</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**{knew}** known · **{study}** to review")

    # Box distribution summary for Leitner mode
    if state.get("fc_mode") == "Leitner mode (adaptive)":
        fresh_states = db.get_leitner_states(user["id"])
        box_dist = {i: 0 for i in range(1, 6)}
        for s in fresh_states.values():
            b = s.get("box", 1)
            box_dist[b] = box_dist.get(b, 0) + 1
        if any(v > 0 for v in box_dist.values()):
            st.markdown("**Your card distribution:**")
            cols = st.columns(5)
            for i, col in enumerate(cols, 1):
                col.markdown(
                    f'<div style="text-align:center;">'
                    f'<div style="font-size:1.4rem;font-weight:700;color:{_BOX_COLOR[i]};">'
                    f'{box_dist[i]}</div>'
                    f'<div style="font-size:0.68rem;color:rgba(11,37,69,0.55);">Box {i}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    btn1, btn2 = st.columns(2)
    if btn1.button("New session", use_container_width=True):
        _clear_session()
        st.rerun()
    if btn2.button("View progress", use_container_width=True):
        st.switch_page("pages/4_Progress.py")
    st.stop()

# ── Card ──────────────────────────────────────────────────────────────────────

card    = cards[idx]
flipped = state["fc_flipped"]
ls      = state.get("fc_leitner_states", {}).get(card["id"])
current_box = ls["box"] if ls else 1

state["fc_topic_saved"] = topic_filter
st.progress(idx / total, text=f"Card {idx + 1} / {total}")

# Topic badge + box indicator
badge_html = f'<span class="topic-badge">{card["topic"]}</span>'
if mode == "Leitner mode (adaptive)":
    badge_html += f'&nbsp;&nbsp;{_box_indicator(current_box)}'
st.markdown(badge_html, unsafe_allow_html=True)
st.markdown("")

if not flipped:
    st.markdown(
        f'<div class="flashcard-front">'
        f'<div><div class="concept">{card["concept_en"]}</div>'
        f'<div style="margin-top:0.8rem;color:rgba(255,255,255,0.65);font-size:0.9rem;">'
        f'Click to reveal the definition</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    fc1, fc2 = st.columns([3, 1])
    if fc1.button("Reveal", use_container_width=True):
        state["fc_flipped"] = True
        st.rerun()
    if fc2.button("Next →", use_container_width=True):
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        st.rerun()
else:
    st.markdown(
        f'<div class="flashcard-back">'
        f'<div style="font-size:1.2rem;font-weight:700;color:#0B2545;margin-bottom:0.8rem;">'
        f'{card["concept_en"]}</div>'
        f'<div style="margin-bottom:0.6rem;">'
        f'{"<b>[EN]</b> " if card.get("definition_fr") else ""}{card["definition_en"]}</div>'
        + (f'<div style="color:#555;"><b>[FR]</b> {card["definition_fr"]}</div>'
           if card.get("definition_fr") else "")
        + (f'<div style="margin-top:0.8rem;color:#1A7F4B;font-style:italic;">'
           f'<b>Example:</b> {card["example_en"]}</div>'
           if card.get("example_en") else "")
        + (f'<div class="formula-box">{card["formula"]}</div>'
           if card.get("formula") else "")
        + '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Next-box preview for Leitner mode
    if mode == "Leitner mode (adaptive)":
        next_box_up   = min(current_box + 1, 5)
        next_box_down = 1
        st.markdown(
            f'<div style="font-size:0.76rem;color:rgba(11,37,69,0.5);margin-bottom:0.4rem;">'
            f'I knew it → {_BOX_LABELS[next_box_up]} &nbsp;|&nbsp; '
            f'Study more → {_BOX_LABELS[next_box_down]}</div>',
            unsafe_allow_html=True,
        )

    col_knew, col_study, col_skip = st.columns(3)
    if col_knew.button("I knew it ✓", use_container_width=True):
        state["fc_knew"] += 1
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        state.setdefault("fc_outcomes", {})[card["id"]] = True
        if mode == "Leitner mode (adaptive)":
            db.update_leitner_card(user["id"], card["id"], knew_it=True)
            state["fc_leitner_states"] = db.get_leitner_states(user["id"])
        st.rerun()
    if col_study.button("Study more", use_container_width=True):
        state["fc_study"] += 1
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        state.setdefault("fc_outcomes", {})[card["id"]] = False
        if mode == "Leitner mode (adaptive)":
            db.update_leitner_card(user["id"], card["id"], knew_it=False)
            state["fc_leitner_states"] = db.get_leitner_states(user["id"])
        st.rerun()
    if col_skip.button("Skip →", use_container_width=True):
        state["fc_idx"] += 1
        state["fc_flipped"] = False
        st.rerun()

# ── Stats bar ─────────────────────────────────────────────────────────────────
st.markdown("---")
c1, c2, c3 = st.columns(3)
c1.metric("Knew", state["fc_knew"])
c2.metric("Study more", state["fc_study"])
c3.metric("Remaining", total - idx)
