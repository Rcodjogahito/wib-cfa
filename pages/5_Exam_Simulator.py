"""
WIB CFA — Exam Simulator page.
Mock Partial (45Q, 75min) and Mock Full (180Q, 270min).
Timer countdown, question flagging, detailed results with pass/fail vs 70%.
"""

import json
import time

import plotly.graph_objects as go
import streamlit as st

from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
from src.database import get_db
from src.styles import inject_styles, metric_card, render_page_header, render_sidebar_brand, render_question, question_first_line

st.set_page_config(
    page_title="Exam Simulator — WIB CFA",
    page_icon="⏱️",
    layout="wide",
)
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

render_page_header("Exam Simulator", "Mock Partial (45Q) · Mock Full (180Q)")

state = st.session_state
PASS_THRESHOLD = 70.0

MOCK_CONFIGS = {
    "Mock Partial (45Q — 1h15)": {"n": 45, "duration_sec": 75 * 60, "session_type": "mock_partial"},
    "Mock Full (180Q — 4h30)": {"n": 180, "duration_sec": 270 * 60, "session_type": "mock_full"},
}

# ── Setup screen ──────────────────────────────────────────────────────────────

if "exam_active" not in state:
    state["exam_active"] = False

if not state["exam_active"]:
    st.markdown('<div class="section-header">Choisir le mode d\'examen</div>', unsafe_allow_html=True)
    st.markdown("")

    col1, col2 = st.columns(2)
    for col, (name, cfg) in zip([col1, col2], MOCK_CONFIGS.items()):
        with col:
            n = cfg["n"]
            mins = cfg["duration_sec"] // 60
            st.markdown(
                f'<div class="wib-card">'
                f'<b style="font-size:1.1rem;">{name}</b><br>'
                f'{n} questions · {mins // 60}h{mins % 60:02d} · 1m{cfg["duration_sec"] // n // 60}s/question'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Lancer {name}", key=f"start_{name}", use_container_width=True, type="primary"):
                questions = db.get_questions(n=cfg["n"])
                if not questions:
                    st.error("Pas assez de questions en base.")
                    st.stop()
                state["exam_active"] = True
                state["exam_config"] = cfg
                state["exam_name"] = name
                state["exam_questions"] = questions
                state["exam_idx"] = 0
                state["exam_answers"] = {}  # {idx: letter or None}
                state["exam_flagged"] = set()
                state["exam_start"] = time.time()
                state["exam_submitted"] = False
                st.rerun()

    st.markdown("---")
    st.info(
        "**Conditions d'examen réelles** — pas de feedback pendant l'examen. "
        "Les résultats détaillés s'affichent après soumission."
    )
    st.stop()

# ── Exam submitted → results ──────────────────────────────────────────────────

if state.get("exam_submitted"):
    questions = state["exam_questions"]
    answers = state["exam_answers"]
    cfg = state["exam_config"]

    correct_count = 0
    topic_results: dict = {}
    results_detail = []

    for i, q in enumerate(questions):
        selected = answers.get(i)
        is_correct = selected == q["correct_answer"] if selected else False
        if is_correct:
            correct_count += 1
        t = q["topic"]
        topic_results.setdefault(t, {"correct": 0, "total": 0})
        topic_results[t]["total"] += 1
        if is_correct:
            topic_results[t]["correct"] += 1
        results_detail.append({
            "q": q,
            "selected": selected,
            "correct": is_correct,
        })

    total = len(questions)
    score_pct = round(correct_count / total * 100, 2) if total else 0
    duration = int(time.time() - state.get("exam_start", time.time()))

    # Save once only
    domain_scores = {t: round(v["correct"] / v["total"] * 100, 1)
                     for t, v in topic_results.items()}
    if not state.get("exam_saved"):
        db.save_session(
            user_id=user["id"],
            session_type=cfg["session_type"],
            topic="All",
            total=total,
            correct=correct_count,
            duration_sec=duration,
            domain_scores=domain_scores,
        )
        for t, v in topic_results.items():
            db.update_progress(user["id"], t, v["correct"], v["total"])
        # Save individual attempts for adaptive algorithm
        for i, r in enumerate(results_detail):
            if r["selected"] is not None:
                db.save_attempt(
                    user_id=user["id"],
                    question_id=r["q"]["id"],
                    selected=r["selected"],
                    is_correct=r["correct"],
                    time_sec=0,
                    session_type=cfg["session_type"],
                )
        state["exam_saved"] = True

    # Pass / Fail banner
    passed = score_pct >= PASS_THRESHOLD
    banner_cls = "pass-banner" if passed else "fail-banner"
    result_text = "RÉUSSI" if passed else "ÉCHEC"
    st.markdown(
        f'<div class="{banner_cls}">{result_text} — {score_pct:.1f}%</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**{correct_count} / {total}** correctes · {duration // 60}m {duration % 60}s")
    st.markdown(f"Seuil de passage : **{PASS_THRESHOLD:.0f}%** — {'+' if passed else '-'}"
                f"{abs(score_pct - PASS_THRESHOLD):.1f} points")

    st.markdown("---")

    # Per-topic breakdown
    st.markdown('<div class="section-header">Résultats par topic</div>', unsafe_allow_html=True)

    topics = list(topic_results.keys())
    scores_vals = [domain_scores.get(t, 0) for t in topics]

    fig = go.Figure(go.Bar(
        x=topics,
        y=scores_vals,
        marker_color=["#1B7F4F" if s >= 70 else ("#C9A84C" if s >= 50 else "#B52B2B")
                      for s in scores_vals],
        text=[f"{s:.0f}%" for s in scores_vals],
        textposition="outside",
    ))
    fig.add_hline(y=70, line_dash="dash", line_color="#0B2545",
                  annotation_text="70% threshold")
    fig.update_layout(
        yaxis=dict(range=[0, 110], title="Score (%)"),
        xaxis=dict(tickangle=-30),
        paper_bgcolor="#F8F9FB",
        plot_bgcolor="#F8F9FB",
        margin=dict(l=20, r=20, t=20, b=80),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    # KPI cards per topic
    cols = st.columns(min(5, len(topics)))
    for i, t in enumerate(topics):
        pct = domain_scores.get(t, 0)
        col = cols[i % len(cols)]
        col.markdown(
            metric_card(f"{pct:.0f}%", t.split(" ")[0]),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Detailed question review
    st.markdown('<div class="section-header">Revue détaillée</div>', unsafe_allow_html=True)
    wrong_only = st.checkbox("Afficher uniquement les erreurs", value=True)
    for i, r in enumerate(results_detail):
        q = r["q"]
        if wrong_only and r["correct"]:
            continue
        icon = "✓" if r["correct"] else "✗"
        cls = "answer-correct" if r["correct"] else "answer-wrong"
        selected_label = r["selected"] or "—"
        preview = question_first_line(q["question_en"])
        st.markdown(
            f'<div class="{cls}">'
            f'{icon} Q{i+1}. [{q["topic"]}] {preview}<br>'
            f'Votre réponse: <b>{selected_label}</b> · '
            f'Correcte: <b>{q["correct_answer"]}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if not r["correct"]:
            _expl_en = q.get("explanation_en", "")
            _expl_fr = q.get("explanation_fr", "")
            _expl_parts = []
            if _expl_en:
                _expl_parts.append(f'<b>[EN]</b> {_expl_en}')
            if _expl_fr:
                _expl_parts.append(f'<b>[FR]</b> {_expl_fr}')
            if _expl_parts:
                st.markdown(
                    f'<div class="explanation-box">{"<br><br>".join(_expl_parts)}</div>',
                    unsafe_allow_html=True,
                )

    if st.button("Nouvel examen", use_container_width=True, type="primary"):
        for k in ["exam_active", "exam_config", "exam_name", "exam_questions",
                  "exam_idx", "exam_answers", "exam_flagged", "exam_start",
                  "exam_submitted", "exam_saved"]:
            state.pop(k, None)
        st.rerun()
    st.stop()

# ── Active exam ───────────────────────────────────────────────────────────────

questions = state["exam_questions"]
cfg = state["exam_config"]
idx = state.get("exam_idx", 0)
total = len(questions)
elapsed = time.time() - state["exam_start"]
remaining = max(0, cfg["duration_sec"] - elapsed)
answers = state["exam_answers"]
flagged = state["exam_flagged"]

# ── Timer bar ─────────────────────────────────────────────────────────────────

timer_color = "#B52B2B" if remaining < 600 else ("#C9A84C" if remaining < 1800 else "#0B2545")
h = int(remaining // 3600)
m = int((remaining % 3600) // 60)
s = int(remaining % 60)
st.markdown(
    f'<div style="display:flex;justify-content:space-between;align-items:center;'
    f'background:#0B2545;padding:0.6rem 1.2rem;border-radius:8px;margin-bottom:1rem;">'
    f'<span style="color:#C9A84C;font-weight:700;">{state["exam_name"]}</span>'
    f'<span style="font-family:monospace;font-size:1.4rem;color:{timer_color};font-weight:700;">'
    f'⏱ {h:02d}:{m:02d}:{s:02d}</span>'
    f'<span style="color:rgba(255,255,255,0.7);">{sum(1 for v in answers.values() if v)} / {total} répondues</span>'
    f'</div>',
    unsafe_allow_html=True,
)

if remaining <= 0 and not state.get("exam_submitted"):
    state["exam_submitted"] = True
    st.rerun()

answered_count = sum(1 for v in answers.values() if v)

# ── Quick submit (shown once ≥ 50% answered) ─────────────────────────────────

if answered_count >= total // 2:
    if st.button("Soumettre l'examen", key="submit_top", type="primary", use_container_width=True):
        state["exam_submitted"] = True
        st.rerun()
    st.markdown("")

# ── Navigation ────────────────────────────────────────────────────────────────

st.progress(idx / total, text=f"Question {idx + 1} / {total}")

nav_cols = st.columns([1, 4, 1, 1])
if nav_cols[0].button("← Préc", disabled=(idx == 0)):
    state["exam_idx"] = idx - 1
    st.rerun()
if nav_cols[2].button("Suiv →", disabled=(idx >= total - 1)):
    state["exam_idx"] = idx + 1
    st.rerun()

flag_label = "Marquée ★" if idx in flagged else "Marquer"
if nav_cols[3].button(flag_label):
    if idx in flagged:
        flagged.discard(idx)
    else:
        flagged.add(idx)
    state["exam_flagged"] = flagged
    st.rerun()

# ── Question ──────────────────────────────────────────────────────────────────

q = questions[idx]
topic_badge = f'<span class="topic-badge">{q["topic"]}</span>'
flag_star = (
    ' <span style="color:var(--gold-500);font-size:0.9rem;">&#9733;</span>'
    if idx in flagged else ""
)
st.markdown(f"{topic_badge}{flag_star}", unsafe_allow_html=True)
st.markdown(
    f'<div class="progress-label">Q{idx + 1} / {total}</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="question-card">', unsafe_allow_html=True)
render_question(q["question_en"])
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="answer-label">Select your answer</div>', unsafe_allow_html=True)
current_answer = answers.get(idx)
options = [("A", q["option_a"]), ("B", q["option_b"]), ("C", q["option_c"])]

for letter, text in options:
    prefix = "✓  " if current_answer == letter else ""
    if st.button(
        f"{prefix}{letter}.  {text}",
        key=f"exam_{idx}_{letter}",
        use_container_width=True,
    ):
        state["exam_answers"][idx] = letter
        st.rerun()

# ── Flagged questions mini-map ────────────────────────────────────────────────

if flagged:
    st.markdown("---")
    st.caption(f"Questions marquées ({len(flagged)}) : " +
               ", ".join(f"Q{i+1}" for i in sorted(flagged)))

# ── Submit button ─────────────────────────────────────────────────────────────

st.markdown("---")
unanswered = total - answered_count

if unanswered > 0:
    st.warning(f"{unanswered} question(s) sans réponse.")

if st.button("Soumettre l'examen", type="primary", use_container_width=True):
    state["exam_submitted"] = True
    st.rerun()

# ── Question grid navigator ───────────────────────────────────────────────────

with st.expander("Naviguer entre les questions"):
    grid_cols = st.columns(10)
    for i in range(total):
        col = grid_cols[i % 10]
        ans = answers.get(i)
        is_flagged = i in flagged
        flag_mark = "★" if is_flagged else ""
        done_mark = "✓" if ans else ""
        label = f"{flag_mark}{done_mark}{i+1}"
        if col.button(label, key=f"nav_{i}",
                      help=f"Q{i+1}: {'Répondu' if ans else 'Non répondu'}"):
            state["exam_idx"] = i
            st.rerun()
