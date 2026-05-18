"""
WIB CFA — Exam Simulator.
CFA Level 1 compliant: 2×90Q×135min full exam, official topic weights, no mid-exam feedback.
"""

import random
import time

import plotly.graph_objects as go
import streamlit as st

from src.adaptive import get_exam_questions
from src.auth import get_current_user, logout, require_auth
from src.database import get_db
from src.styles import (
    inject_styles, metric_card, question_first_line,
    render_page_header, render_question, render_sidebar_brand, render_sidebar_user,
)

st.set_page_config(
    page_title="Exam Simulator — WIB CFA",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="collapsed",
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

render_page_header("Exam Simulator", "CFA Level 1 — Official exam conditions")

# ── CFA Level 1 official topic allocations (2026) ────────────────────────────
# Ranges: Ethics 15-20% | Quant 6-9% | Econ 6-9% | FSA 11-14% | Corp 6-9%
#         Equity 11-14% | FI 11-14% | Deriv 5-8% | AI 7-10% | PM 8-12%
_TOPIC_COUNTS_180 = {
    "Ethics & Professional Standards": 27,  # 15.0%
    "Quantitative Methods":            14,  # 7.8%
    "Economics":                       14,  # 7.8%
    "Financial Statement Analysis":    21,  # 11.7%
    "Corporate Issuers":               14,  # 7.8%
    "Equity Investments":              21,  # 11.7%
    "Fixed Income":                    21,  # 11.7%
    "Derivatives":                     12,  # 6.7%
    "Alternative Investments":         15,  # 8.3%
    "Portfolio Management":            21,  # 11.7%
}  # total = 180

_TOPIC_COUNTS_45 = {
    "Ethics & Professional Standards":  7,  # 15.6%
    "Quantitative Methods":             3,  # 6.7%
    "Economics":                        3,  # 6.7%
    "Financial Statement Analysis":     5,  # 11.1%
    "Corporate Issuers":                3,  # 6.7%
    "Equity Investments":               5,  # 11.1%
    "Fixed Income":                     5,  # 11.1%
    "Derivatives":                      3,  # 6.7%
    "Alternative Investments":          4,  # 8.9%
    "Portfolio Management":             7,  # 15.6%
}  # total = 45

MOCK_CONFIGS = {
    "Mock Partial (45Q — 1h15)": {
        "n": 45,
        "sessions": 1,
        "session_duration_sec": 75 * 60,
        "session_type": "mock_partial",
        "topic_counts": _TOPIC_COUNTS_45,
    },
    "Mock Full (180Q — 4h30)": {
        "n": 180,
        "sessions": 2,
        "session_duration_sec": 135 * 60,  # 135 min per session
        "session_type": "mock_full",
        "topic_counts": _TOPIC_COUNTS_180,
    },
}

# Reference benchmark; actual CFA MPS set by psychometric methods (not published)
PASS_THRESHOLD = 70.0


def _fetch_questions(topic_counts: dict) -> list:
    """Fetch questions with CFA topic weights, prioritizing user's previously wrong answers."""
    return get_exam_questions(user["id"], topic_counts, db=db)


# ── Setup screen ──────────────────────────────────────────────────────────────

if "exam_active" not in state:
    state["exam_active"] = False

if not state["exam_active"]:
    st.markdown('<div class="section-header">Choose exam mode</div>', unsafe_allow_html=True)
    st.markdown("")

    col1, col2 = st.columns(2)
    for col, (name, cfg) in zip([col1, col2], MOCK_CONFIGS.items()):
        with col:
            n = cfg["n"]
            sess = cfg["sessions"]
            dur_min = cfg["session_duration_sec"] // 60
            total_min = dur_min * sess
            spq = cfg["session_duration_sec"] // (n // sess)
            spq_m, spq_s = divmod(spq, 60)

            if sess == 2:
                detail = (
                    f"{n} questions · {total_min // 60}h{total_min % 60:02d} total<br>"
                    f"<span style='font-size:0.84rem;color:rgba(11,37,69,0.65);'>"
                    f"2 sessions × 90Q × {dur_min // 60}h{dur_min % 60:02d}"
                    f" · ~{spq_m}m{spq_s:02d}s/question</span>"
                )
            else:
                detail = (
                    f"{n} questions · {dur_min // 60}h{dur_min % 60:02d}"
                    f" · ~{spq_m}m{spq_s:02d}s/question"
                )

            st.markdown(
                f'<div class="wib-card"><b style="font-size:1.05rem;">{name}</b><br>{detail}</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Start {name}", key=f"start_{name}",
                         use_container_width=True, type="primary"):
                questions = _fetch_questions(cfg["topic_counts"])
                if len(questions) < cfg["n"]:
                    st.error(
                        f"Not enough questions in the database "
                        f"(need {cfg['n']}, got {len(questions)})."
                    )
                    st.stop()
                questions = questions[:cfg["n"]]
                now = time.time()
                state.update({
                    "exam_active": True,
                    "exam_config": cfg,
                    "exam_name": name,
                    "exam_questions": questions,
                    "exam_idx": 0,
                    "exam_answers": {},
                    "exam_flagged": set(),
                    "exam_submitted": False,
                    "exam_phase": 1,
                    "exam_start": now,
                    "exam_session1_start": now,
                    "exam_session2_start": None,
                    "exam_saved": False,
                })
                st.rerun()

    st.markdown("---")
    with st.expander("CFA Level 1 topic weights — official 2026 curriculum"):
        st.markdown("""
| Topic | CFA Range | Full exam (180Q) | Partial (45Q) |
|---|---|---|---|
| Ethics & Professional Standards | 15–20% | 27 | 7 |
| Quantitative Methods | 6–9% | 14 | 3 |
| Economics | 6–9% | 14 | 3 |
| Financial Statement Analysis | 11–14% | 21 | 5 |
| Corporate Issuers | 6–9% | 14 | 3 |
| Equity Investments | 11–14% | 21 | 5 |
| Fixed Income | 11–14% | 21 | 5 |
| Derivatives | 5–8% | 12 | 3 |
| Alternative Investments | 7–10% | 15 | 4 |
| Portfolio Management | 8–12% | 21 | 7 |

*3 answer choices (A/B/C). No negative marking. All questions equal weight.*
*Pass benchmark: 70% (indicative — actual CFA MPS set by psychometric analysis).*
        """)

    st.info(
        "**Real exam conditions** — no feedback during the exam. "
        "In the full exam, Session 1 answers are locked once you advance to Session 2. "
        "Detailed results are shown after final submission."
    )
    st.stop()


# ── Results screen ────────────────────────────────────────────────────────────

if state.get("exam_submitted"):
    questions = state["exam_questions"]
    answers = state["exam_answers"]
    cfg = state["exam_config"]
    is_full = cfg["sessions"] == 2
    half = cfg["n"] // 2 if is_full else cfg["n"]
    total = len(questions)

    topic_results: dict = {}
    results_detail = []
    correct_count = 0

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
        results_detail.append({"q": q, "selected": selected, "correct": is_correct})

    score_pct = round(correct_count / total * 100, 2) if total else 0
    passed = score_pct >= PASS_THRESHOLD
    duration = int(time.time() - state.get("exam_start", time.time()))
    domain_scores = {t: round(v["correct"] / v["total"] * 100, 1)
                     for t, v in topic_results.items()}

    if is_full:
        s1_correct = sum(1 for i in range(half) if results_detail[i]["correct"])
        s2_correct = sum(1 for i in range(half, total) if results_detail[i]["correct"])
        s1_pct = round(s1_correct / half * 100, 1)
        s2_pct = round(s2_correct / half * 100, 1)

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
    banner_cls = "pass-banner" if passed else "fail-banner"
    st.markdown(
        f'<div class="{banner_cls}">{"PASSED" if passed else "FAILED"} — {score_pct:.1f}%</div>',
        unsafe_allow_html=True,
    )
    _h, _rem = divmod(duration, 3600)
    _m, _s = divmod(_rem, 60)
    _dur_str = f"{_h}h {_m:02d}m {_s:02d}s" if _h else f"{_m}m {_s:02d}s"
    st.markdown(f"**{correct_count} / {total}** correct · {_dur_str}")
    st.markdown(
        f'<span style="color:rgba(11,37,69,0.6);font-size:0.82rem;">'
        f'Benchmark: 70% (indicative — actual CFA MPS not published) · '
        f'{"+" if passed else "-"}{abs(score_pct - PASS_THRESHOLD):.1f} pp</span>',
        unsafe_allow_html=True,
    )

    if is_full:
        st.markdown("---")
        sc1, sc2 = st.columns(2)
        sc1.markdown(
            metric_card(f"{s1_pct:.1f}%", "Session 1 (Q1–90)"),
            unsafe_allow_html=True,
        )
        sc2.markdown(
            metric_card(f"{s2_pct:.1f}%", "Session 2 (Q91–180)"),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown('<div class="section-header">Results by topic</div>', unsafe_allow_html=True)

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
                  annotation_text="70% benchmark")
    fig.update_layout(
        yaxis=dict(range=[0, 110], title="Score (%)"),
        xaxis=dict(tickangle=-30),
        paper_bgcolor="#F8F9FB",
        plot_bgcolor="#F8F9FB",
        margin=dict(l=20, r=20, t=20, b=80),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    cols = st.columns(min(5, len(topics)))
    for i, t in enumerate(topics):
        cols[i % len(cols)].markdown(
            metric_card(f"{domain_scores.get(t, 0):.0f}%", t.split(" ")[0]),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown('<div class="section-header">Detailed review</div>', unsafe_allow_html=True)
    wrong_only = st.checkbox("Show incorrect only", value=True)

    for i, r in enumerate(results_detail):
        q = r["q"]
        if wrong_only and r["correct"]:
            continue
        sess_tag = ""
        if is_full:
            sn = 1 if i < half else 2
            qi = i + 1 if sn == 1 else i - half + 1
            sess_tag = f" [S{sn}·Q{qi}]"
        icon = "✓" if r["correct"] else "✗"
        cls = "answer-correct" if r["correct"] else "answer-wrong"
        preview = question_first_line(q["question_en"])
        st.markdown(
            f'<div class="{cls}">'
            f'{icon} Q{i+1}{sess_tag} [{q["topic"]}] {preview}<br>'
            f'Your answer: <b>{r["selected"] or "—"}</b> · '
            f'Correct: <b>{q["correct_answer"]}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if not r["correct"] or not wrong_only:
            _expl_en = q.get("explanation_en", "")
            _expl_fr = q.get("explanation_fr", "")
            _has_both = bool(_expl_en) and bool(_expl_fr)
            _parts = []
            if _expl_en:
                _parts.append(f'<b>[EN]</b>\n{_expl_en}' if _has_both else _expl_en)
            if _expl_fr:
                _parts.append(f'<b>[FR]</b>\n{_expl_fr}')
            if _parts:
                st.markdown('<div class="explanation-label">Explanation</div>',
                            unsafe_allow_html=True)
                st.markdown(
                    f'<div class="explanation-box">{chr(10).join(_parts)}</div>',
                    unsafe_allow_html=True,
                )

    btn1, btn2, btn3 = st.columns(3)
    if btn1.button("Restart same exam", use_container_width=True):
        now = time.time()
        state.update({
            "exam_idx": 0,
            "exam_answers": {},
            "exam_flagged": set(),
            "exam_submitted": False,
            "exam_saved": False,
            "exam_phase": 1,
            "exam_start": now,
            "exam_session1_start": now,
            "exam_session2_start": None,
        })
        state.pop("exam_restart_confirm", None)
        st.rerun()
    if btn2.button("New exam", use_container_width=True, type="primary"):
        for k in ["exam_active", "exam_config", "exam_name", "exam_questions",
                  "exam_idx", "exam_answers", "exam_flagged", "exam_start",
                  "exam_session1_start", "exam_session2_start",
                  "exam_submitted", "exam_saved", "exam_phase", "exam_restart_confirm"]:
            state.pop(k, None)
        st.rerun()
    if btn3.button("View progress", use_container_width=True):
        st.switch_page("pages/4_Progress.py")
    st.stop()


# ── Inter-session break screen (full exam only) ───────────────────────────────

if state.get("exam_phase") == "break":
    answers = state["exam_answers"]
    s1_answered = sum(1 for i in range(90) if answers.get(i))
    s1_unanswered = 90 - s1_answered
    unanswered_note = (
        f' <span style="color:#C9A84C;font-weight:600;">{s1_unanswered} left unanswered.</span>'
        if s1_unanswered else ''
    )
    st.markdown(
        f'<div style="background:#0B2545;color:white;border-radius:12px;'
        f'padding:2.5rem;text-align:center;margin:2rem 0;">'
        f'<div style="font-size:1.8rem;font-weight:700;color:#C9A84C;margin-bottom:0.8rem;">'
        f'Session 1 Complete</div>'
        f'<div style="font-size:1rem;color:rgba(255,255,255,0.9);">'
        f'You answered <b>{s1_answered} / 90</b> questions.{unanswered_note}</div>'
        f'<div style="font-size:0.88rem;color:rgba(255,255,255,0.55);margin-top:1.2rem;">'
        f'Session 1 answers are now locked. You may take your optional break.'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.warning(
        "Once you start Session 2, you cannot return to Session 1 questions. "
        "Session 2: 90 questions · 2h15."
    )
    _, c2, _ = st.columns([1, 2, 1])
    with c2:
        if st.button("Start Session 2 →", type="primary", use_container_width=True):
            now = time.time()
            state["exam_phase"] = 2
            state["exam_session2_start"] = now
            state["exam_idx"] = 90
            st.rerun()
    st.stop()


# ── Active exam ───────────────────────────────────────────────────────────────

questions = state["exam_questions"]
cfg = state["exam_config"]
idx = state.get("exam_idx", 0)
total = len(questions)
answers = state["exam_answers"]
flagged = state["exam_flagged"]
is_full = cfg["sessions"] == 2
phase = state.get("exam_phase", 1)

# Session boundaries (exclusive end)
half = total // 2 if is_full else total
sess_start = half if (is_full and phase == 2) else 0
sess_end = total if (is_full and phase == 2) else half
sess_total = sess_end - sess_start  # 90 or 45
sess_answered = sum(1 for i in range(sess_start, sess_end) if answers.get(i))
q_in_sess = idx - sess_start + 1  # 1-indexed display


# ── Timer (live, per-session countdown) ──────────────────────────────────────

@st.fragment(run_every=1)
def _exam_timer():
    _s = st.session_state
    if _s.get("exam_submitted") or _s.get("exam_phase") == "break":
        return
    _cfg = _s.get("exam_config", {})
    _phase = _s.get("exam_phase", 1)
    _is_full = _cfg.get("sessions", 1) == 2
    _answers = _s.get("exam_answers", {})
    _qs = _s.get("exam_questions", [])
    _half = len(_qs) // 2 if _is_full else len(_qs)

    if _is_full and _phase == 1:
        _start = _s.get("exam_session1_start", time.time())
        _label = "Session 1 of 2 · 90Q"
        _ans = sum(1 for i in range(_half) if _answers.get(i))
        _stotal = _half
    elif _is_full and _phase == 2:
        _start = _s.get("exam_session2_start", time.time())
        _label = "Session 2 of 2 · 90Q"
        _ans = sum(1 for i in range(_half, len(_qs)) if _answers.get(i))
        _stotal = _half
    else:
        _start = _s.get("exam_start", time.time())
        _label = _s.get("exam_name", "Exam")
        _ans = sum(1 for v in _answers.values() if v)
        _stotal = len(_qs)

    _remaining = max(0.0, _cfg.get("session_duration_sec", 0) - (time.time() - _start))
    _color = "#B52B2B" if _remaining < 600 else ("#C9A84C" if _remaining < 1800 else "#FFFFFF")
    _h = int(_remaining // 3600)
    _m = int((_remaining % 3600) // 60)
    _sec = int(_remaining % 60)

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'background:#0B2545;padding:0.6rem 1.2rem;border-radius:8px;margin-bottom:1rem;">'
        f'<span style="color:#C9A84C;font-weight:700;">{_label}</span>'
        f'<span style="font-family:monospace;font-size:1.4rem;color:{_color};font-weight:700;">'
        f'⏱ {_h:02d}:{_m:02d}:{_sec:02d}</span>'
        f'<span style="color:rgba(255,255,255,0.7);">{_ans} / {_stotal} answered</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if _remaining <= 0 and not _s.get("exam_submitted"):
        if _is_full and _phase == 1:
            _s["exam_phase"] = "break"
        else:
            _s["exam_submitted"] = True
        st.rerun()


_exam_timer()

# ── Quick submit (shown when ≥50% of current session answered) ────────────────

if sess_answered >= sess_total // 2:
    btn_label = "Submit Session 1 →" if is_full and phase == 1 else "Submit Exam"
    if st.button(btn_label, key="submit_top", type="primary", use_container_width=True):
        if is_full and phase == 1:
            state["exam_phase"] = "break"
        else:
            state["exam_submitted"] = True
        st.rerun()
    st.markdown("")

# ── Progress bar ──────────────────────────────────────────────────────────────

st.progress(
    q_in_sess / sess_total,
    text=(f"Q{q_in_sess} / {sess_total}" + (f" — Session {phase}" if is_full else "")),
)

# ── Question ──────────────────────────────────────────────────────────────────

q = questions[idx]
topic_badge = f'<span class="topic-badge">{q["topic"]}</span>'
flag_star = (
    ' <span style="color:var(--gold-500);font-size:0.9rem;">&#9733;</span>'
    if idx in flagged else ""
)
st.markdown(f"{topic_badge}{flag_star}", unsafe_allow_html=True)
st.markdown(
    f'<div class="progress-label">Q{q_in_sess} / {sess_total}'
    + (f" — Session {phase}" if is_full else "") + "</div>",
    unsafe_allow_html=True,
)
render_question(q["question_en"])

st.markdown('<div class="answer-label">Select your answer</div>', unsafe_allow_html=True)
current_answer = answers.get(idx)

if current_answer:
    st.markdown(
        f'<div style="background:var(--navy-100);border:1px solid rgba(12,29,58,0.12);'
        f'border-left:3px solid var(--gold-500);border-radius:var(--radius);'
        f'padding:0.5rem 1rem;margin-bottom:0.6rem;font-size:0.85rem;color:var(--navy-700);">'
        f'Selected: <b>{current_answer}</b> — click another option to change'
        f'</div>',
        unsafe_allow_html=True,
    )

for letter, text in [("A", q["option_a"]), ("B", q["option_b"]), ("C", q["option_c"])]:
    prefix = "✓  " if current_answer == letter else ""
    if st.button(f"{prefix}{letter}.  {text}", key=f"exam_{idx}_{letter}",
                 use_container_width=True):
        state["exam_answers"][idx] = letter
        st.rerun()

# ── Navigation ────────────────────────────────────────────────────────────────

nav_cols = st.columns([1, 4, 1, 1])
if nav_cols[0].button("← Prev", disabled=(idx <= sess_start)):
    state["exam_idx"] = idx - 1
    st.rerun()
if nav_cols[2].button("Next →", disabled=(idx >= sess_end - 1)):
    state["exam_idx"] = idx + 1
    st.rerun()

flag_label = "Flagged ★" if idx in flagged else "Flag"
if nav_cols[3].button(flag_label):
    if idx in flagged:
        flagged.discard(idx)
    else:
        flagged.add(idx)
    state["exam_flagged"] = flagged
    st.rerun()

# Flagged in current session
sess_flagged = [i for i in sorted(flagged) if sess_start <= i < sess_end]
if sess_flagged:
    st.markdown("---")
    st.caption(
        f"Flagged ({len(sess_flagged)}): "
        + ", ".join(f"Q{i - sess_start + 1}" for i in sess_flagged)
    )

# ── Submit button ─────────────────────────────────────────────────────────────

st.markdown("---")
sess_unanswered = sess_total - sess_answered
if sess_unanswered > 0:
    st.warning(f"{sess_unanswered} unanswered question(s) in this session.")

submit_label = "Submit Session 1 →" if is_full and phase == 1 else "Submit Exam"
if st.button(submit_label, type="primary", use_container_width=True):
    if is_full and phase == 1:
        state["exam_phase"] = "break"
    else:
        state["exam_submitted"] = True
    st.rerun()

# ── Restart confirm ───────────────────────────────────────────────────────────

if state.get("exam_restart_confirm"):
    st.warning("Restarting will clear all your answers and reset the timer.")
    rc1, rc2 = st.columns(2)
    if rc1.button("Cancel", use_container_width=True, key="exam_restart_cancel"):
        state.pop("exam_restart_confirm", None)
        st.rerun()
    if rc2.button("Yes, restart", use_container_width=True, type="primary",
                  key="exam_restart_yes"):
        now = time.time()
        state.update({
            "exam_idx": 0,
            "exam_answers": {},
            "exam_flagged": set(),
            "exam_submitted": False,
            "exam_saved": False,
            "exam_phase": 1,
            "exam_start": now,
            "exam_session1_start": now,
            "exam_session2_start": None,
        })
        state.pop("exam_restart_confirm", None)
        st.rerun()
else:
    if st.button("Restart exam", use_container_width=True, key="exam_restart_btn"):
        state["exam_restart_confirm"] = True
        st.rerun()

# ── Question grid navigator ───────────────────────────────────────────────────

with st.expander("Navigate questions", expanded=True):
    _ncols = 15

    if is_full:
        st.caption(f"Session 1{'  (locked)' if phase == 2 else ''}")
        g1 = st.columns(_ncols)
        for i in range(half):
            locked = (phase == 2)
            ans = answers.get(i)
            label = f"{'★' if i in flagged else ''}{'✓' if ans else ''}{i + 1}"
            if g1[i % _ncols].button(
                label, key=f"nav_{i}",
                type="primary" if i == idx else "secondary",
                disabled=locked,
                help=f"Q{i+1}: {'Answered' if ans else 'Unanswered'}"
                     + (" (locked)" if locked else ""),
            ):
                state["exam_idx"] = i
                st.rerun()

        st.caption(f"Session 2{'  (not yet started)' if phase == 1 else ''}")
        g2 = st.columns(_ncols)
        for i in range(half, total):
            locked = (phase == 1)
            ans = answers.get(i)
            label = f"{'★' if i in flagged else ''}{'✓' if ans else ''}{i - half + 1}"
            if g2[i % _ncols].button(
                label, key=f"nav_{i}",
                type="primary" if i == idx else "secondary",
                disabled=locked,
                help=f"Q{i - half + 1}: {'Answered' if ans else 'Unanswered'}"
                     + (" (not started)" if locked else ""),
            ):
                state["exam_idx"] = i
                st.rerun()
    else:
        g = st.columns(_ncols)
        for i in range(total):
            ans = answers.get(i)
            label = f"{'★' if i in flagged else ''}{'✓' if ans else ''}{i + 1}"
            if g[i % _ncols].button(
                label, key=f"nav_{i}",
                type="primary" if i == idx else "secondary",
                help=f"Q{i+1}: {'Answered' if ans else 'Unanswered'}",
            ):
                state["exam_idx"] = i
                st.rerun()
