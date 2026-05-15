"""
WIB CFA — Quiz page.
Topic selection, difficulty filter, immediate bilingual feedback, saves attempts.
"""

import time

import streamlit as st

from src.adaptive import get_weighted_questions
from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
from src.database import get_db
from src.styles import inject_styles, render_page_header, render_sidebar_brand, render_question, question_first_line

st.set_page_config(page_title="Quiz — WIB CFA", page_icon="🎯", layout="wide")
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
            state["quiz_results"] = []
            state["quiz_start"] = time.time()
            state["quiz_q_start"] = time.time()
            state["quiz_answered"] = False
            state["quiz_selected"] = None
            state["quiz_use_timer"] = use_timer
            state["quiz_topic"] = topic_choice
            st.rerun()
    st.stop()

# ── Active quiz ───────────────────────────────────────────────────────────────

questions = state["quiz_questions"]
idx = state["quiz_idx"]
total = len(questions)

if idx >= total:
    _show_results = True
else:
    _show_results = False

if _show_results:
    # ── Results screen ────────────────────────────────────────────────────────
    results = state["quiz_results"]
    correct_count = sum(1 for r in results if r["correct"])
    score_pct = round(correct_count / total * 100, 1) if total else 0
    duration = int(time.time() - state["quiz_start"])

    if score_pct >= 70:
        st.markdown(
            f'<div class="pass-banner">Score : {score_pct:.0f}% — Réussi !</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="fail-banner">Score : {score_pct:.0f}% — À retravailler</div>',
            unsafe_allow_html=True,
        )

    st.markdown(f"**{correct_count} / {total}** correctes · {duration // 60}m {duration % 60}s")
    st.markdown("---")

    # Save session + progress (once only)
    if not state.get("quiz_saved"):
        topic_results: dict = {}
        for r in results:
            t = r["topic"]
            topic_results.setdefault(t, {"correct": 0, "total": 0})
            topic_results[t]["total"] += 1
            if r["correct"]:
                topic_results[t]["correct"] += 1
        domain_scores = {t: round(v["correct"] / v["total"] * 100, 1)
                         for t, v in topic_results.items()}
        db.save_session(
            user_id=user["id"],
            session_type="quiz",
            topic=state.get("quiz_topic", "All"),
            total=total,
            correct=correct_count,
            duration_sec=duration,
            domain_scores=domain_scores,
        )
        for t, v in topic_results.items():
            db.update_progress(user["id"], t, v["correct"], v["total"])
        state["quiz_saved"] = True
    else:
        topic_results = {}
        for r in results:
            t = r["topic"]
            topic_results.setdefault(t, {"correct": 0, "total": 0})
            topic_results[t]["total"] += 1
            if r["correct"]:
                topic_results[t]["correct"] += 1
        domain_scores = {t: round(v["correct"] / v["total"] * 100, 1)
                         for t, v in topic_results.items()}

    # Per-topic breakdown
    st.subheader("Résultats par topic")
    for t, v in topic_results.items():
        pct = round(v["correct"] / v["total"] * 100)
        color = "#1B7F4F" if pct >= 70 else ("#856404" if pct >= 50 else "#B52B2B")
        st.markdown(f'<b>{t}</b> — <span style="color:{color};font-weight:700;">{pct}%</span>', unsafe_allow_html=True)
        st.progress(pct / 100)

    # Detailed review
    with st.expander("Revoir toutes les questions"):
        for i, r in enumerate(results):
            icon = "✓" if r["correct"] else "✗"
            cls = "answer-correct" if r["correct"] else "answer-wrong"
            preview = question_first_line(r["question"])
            st.markdown(
                f'<div class="{cls}">{icon} Q{i+1}. {preview}</div>',
                unsafe_allow_html=True,
            )
            if not r["correct"]:
                    expl_en = r.get("explanation_en", "")
                    expl_fr = r.get("explanation_fr", "")
                    expl_parts = []
                    if expl_en:
                        expl_parts.append(f'<b>[EN]</b> {expl_en}')
                    if expl_fr:
                        expl_parts.append(f'<b>[FR]</b> {expl_fr}')
                    if expl_parts:
                        st.markdown(
                            f'<div class="explanation-box">{"<br><br>".join(expl_parts)}</div>',
                            unsafe_allow_html=True,
                        )

    col1, col2 = st.columns(2)
    if col1.button("Nouveau quiz", use_container_width=True, type="primary"):
        for k in ["quiz_active", "quiz_questions", "quiz_idx", "quiz_results",
                  "quiz_start", "quiz_q_start", "quiz_answered", "quiz_selected",
                  "quiz_use_timer", "quiz_topic", "quiz_saved"]:
            state.pop(k, None)
        st.rerun()
    if col2.button("Voir la progression", use_container_width=True):
        st.switch_page("pages/4_Progress.py")
    st.stop()

