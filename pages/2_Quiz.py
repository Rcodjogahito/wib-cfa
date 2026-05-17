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
    st.markdown('<div class="section-header">Quiz configuration</div>', unsafe_allow_html=True)

    topic_options = ["All (Adaptive)"] + CFA_TOPICS
    _preselect = state.pop("quiz_preselect_topic", None)
    _default_idx = topic_options.index(_preselect) if _preselect in topic_options else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        topic_choice = st.selectbox("Topic", topic_options, index=_default_idx)
    _DIFF_LABELS = {"All": None, "Easy": "easy", "Medium": "medium", "Hard": "hard"}
    with col2:
        if topic_choice == "All (Adaptive)":
            difficulty = None
            st.caption("Adaptive mode — all difficulties, weak topics prioritized")
        else:
            _diff_label = st.selectbox("Difficulty", list(_DIFF_LABELS.keys()))
            difficulty = _DIFF_LABELS[_diff_label]
    with col3:
        n_questions = st.selectbox("Number of questions", [10, 20, 30], index=1)

    use_timer = st.checkbox("Global timer (1 min 30 s / question)", value=False)

    if st.button("Start quiz", use_container_width=True, type="primary"):
        topic = None if topic_choice == "All (Adaptive)" else topic_choice

        if topic_choice == "All (Adaptive)":
            questions = get_weighted_questions(user["id"], topic=None, n=n_questions, db=db)
        else:
            questions = db.get_questions(topic=topic, difficulty=difficulty, n=n_questions)

        if not questions:
            st.error("No questions found with these filters.")
        else:
            state["quiz_active"] = True
            state["quiz_questions"] = questions
            state["quiz_idx"] = 0
            state["quiz_answers"] = {}
            state["quiz_q_starts"] = {}
            state["quiz_start"] = time.time()
            state["quiz_use_timer"] = use_timer
            state["quiz_total_duration"] = len(questions) * 90 if use_timer else 0
            state["quiz_topic"] = topic_choice if topic_choice != "All (Adaptive)" else "All (Adaptive)"
            st.rerun()
    st.stop()

# ── Active quiz ───────────────────────────────────────────────────────────────

