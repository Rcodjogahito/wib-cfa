"""
WIB CFA — Main entry point.
Login → Diagnostic (first time) → Dashboard.
"""

import random
import time
import traceback as _tb

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="WIB – CFA Level 1",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
    from src.database import get_db
    from src.progress import compute_mastery_map, readiness_score, weak_topics
    from src.styles import inject_styles, metric_card, render_hero, render_page_header, render_sidebar_brand, render_ticker, render_question
except Exception as _e:
    st.error(f"**Erreur d'import — {type(_e).__name__}:** `{_e}`")
    st.code(_tb.format_exc())
    st.stop()

inject_styles()


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _sidebar():
    with st.sidebar:
        render_sidebar_brand()
        st.divider()
        if st.session_state.get("user_id"):
            user = get_current_user()
            st.markdown(
                f'<div style="font-size:0.82rem;font-weight:600;color:rgba(255,255,255,0.85);'
                f'letter-spacing:0.03em;">{user["username"]}</div>',
                unsafe_allow_html=True,
            )
            st.divider()
            st.page_link("streamlit_app.py", label="Accueil", icon="🏠")
            st.page_link("pages/1_Study.py", label="Fiches de cours", icon="📖")
            st.page_link("pages/2_Quiz.py", label="Quiz", icon="🎯")
            st.page_link("pages/3_Flashcards.py", label="Flashcards", icon="🃏")
            st.page_link("pages/4_Progress.py", label="Progression", icon="📈")
            st.page_link("pages/5_Exam_Simulator.py", label="Simulateur d'examen", icon="⏱️")
            if st.session_state.get("user_email") == "sam":
                st.page_link("pages/admin.py", label="Admin", icon="🔐")
            st.divider()
            if st.button("Déconnexion", use_container_width=True):
                logout()


_sidebar()

# ── Auth gate ─────────────────────────────────────────────────────────────────

if not require_auth():
    st.stop()

user = get_current_user()
db = get_db()


# ── Diagnostic test ───────────────────────────────────────────────────────────

def _reset_diagnostic():
    """Clear all diagnostic state from session and DB, then rerun."""
    db.clear_diagnostic_progress(user["id"])
    for k in ["diag_questions", "diag_idx", "diag_answers", "diag_start",
              "diag_reset_confirm", "diag_view_idx", "diag_answered_set", "diag_pending"]:
        st.session_state.pop(k, None)
    # Safety flag: skip DB restore even if clear_diagnostic_progress failed
    # (RLS may block deletes when using anon key without service key configured)
    st.session_state["diag_skip_restore"] = True
    st.rerun()