# ── Current question ──────────────────────────────────────────────────────────

q = questions[idx]

# Timer
if state.get("quiz_use_timer"):
    elapsed = time.time() - state.get("quiz_q_start", time.time())
    remaining = max(0, 90 - elapsed)
    timer_color = "#B52B2B" if remaining < 20 else "#0B2545"
    st.markdown(
        f'<div style="text-align:right;font-family:monospace;font-size:1.2rem;'
        f'color:{timer_color};font-weight:700;">'
        f'⏱ {int(remaining // 60):02d}:{int(remaining % 60):02d}</div>',
        unsafe_allow_html=True,
    )
    if remaining == 0 and not state["quiz_answered"]:
        state["quiz_answered"] = True
        state["quiz_selected"] = None

st.markdown(f'<div class="progress-label">Question {idx + 1} / {total}</div>', unsafe_allow_html=True)
st.progress((idx) / total)

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

st.markdown('<div class="answer-label">Select your answer</div>', unsafe_allow_html=True)

# Answer buttons (disabled after answer)
answered = state["quiz_answered"]
selected = state["quiz_selected"]

for letter, option in [
    ("A", q["option_a"]),
    ("B", q["option_b"]),
    ("C", q["option_c"]),
]:
    if st.button(f"{letter}.  {option}", key=f"q_{idx}_{letter}",
                 use_container_width=True, disabled=answered):
        state["quiz_selected"] = letter
        state["quiz_answered"] = True
        correct = letter == q["correct_answer"]
        time_sec = int(time.time() - state.get("quiz_q_start", time.time()))
        db.save_attempt(
            user_id=user["id"],
            question_id=q["id"],
            selected=letter,
            is_correct=correct,
            time_sec=time_sec,
            session_type="quiz",
        )
        state["quiz_results"].append({
            "question_id": q["id"],
            "question": q["question_en"],
            "topic": q["topic"],
            "selected": letter,
            "correct_answer": q["correct_answer"],
            "correct": correct,
            "explanation_en": q.get("explanation_en", ""),
            "explanation_fr": q.get("explanation_fr", ""),
        })
        st.rerun()

# Feedback after answer
if answered and selected:
    correct = selected == q["correct_answer"]
    if correct:
        st.markdown(
            '<div class="answer-correct">Correct !</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="answer-wrong">Incorrect — La bonne réponse est <b>{q["correct_answer"]}</b></div>',
            unsafe_allow_html=True,
        )
    expl_en = q.get("explanation_en", "")
    expl_fr = q.get("explanation_fr", "")
    expl_parts = []
    if expl_en:
        expl_parts.append(f'<b>[EN]</b> {expl_en}')
    if expl_fr:
        expl_parts.append(f'<b>[FR]</b> {expl_fr}')
    if expl_parts:
        st.markdown(f'<div class="explanation-box">{"<br><br>".join(expl_parts)}</div>', unsafe_allow_html=True)
    if st.button("Question suivante →", use_container_width=True):
        state["quiz_idx"] += 1
        state["quiz_answered"] = False
        state["quiz_selected"] = None
        state["quiz_q_start"] = time.time()
        st.rerun()
elif answered and selected is None:
    st.warning("Temps écoulé — question ignorée.")
    if st.button("Question suivante →", use_container_width=True):
        state["quiz_idx"] += 1
        state["quiz_answered"] = False
        state["quiz_selected"] = None
        state["quiz_q_start"] = time.time()
        st.rerun()