questions = state["quiz_questions"]
idx = state["quiz_idx"]
total = len(questions)
answers = state.setdefault("quiz_answers", {})
q_starts = state.setdefault("quiz_q_starts", {})
pending = state.setdefault("quiz_pending", {})

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
        st.markdown(f'<div class="pass-banner">Score: {score_pct:.0f}% — Passed!</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="fail-banner">Score: {score_pct:.0f}% — Needs work</div>', unsafe_allow_html=True)

    _h, _rem = divmod(duration, 3600)
    _m, _s = divmod(_rem, 60)
    _dur_str = f"{_h}h {_m:02d}m {_s:02d}s" if _h else f"{_m}m {_s:02d}s"
    skip_note = f" · {skipped} skipped" if skipped else ""
    st.markdown(f"**{correct_count} / {total_answered}** correct · {_dur_str}{skip_note}")
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

    st.subheader("Results by topic")
    for t, v in topic_results.items():
        pct = round(v["correct"] / v["total"] * 100)
        color = "#1B7F4F" if pct >= 70 else ("#856404" if pct >= 50 else "#B52B2B")
        st.markdown(f'<b>{t}</b> — <span style="color:{color};font-weight:700;">{pct}%</span>', unsafe_allow_html=True)
        st.progress(pct / 100)

    with st.expander("Review all questions", expanded=True):
        _show_all_expls = st.checkbox("Show explanations for correct answers too", value=False)
        for i, r in enumerate(results):
            icon = "✓" if r["correct"] else "✗"
            cls = "answer-correct" if r["correct"] else "answer-wrong"
            preview = question_first_line(r["question"])
            selected = r["selected"]
            correct_ans = r["correct_answer"]
            st.markdown(
                f'<div class="{cls}">{icon} Q{i+1}. {preview}'
                + (f' — <b>Your answer: {selected}</b> · Correct: <b>{correct_ans}</b>' if not r["correct"] else "")
                + f'</div>',
                unsafe_allow_html=True,
            )
            if not r["correct"] or _show_all_expls:
                expl_parts = []
                _has_both = r.get("explanation_en") and r.get("explanation_fr")
                if r.get("explanation_en"):
                    expl_parts.append(f'<b>[EN]</b>\n{r["explanation_en"]}' if _has_both else r["explanation_en"])
                if r.get("explanation_fr"):
                    expl_parts.append(f'<b>[FR]</b>\n{r["explanation_fr"]}')
                if expl_parts:
                    st.markdown('<div class="explanation-label">Explanation</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="explanation-box">{chr(10).join(expl_parts)}</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    if col1.button("Restart", use_container_width=True):
        state["quiz_idx"] = 0
        state["quiz_answers"] = {}
        state["quiz_q_starts"] = {0: time.time()}
        state["quiz_start"] = time.time()
        state.pop("quiz_saved", None)
        state.pop("quiz_pending", None)
        st.rerun()
    if col2.button("New quiz", use_container_width=True, type="primary"):
        for k in ["quiz_active", "quiz_questions", "quiz_idx", "quiz_answers",
                  "quiz_q_starts", "quiz_start", "quiz_use_timer", "quiz_topic",
                  "quiz_saved", "quiz_pending"]:
            state.pop(k, None)
        st.rerun()
    if col3.button("View progress", use_container_width=True):
        st.switch_page("pages/4_Progress.py")
    st.stop()

# ── Current question ──────────────────────────────────────────────────────────

q = questions[idx]
current = answers.get(idx)   # None or {"selected": letter, "correct": bool}
answered = current is not None

# ── Timer bar — toujours visible (temps écoulé, ou décompte si activé) ─────────
@st.fragment(run_every=1)
def _quiz_timer():
    _use_countdown = st.session_state.get("quiz_use_timer", False)
    _start = st.session_state.get("quiz_start", time.time())
    _elapsed = int(time.time() - _start)
    _total_dur = st.session_state.get("quiz_total_duration", 0)
    _topic = st.session_state.get("quiz_topic", "All (Adaptive)")
    _q_total = len(st.session_state.get("quiz_questions", []))
    _ans_count = len(st.session_state.get("quiz_answers", {}))

    if _use_countdown and _total_dur > 0:
        _remaining = max(0, _total_dur - _elapsed)
        _color = "#B52B2B" if _remaining < 60 else ("#C9A84C" if _remaining < 300 else "#FFFFFF")
        _m, _s = divmod(int(_remaining), 60)
        _time_str = f"⏱ {_m:02d}:{_s:02d} restantes"
        if _remaining == 0:
            st.session_state["quiz_idx"] = _q_total
            st.rerun()
    else:
        _color = "#C9A84C"
        _m, _s = divmod(_elapsed, 60)
        _time_str = f"⏱ {_m:02d}:{_s:02d}"

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'background:#0B2545;padding:0.5rem 1.2rem;border-radius:8px;margin-bottom:1rem;">'
        f'<span style="color:#C9A84C;font-weight:700;">'
        f'Quiz{(" — " + _topic) if _topic not in ("All (Adaptive)",) else ""}</span>'
        f'<span style="font-family:monospace;font-size:1.1rem;color:{_color};font-weight:700;">'
        f'{_time_str}</span>'
        f'<span style="color:rgba(255,255,255,0.7);">{_ans_count} / {_q_total} answered</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

_quiz_timer()

# Progress
st.markdown(
    f'<div class="progress-label">Question {idx + 1} / {total}'
    f'{"  ·  " + str(answered_count) + " answered" if answered_count else ""}</div>',
    unsafe_allow_html=True,
)
st.progress(answered_count / total if total else 0)

# Badges
topic_badge = f'<span class="topic-badge">{q["topic"]}</span>'
diff = q.get("difficulty", "medium")
_DIFF_FR = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}
diff_badge = f'<span class="difficulty-{diff}">{_DIFF_FR.get(diff, diff.capitalize())}</span>'
source = q.get("source", "")
src_badge = (
    f'<span style="background:var(--navy-100);color:var(--navy-700);border:1px solid '
    f'rgba(12,29,58,0.12);border-radius:3px;padding:2px 8px;font-size:0.70rem;'
    f'font-weight:700;letter-spacing:0.04em;margin-left:4px;">{source}</span>'
) if source else ""
st.markdown(f"{topic_badge} {diff_badge}{src_badge}", unsafe_allow_html=True)

render_question(q["question_en"])

# ── Answer buttons — deux étapes : sélection → validation ────────────────────
st.markdown('<div class="answer-label">Select your answer</div>', unsafe_allow_html=True)

pending_letter = pending.get(idx)