def _run_diagnostic():
    st.markdown('<div class="section-header">Diagnostic Initial</div>', unsafe_allow_html=True)
    st.caption("30 questions · 3 per topic · ~20 minutes — évaluons votre niveau de départ.")

    state = st.session_state

    if "diag_questions" not in state:
        # Skip restore if an explicit reset was just triggered
        skip = state.pop("diag_skip_restore", False)
        # Try to restore in-progress state from DB (survives server restarts)
        saved = None if skip else db.load_diagnostic_progress(user["id"])
        if saved and saved.get("diag_questions"):
            state["diag_questions"] = saved["diag_questions"]
            state["diag_idx"] = saved.get("diag_idx", 0)
            state["diag_answers"] = saved.get("diag_answers", [])
            state["diag_start"] = saved.get("diag_start", time.time())
        else:
            qs: list = []
            for topic in CFA_TOPICS:
                pool = db.get_questions(topic=topic, n=3)
                qs.extend(pool[:3])
            random.shuffle(qs)
            state["diag_questions"] = qs
            state["diag_idx"] = 0
            state["diag_answers"] = []
            state["diag_start"] = time.time()
            db.save_diagnostic_progress(
                user["id"], 0, state["diag_questions"], [], state["diag_start"]
            )

    qs = state["diag_questions"]
    total = len(qs)

    # Free navigation state (session-only; reconstructed on restore from answered count)
    if "diag_answered_set" not in state:
        state["diag_answered_set"] = set(range(state["diag_idx"]))
    if "diag_view_idx" not in state:
        # Start at first unanswered question
        answered_set = state["diag_answered_set"]
        first_unanswered = next((i for i in range(total) if i not in answered_set), total - 1)
        state["diag_view_idx"] = first_unanswered

    answered_set = state["diag_answered_set"]
    idx = state["diag_view_idx"]

    if len(answered_set) >= total:
        _finish_diagnostic(qs, state["diag_answers"])
        return

    q = qs[idx]
    is_answered = idx in answered_set

    # Look up the answer previously given for this question (if any)
    prev = next((a for a in state["diag_answers"] if a["question_id"] == q["id"]), None)

    answered_count = len(answered_set)
    st.markdown(
        f'<div class="progress-label">Question {idx + 1} / {total}'
        f'{"  ·  " + str(answered_count) + "/" + str(total) + " répondues" if answered_count else ""}</div>',
        unsafe_allow_html=True,
    )
    st.progress(answered_count / total)

    topic_badge = f'<span class="topic-badge">{q["topic"]}</span>'
    diff = q.get("difficulty", "medium")
    diff_badge = f'<span class="difficulty-{diff}">{diff.capitalize()}</span>'
    st.markdown(f"{topic_badge} {diff_badge}", unsafe_allow_html=True)
    render_question(q["question_en"])

    st.markdown('<div class="answer-label">Sélectionnez votre réponse</div>', unsafe_allow_html=True)

    if is_answered and prev:
        # Read-only: show selected answer highlighted
        for letter, opt_key in [("A", "option_a"), ("B", "option_b"), ("C", "option_c")]:
            prefix = "✓  " if letter == prev["selected"] else ""
            st.button(f"{prefix}{letter}.  {q[opt_key]}", key=f"d_{letter}_{idx}",
                      use_container_width=True, disabled=True)
        if prev["correct"]:
            st.markdown('<div class="answer-correct">Correct !</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="answer-wrong">Incorrect — La bonne réponse est <b>{q["correct_answer"]}</b></div>',
                unsafe_allow_html=True,
            )
        if q.get("explanation_en"):
            st.markdown(f'<div class="explanation-box">{q["explanation_en"]}</div>', unsafe_allow_html=True)
    else:
        diag_pending = state.setdefault("diag_pending", {})
        pending_letter = diag_pending.get(idx)

        if pending_letter:
            st.markdown(
                f'<div style="background:var(--navy-100);border:1px solid rgba(12,29,58,0.12);'
                f'border-left:3px solid var(--gold-500);border-radius:var(--radius);'
                f'padding:0.5rem 1rem;margin-bottom:0.6rem;font-size:0.85rem;color:var(--navy-700);">'
                f'Réponse sélectionnée : <b>{pending_letter}</b>'
                f' — cliquez une autre option pour modifier'
                f'</div>',
                unsafe_allow_html=True,
            )
        for letter, opt_key in [("A", "option_a"), ("B", "option_b"), ("C", "option_c")]:
            prefix = "✓  " if pending_letter == letter else ""
            if st.button(f"{prefix}{letter}.  {q[opt_key]}", key=f"d_{letter}_{idx}", use_container_width=True):
                diag_pending[idx] = letter
                st.rerun()

        if pending_letter:
            st.markdown("")
            if st.button("Valider", key="diag_validate", type="primary", use_container_width=True):
                correct = pending_letter == q["correct_answer"]
                state["diag_answers"].append({
                    "question_id": q["id"],
                    "topic": q["topic"],
                    "selected": pending_letter,
                    "correct": correct,
                })
                db.save_attempt(
                    user_id=user["id"],
                    question_id=q["id"],
                    selected=pending_letter,
                    is_correct=correct,
                    time_sec=0,
                    session_type="diagnostic",
                )
                answered_set.add(idx)
                state["diag_answered_set"] = answered_set
                state["diag_idx"] = len(state["diag_answers"])
                db.save_diagnostic_progress(
                    user["id"], state["diag_idx"],
                    state["diag_questions"], state["diag_answers"],
                    state["diag_start"],
                )
                diag_pending.pop(idx, None)
                # Auto-advance to next unanswered
                next_q = next((i for i in range(total) if i not in answered_set), None)
                if next_q is not None:
                    state["diag_view_idx"] = next_q
                st.rerun()

    # Navigation bar
    dnav1, _dmid, dnav3 = st.columns([1, 4, 1])
    with dnav1:
        if st.button("← Préc", disabled=(idx == 0), use_container_width=True, key="dnav_prev"):
            state["diag_view_idx"] -= 1
            st.rerun()
    with dnav3:
        if st.button("Suiv →", disabled=(idx >= total - 1), use_container_width=True, key="dnav_next"):
            state["diag_view_idx"] += 1
            st.rerun()

    # ── Reset section ──────────────────────────────────────────────────────
    st.markdown("---")
    if state.get("diag_reset_confirm"):
        st.warning("Es-tu sûr(e) de vouloir recommencer le test depuis le début ? Toute ta progression sera perdue.")
        rc1, rc2 = st.columns(2)
        if rc1.button("Annuler", key="diag_reset_cancel", use_container_width=True):
            state.pop("diag_reset_confirm", None)
            st.rerun()
        if rc2.button("Recommencer", key="diag_reset_yes", type="primary", use_container_width=True):
            _reset_diagnostic()
    else:
        if st.button("↺ Recommencer le test depuis le début", key="diag_reset_btn"):
            state["diag_reset_confirm"] = True
            st.rerun()


