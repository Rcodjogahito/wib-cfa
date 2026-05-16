"""
WIB CFA — Quiz page.
Topic selection, difficulty filter, immediate bilingual feedback, saves attempts.
Free navigation between questions — answer in any order.
"""

import time

import streamlit as st

from src.adaptive import get_weighted_questions
from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
from src.database import get_db
from src.styles import inject_styles, render_page_header, render_sidebar_brand, render_question, question_first_line

st.set_page_config(page_title="Quiz — WIB CFA", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")
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

render_page_header("Quiz", "Adaptive practice — 7,249 questions")

# ── Quiz configuration ────────────────────────────────────────────────────────

state = st.session_state

if "quiz_active" not in state:
    state["quiz_active"] = False

if not state["quiz_active"]:
    st.markdown('<div class="section-header">Configuration du quiz</div>', unsafe_allow_html=True)

    topic_options = ["All (Adaptatif)"] + CFA_TOPICS
    _preselect = state.pop("quiz_preselect_topic", None)
    _default_idx = topic_options.index(_preselect) if _preselect in topic_options else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        topic_choice = st.selectbox("Topic", topic_options, index=_default_idx)
    with col2:
        if topic_choice == "All (Adaptatif)":
            difficulty = "All"
            st.caption("Mode adaptatif — toutes difficultés, topics faibles prioritaires")
        else:
            difficulty = st.selectbox("Difficulté", ["All", "Easy", "Medium", "Hard"])
    with col3:
        n_questions = st.selectbox("Nombre de questions", [10, 20, 30], index=1)

    use_timer = st.checkbox("Timer (1 min 30 s / question)", value=False)

    if st.button("Lancer le quiz", use_container_width=True, type="primary"):
        topic = None if topic_choice == "All (Adaptatif)" else topic_choice
        diff = None if difficulty == "All" else difficulty

        if topic_choice == "All (Adaptatif)":
            questions = get_weighted_questions(user["id"], topic=None, n=n_questions, db=db)
        else:
            questions = db.get_questions(topic=topic, difficulty=diff, n=n_questions)

        if not questions:
            st.error("Aucune question trouvée avec ces filtres.")
        else:
            state["quiz_active"] = True
            state["quiz_questions"] = questions
            state["quiz_idx"] = 0
            state["quiz_answers"] = {}      # {idx: {"selected": letter, "correct": bool}}
            state["quiz_q_starts"] = {}     # {idx: first_view_timestamp}
            state["quiz_start"] = time.time()
            state["quiz_use_timer"] = use_timer
            state["quiz_topic"] = topic_choice
            st.rerun()
    st.stop()

# ── Active quiz ───────────────────────────────────────────────────────────────

questions = state["quiz_questions"]
idx = state["quiz_idx"]
total = len(questions)
answers = state.setdefault("quiz_answers", {})
q_starts = state.setdefault("quiz_q_starts", {})

# Track first view time for this question
if 0 <= idx < total and idx not in q_starts:
    q_starts[idx] = time.time()

answered_count = len(answers)

# ── Results screen ────────────────────────────────────────────────────────────

if idx >= total:
    results = []
    for i, q in enumerate(questions):
        ans = answers.get(i)
        if ans:
            results.append({
                "question_id": questions[i]["id"],
                "question": questions[i]["question_en"],
                "topic": questions[i]["topic"],
                "selected": ans["selected"],
                "correct_answer": questions[i]["correct_answer"],
                "correct": ans["correct"],
                "explanation_en": questions[i].get("explanation_en", ""),
                "explanation_fr": questions[i].get("explanation_fr", ""),
            })

    total_answered = len(results)
    correct_count = sum(1 for r in results if r["correct"])
    score_pct = round(correct_count / total_answered * 100, 1) if total_answered else 0
    skipped = total - total_answered
    duration = int(time.time() - state["quiz_start"])

    if score_pct >= 70:
        st.markdown(f'<div class="pass-banner">Score : {score_pct:.0f}% — Réussi !</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="fail-banner">Score : {score_pct:.0f}% — À retravailler</div>', unsafe_allow_html=True)

    _h, _rem = divmod(duration, 3600)
    _m, _s = divmod(_rem, 60)
    _dur_str = f"{_h}h {_m:02d}m {_s:02d}s" if _h else f"{_m}m {_s:02d}s"
    skip_note = f" · {skipped} ignorée(s)" if skipped else ""
    st.markdown(f"**{correct_count} / {total_answered}** correctes · {_dur_str}{skip_note}")
    st.markdown("---")

    # Build per-topic stats
    topic_results: dict = {}
    for r in results:
        t = r["topic"]
        topic_results.setdefault(t, {"correct": 0, "total": 0})
        topic_results[t]["total"] += 1
        if r["correct"]:
            topic_results[t]["correct"] += 1

    # Save once only
    if not state.get("quiz_saved") and total_answered > 0:
        domain_scores = {t: round(v["correct"] / v["total"] * 100, 1) for t, v in topic_results.items()}
        db.save_session(
            user_id=user["id"],
            session_type="quiz",
            topic=state.get("quiz_topic", "All"),
            total=total_answered,
            correct=correct_count,
            duration_sec=duration,
            domain_scores=domain_scores,
        )
        for t, v in topic_results.items():
            db.update_progress(user["id"], t, v["correct"], v["total"])
        state["quiz_saved"] = True

    st.subheader("Résultats par topic")
    for t, v in topic_results.items():
        pct = round(v["correct"] / v["total"] * 100)
        color = "#1B7F4F" if pct >= 70 else ("#856404" if pct >= 50 else "#B52B2B")
        st.markdown(f'<b>{t}</b> — <span style="color:{color};font-weight:700;">{pct}%</span>', unsafe_allow_html=True)
        st.progress(pct / 100)

    with st.expander("Revoir toutes les questions"):
        for i, r in enumerate(results):
            icon = "✓" if r["correct"] else "✗"
            cls = "answer-correct" if r["correct"] else "answer-wrong"
            preview = question_first_line(r["question"])
            st.markdown(f'<div class="{cls}">{icon} Q{i+1}. {preview}</div>', unsafe_allow_html=True)
            if not r["correct"]:
                expl_parts = []
                if r.get("explanation_en"):
                    expl_parts.append(f'<b>[EN]</b> {r["explanation_en"]}')
                if r.get("explanation_fr"):
                    expl_parts.append(f'<b>[FR]</b> {r["explanation_fr"]}')
                if expl_parts:
                    st.markdown(f'<div class="explanation-box">{"<br><br>".join(expl_parts)}</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    if col1.button("Recommencer", use_container_width=True):
        state["quiz_idx"] = 0
        state["quiz_answers"] = {}
        state["quiz_q_starts"] = {0: time.time()}
        state.pop("quiz_saved", None)
        st.rerun()
    if col2.button("Nouveau quiz", use_container_width=True, type="primary"):
        for k in ["quiz_active", "quiz_questions", "quiz_idx", "quiz_answers",
                  "quiz_q_starts", "quiz_start", "quiz_use_timer", "quiz_topic", "quiz_saved"]:
            state.pop(k, None)
        st.rerun()
    if col3.button("Voir la progression", use_container_width=True):
        st.switch_page("pages/4_Progress.py")
    st.stop()

# ── Current question ──────────────────────────────────────────────────────────

q = questions[idx]
current = answers.get(idx)   # None or {"selected": letter, "correct": bool}
answered = current is not None

# Timer (unanswered questions only — live countdown via fragment)
if state.get("quiz_use_timer") and not answered:
    @st.fragment(run_every=1)
    def _quiz_timer():
        _idx = st.session_state.get("quiz_idx", 0)
        if _idx in st.session_state.get("quiz_answers", {}):
            return
        _starts = st.session_state.get("quiz_q_starts", {})
        _elapsed = time.time() - _starts.get(_idx, time.time())
        _remaining = max(0, 90 - _elapsed)
        _color = "#B52B2B" if _remaining < 20 else "#0B2545"
        st.markdown(
            f'<div style="text-align:right;font-family:monospace;font-size:1.2rem;'
            f'color:{_color};font-weight:700;">'
            f'⏱ {int(_remaining // 60):02d}:{int(_remaining % 60):02d}</div>',
            unsafe_allow_html=True,
        )
        if _remaining == 0:
            st.session_state["quiz_idx"] += 1
            st.rerun()
    _quiz_timer()

# Progress
st.markdown(
    f'<div class="progress-label">Question {idx + 1} / {total}'
    f'{"  ·  " + str(answered_count) + " répondue(s)" if answered_count else ""}</div>',
    unsafe_allow_html=True,
)
st.progress(idx / total)

# Badges
topic_badge = f'<span class="topic-badge">{q["topic"]}</span>'
diff = q.get("difficulty", "medium")
diff_badge = f'<span class="difficulty-{diff}">{diff.capitalize()}</span>'
source = q.get("source", "")
src_badge = (
    f'<span style="background:var(--navy-100);color:var(--navy-700);border:1px solid '
    f'rgba(12,29,58,0.12);border-radius:3px;padding:2px 8px;font-size:0.70rem;'
    f'font-weight:700;letter-spacing:0.04em;margin-left:4px;">{source}</span>'
) if source else ""
st.markdown(f"{topic_badge} {diff_badge}{src_badge}", unsafe_allow_html=True)

st.markdown('<div class="question-card">', unsafe_allow_html=True)
render_question(q["question_en"])
st.markdown('</div>', unsafe_allow_html=True)

# ── Navigation bar ────────────────────────────────────────────────────────────
nav1, _nav_mid, nav3 = st.columns([1, 4, 1])
with nav1:
    if st.button("← Préc", disabled=(idx == 0), use_container_width=True, key="qnav_prev"):
        state["quiz_idx"] -= 1
        st.rerun()
with nav3:
    next_label = "Résultats →" if idx == total - 1 else "Suiv →"
    if st.button(next_label, use_container_width=True, key="qnav_next"):
        state["quiz_idx"] += 1
        st.rerun()

# ── Answer buttons ────────────────────────────────────────────────────────────
st.markdown('<div class="answer-label">Select your answer</div>', unsafe_allow_html=True)
for letter, option in [("A", q["option_a"]), ("B", q["option_b"]), ("C", q["option_c"])]:
    prefix = "✓  " if answered and current["selected"] == letter else ""
    if st.button(
        f"{prefix}{letter}.  {option}",
        key=f"q_{idx}_{letter}",
        use_container_width=True,
        disabled=answered,
    ):
        correct = letter == q["correct_answer"]
        time_sec = int(time.time() - q_starts.get(idx, time.time()))
        db.save_attempt(
            user_id=user["id"],
            question_id=q["id"],
            selected=letter,
            is_correct=correct,
            time_sec=time_sec,
            session_type="quiz",
        )
        state["quiz_answers"][idx] = {"selected": letter, "correct": correct}
        st.rerun()

# ── Feedback ──────────────────────────────────────────────────────────────────
if answered:
    if current["correct"]:
        st.markdown('<div class="answer-correct">Correct !</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="answer-wrong">Incorrect — La bonne réponse est <b>{q["correct_answer"]}</b></div>',
            unsafe_allow_html=True,
        )
    expl_parts = []
    if q.get("explanation_en"):
        expl_parts.append(f'<b>[EN]</b> {q["explanation_en"]}')
    if q.get("explanation_fr"):
        expl_parts.append(f'<b>[FR]</b> {q["explanation_fr"]}')
    if expl_parts:
        st.markdown(f'<div class="explanation-box">{"<br><br>".join(expl_parts)}</div>', unsafe_allow_html=True)

# ── Bottom actions ────────────────────────────────────────────────────────────
st.markdown("---")
_tcol, _rcol = st.columns([3, 1])
with _tcol:
    if answered_count > 0:
        all_done = answered_count == total
        if st.button(
            "Terminer le quiz" if all_done else f"Terminer le quiz ({answered_count}/{total} répondues)",
            use_container_width=True,
            type="primary" if all_done else "secondary",
        ):
            state["quiz_idx"] = total
            st.rerun()
with _rcol:
    if st.button("Recommencer", use_container_width=True, key="quiz_restart"):
        state["quiz_idx"] = 0
        state["quiz_answers"] = {}
        state["quiz_q_starts"] = {0: time.time()}
        state.pop("quiz_saved", None)
        st.rerun()