if not answered:
    if pending_letter:
        st.markdown(
            f'<div style="background:var(--navy-100);border:1px solid rgba(12,29,58,0.12);'
            f'border-left:3px solid var(--gold-500);border-radius:var(--radius);'
            f'padding:0.5rem 1rem;margin-bottom:0.6rem;font-size:0.85rem;color:var(--navy-700);">'
            f'Selected: <b>{pending_letter}</b>'
            f' — click another option to change'
            f'</div>',
            unsafe_allow_html=True,
        )
    for letter, option in [("A", q["option_a"]), ("B", q["option_b"]), ("C", q["option_c"])]:
        prefix = "✓  " if pending_letter == letter else ""
        if st.button(f"{prefix}{letter}.  {option}", key=f"q_{idx}_{letter}", use_container_width=True):
            pending[idx] = letter
            st.rerun()
    if pending_letter:
        st.markdown("")
        if st.button("Confirm", key="quiz_validate", type="primary", use_container_width=True):
            correct = pending_letter == q["correct_answer"]
            time_sec = int(time.time() - q_starts.get(idx, time.time()))
            db.save_attempt(
                user_id=user["id"],
                question_id=q["id"],
                selected=pending_letter,
                is_correct=correct,
                time_sec=time_sec,
                session_type="quiz",
            )
            state["quiz_answers"][idx] = {"selected": pending_letter, "correct": correct}
            pending.pop(idx, None)
            st.rerun()
else:
    for letter, option in [("A", q["option_a"]), ("B", q["option_b"]), ("C", q["option_c"])]:
        is_selected = current["selected"] == letter
        is_correct_ans = letter == q["correct_answer"]
        if is_selected and not is_correct_ans:
            prefix = "✗  "
        elif is_correct_ans:
            prefix = "✓  "
        else:
            prefix = ""
        st.button(f"{prefix}{letter}.  {option}", key=f"q_{idx}_{letter}",
                  use_container_width=True, disabled=True)

# ── Feedback ──────────────────────────────────────────────────────────────────
if answered:
    if current["correct"]:
        st.markdown('<div class="answer-correct">Correct!</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="answer-wrong">Incorrect — Correct answer: <b>{q["correct_answer"]}</b></div>',
            unsafe_allow_html=True,
        )
    expl_parts = []
    _has_both = q.get("explanation_en") and q.get("explanation_fr")
    if q.get("explanation_en"):
        expl_parts.append(f'<b>[EN]</b>\n{q["explanation_en"]}' if _has_both else q["explanation_en"])
    if q.get("explanation_fr"):
        expl_parts.append(f'<b>[FR]</b>\n{q["explanation_fr"]}')
    if expl_parts:
        st.markdown('<div class="explanation-label">Explanation</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="explanation-box">{chr(10).join(expl_parts)}</div>', unsafe_allow_html=True)
    st.markdown("")
    _next_label_inline = "View results →" if idx == total - 1 else "Next question →"
    if st.button(_next_label_inline, key="qnav_next_inline", type="primary", use_container_width=True):
        state["quiz_idx"] += 1
        st.rerun()

# ── Navigation bar ────────────────────────────────────────────────────────────
nav1, _nav_mid, nav3 = st.columns([1, 4, 1])
with nav1:
    if st.button("← Prev", disabled=(idx == 0), use_container_width=True, key="qnav_prev"):
        state["quiz_idx"] -= 1
        st.rerun()
with nav3:
    next_label = "Results →" if idx == total - 1 else "Next →"
    if st.button(next_label, use_container_width=True, key="qnav_next"):
        state["quiz_idx"] += 1
        st.rerun()

# ── Question grid navigator ──────────────────────────────────────────────────
with st.expander("Navigate questions", expanded=True):
    _gcols = st.columns(10)
    for _gi in range(total):
        _gc = _gcols[_gi % 10]
        _ga = answers.get(_gi)
        _is_current = (_gi == idx)
        _label = f"{'✓' if _ga else ''}{_gi+1}"
        _btn_type = "primary" if _is_current else "secondary"
        if _gc.button(_label, key=f"qnav_grid_{_gi}", type=_btn_type,
                      help=f"Q{_gi+1}: {'Answered' if _ga else 'Not answered'}"):
            state["quiz_idx"] = _gi
            st.rerun()

# ── Bottom actions ────────────────────────────────────────────────────────────
st.markdown("---")
_tcol, _rcol = st.columns([3, 1])
with _tcol:
    if answered_count > 0:
        all_done = answered_count == total
        if st.button(
            "Finish quiz" if all_done else f"Finish quiz ({answered_count}/{total} answered)",
            use_container_width=True,
            type="primary" if all_done else "secondary",
        ):
            state["quiz_idx"] = total
            st.rerun()
with _rcol:
    if st.button("Restart", use_container_width=True, key="quiz_restart"):
        state["quiz_idx"] = 0
        state["quiz_answers"] = {}
        state["quiz_q_starts"] = {0: time.time()}
        state["quiz_start"] = time.time()
        state.pop("quiz_saved", None)
        state.pop("quiz_pending", None)
        st.rerun()