def _finish_diagnostic(qs, answers):
    duration = int(time.time() - st.session_state.get("diag_start", time.time()))
    correct = sum(1 for a in answers if a["correct"])
    total = len(answers) or 1
    score = round(correct / total * 100, 1)

    # Per-topic breakdown
    topic_results: dict = {}
    for a in answers:
        t = a["topic"]
        if t not in topic_results:
            topic_results[t] = {"correct": 0, "total": 0}
        topic_results[t]["total"] += 1
        if a["correct"]:
            topic_results[t]["correct"] += 1

    domain_scores = {t: round(v["correct"] / v["total"] * 100, 1)
                     for t, v in topic_results.items() if v["total"]}

    # Save session + progress
    db.save_session(
        user_id=user["id"],
        session_type="diagnostic",
        topic="All",
        total=total,
        correct=correct,
        duration_sec=duration,
        domain_scores=domain_scores,
    )
    for t, v in topic_results.items():
        db.update_progress(user["id"], t, v["correct"], v["total"])

    db.update_user(user["id"], diagnostic_done=1, diagnostic_score=score)
    st.session_state["diagnostic_done"] = True
    st.session_state["diagnostic_score"] = score

    # Clean up diagnostic state (session + DB)
    db.clear_diagnostic_progress(user["id"])
    for k in ["diag_questions", "diag_idx", "diag_answers", "diag_start",
              "diag_reset_confirm", "diag_view_idx", "diag_answered_set", "diag_pending"]:
        st.session_state.pop(k, None)

    # Display result
    banner_cls = "pass-banner" if score >= 60 else "fail-banner"
    label = "Bon point de départ !" if score >= 60 else "Du travail en perspective !"
    st.markdown(
        f'<div class="{banner_cls}">{score:.1f}% — {label}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.subheader("Résultats par topic")
    for t in CFA_TOPICS:
        pct = domain_scores.get(t, 0)
        st.markdown(f"**{t}**")
        st.progress(pct / 100, text=f"{pct:.0f}%")

    if st.button("Aller au dashboard →", use_container_width=True, type="primary"):
        st.rerun()


if not st.session_state.get("diagnostic_done"):
    render_page_header("Diagnostic Initial", "30 questions · évaluons votre niveau de départ")
    _run_diagnostic()
    st.stop()


# ── Dashboard ─────────────────────────────────────────────────────────────────

render_ticker()
render_hero(f"Bienvenue, {user['first_name']} !")

progress_rows = db.get_progress(user["id"])
mastery = compute_mastery_map(progress_rows)
readiness = readiness_score(mastery)
sessions = db.get_sessions(user["id"])

# ── KPI row ───────────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
total_attempts = sum(r.get("total_attempted", 0) for r in progress_rows)
total_correct = sum(r.get("total_correct", 0) for r in progress_rows)
overall_acc = round(total_correct / total_attempts * 100, 1) if total_attempts else 0
mastered_count = sum(1 for v in mastery.values() if v >= 70)
_diag_score = st.session_state.get("diagnostic_score")
diag_display = f"{_diag_score:.0f}%" if _diag_score is not None else "—"

k1.markdown(metric_card(f"{readiness:.0f}%", "Readiness Score"), unsafe_allow_html=True)
k2.markdown(metric_card(f"{overall_acc:.0f}%", "Accuracy globale"), unsafe_allow_html=True)
k3.markdown(metric_card(f"{mastered_count}/10", "Topics maîtrisés"), unsafe_allow_html=True)
k4.markdown(metric_card(str(len(sessions)), "Sessions complétées"), unsafe_allow_html=True)
k5.markdown(metric_card(diag_display, "Score diagnostic"), unsafe_allow_html=True)

st.markdown("---")

# ── Two-column layout: radar + weak areas ────────────────────────────────────

col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown('<div class="section-header">Maîtrise par topic</div>', unsafe_allow_html=True)
    topics = list(mastery.keys())
    values = [mastery[t] for t in topics]
    short = [t.split(" ")[0] for t in topics]

    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=short + [short[0]],
        fill="toself",
        line_color="#C9A84C",
        fillcolor="rgba(201,168,76,0.25)",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont_size=9, gridcolor="#ddd"),
            angularaxis=dict(tickfont_size=11),
            bgcolor="#F8F9FB",
        ),
        paper_bgcolor="#F8F9FB",
        margin=dict(l=40, r=40, t=20, b=20),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown('<div class="section-header">Points faibles prioritaires</div>', unsafe_allow_html=True)
    weak = weak_topics(mastery, threshold=50)
    medium = weak_topics(mastery, threshold=70)
    if weak:
        for t in weak[:5]:
            pct = mastery[t]
            st.markdown(
                f'<div class="wib-card"><b>{t}</b><br>'
                f'<span style="color:#B52B2B;font-size:1.1rem;font-weight:700;">{pct:.0f}%</span>'
                f' — Priorité haute</div>',
                unsafe_allow_html=True,
            )
    else:
        medium_only = [t for t in medium if t not in weak]
        if medium_only:
            for t in medium_only[:5]:
                pct = mastery[t]
                st.markdown(
                    f'<div class="wib-card"><b>{t}</b><br>'
                    f'<span style="color:#856404;font-size:1.1rem;font-weight:700;">{pct:.0f}%</span>'
                    f' — À renforcer</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("Excellent ! Tous les topics sont au-dessus de 50%.")

st.markdown("---")

# ── Topic mastery bars ────────────────────────────────────────────────────────

st.markdown('<div class="section-header">Progression détaillée</div>', unsafe_allow_html=True)

TOPIC_WEIGHTS = {
    "Ethics & Professional Standards": "15–20%",
    "Quantitative Methods": "6–9%",
    "Economics": "6–9%",
    "Financial Statement Analysis": "11–14%",
    "Corporate Issuers": "6–9%",
    "Equity Investments": "11–14%",
    "Fixed Income": "11–14%",
    "Derivatives": "5–8%",
    "Alternative Investments": "7–10%",
    "Portfolio Management": "8–12%",
}

col_a, col_b = st.columns(2)
for i, topic in enumerate(CFA_TOPICS):
    pct = mastery[topic]
    col = col_a if i % 2 == 0 else col_b
    with col:
        label = f"{topic} ({TOPIC_WEIGHTS.get(topic, '')})"
        color = "#1B7F4F" if pct >= 70 else ("#C9A84C" if pct >= 50 else "#B52B2B")
        st.markdown(
            f'<div style="margin-bottom:0.3rem;"><b>{label}</b> '
            f'<span style="color:{color};font-weight:700;">{pct:.0f}%</span></div>',
            unsafe_allow_html=True,
        )
        st.progress(pct / 100)

st.markdown("---")

# ── 30-day study plan ─────────────────────────────────────────────────────────

st.markdown('<div class="section-header">Programme 30 jours</div>', unsafe_allow_html=True)

plan = [
    ("Semaine 1", "Diagnostic + Ethics, Quant, Economics, FSA"),
    ("Semaine 2", "Corporate Issuers, Equity, Fixed Income + révision faibles S1"),
    ("Semaine 3", "Derivatives, Alternatives, Portfolio Mgmt + Mock Partial"),
    ("Semaine 4", "Mock Full ×3 + révision ciblée points faibles"),
]
p1, p2, p3, p4 = st.columns(4)
for col, (week, desc) in zip([p1, p2, p3, p4], plan):
    col.markdown(
        f'<div class="wib-card"><b style="color:#C9A84C;">{week}</b><br>'
        f'<span style="font-size:0.88rem;">{desc}</span></div>',
        unsafe_allow_html=True,
    )

# ── Quick-action buttons ──────────────────────────────────────────────────────

st.markdown("---")
qa1, qa2, qa3, qa4 = st.columns(4)
qa1.page_link("pages/2_Quiz.py", label="Lancer un Quiz", icon="🎯")
qa2.page_link("pages/3_Flashcards.py", label="Réviser Flashcards", icon="🃏")
qa3.page_link("pages/5_Exam_Simulator.py", label="Simuler l'examen", icon="⏱️")
qa4.page_link("pages/4_Progress.py", label="Voir la progression", icon="📈")
