"""
WIB CFA — Progress tracker page.
Radar chart, score history, mastery bars, weak areas, readiness estimate.
"""

import plotly.graph_objects as go
import streamlit as st

from src.auth import CFA_TOPICS, get_current_user, logout, require_auth
from src.database import get_db
from src.progress import compute_mastery_map, readiness_score, weak_topics
from src.styles import inject_styles, metric_card, render_page_header, render_sidebar_brand, render_sidebar_user

st.set_page_config(page_title="Progress — WIB CFA", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
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

render_page_header("Progress", "Mastery tracking — CFA Level I")

progress_rows = db.get_progress(user["id"])
sessions = db.get_sessions(user["id"])
mastery = compute_mastery_map(progress_rows)
readiness = readiness_score(mastery)

# ── KPIs ──────────────────────────────────────────────────────────────────────

total_att = sum(r.get("total_attempted", 0) for r in progress_rows)
total_cor = sum(r.get("total_correct", 0) for r in progress_rows)
acc = round(total_cor / total_att * 100, 1) if total_att else 0
mastered = sum(1 for v in mastery.values() if v >= 70)

k1, k2, k3, k4 = st.columns(4)
k1.markdown(metric_card(f"{readiness:.0f}%", "Readiness"), unsafe_allow_html=True)
k2.markdown(metric_card(f"{acc:.0f}%", "Accuracy"), unsafe_allow_html=True)
k3.markdown(metric_card(f"{mastered}/10", "Topics ≥ 70%"), unsafe_allow_html=True)
k4.markdown(metric_card(str(len(sessions)), "Sessions"), unsafe_allow_html=True)

st.markdown("---")

# ── Radar + Gauge ─────────────────────────────────────────────────────────────

col_radar, col_gauge = st.columns([3, 2])

with col_radar:
    st.markdown('<div class="section-header">Mastery by topic</div>', unsafe_allow_html=True)
    labels = [t.split(" ")[0] for t in CFA_TOPICS]
    values = [mastery[t] for t in CFA_TOPICS]

    fig_radar = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        line_color="#C9A84C",
        fillcolor="rgba(201,168,76,0.25)",
        name="Mastery",
    ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont_size=9),
            angularaxis=dict(tickfont_size=11),
            bgcolor="#F8F9FB",
        ),
        paper_bgcolor="#F8F9FB",
        margin=dict(l=40, r=40, t=20, b=20),
        height=380,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col_gauge:
    st.markdown('<div class="section-header">Readiness score</div>', unsafe_allow_html=True)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=readiness,
        number={"suffix": "%", "font": {"size": 40, "color": "#C9A84C"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": "#C9A84C"},
            "bgcolor": "#EEF0F5",
            "steps": [
                {"range": [0, 50], "color": "#FDECEC"},
                {"range": [50, 70], "color": "#FFF3CD"},
                {"range": [70, 100], "color": "#E8F5EE"},
            ],
            "threshold": {
                "line": {"color": "#1B7F4F", "width": 3},
                "thickness": 0.8,
                "value": 70,
            },
        },
        title={"text": "Target: 70%", "font": {"size": 14}},
    ))
    fig_gauge.update_layout(
        paper_bgcolor="#F8F9FB",
        margin=dict(l=20, r=20, t=60, b=20),
        height=300,
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Weak areas
    weak = weak_topics(mastery, threshold=50)
    if weak:
        st.markdown("**Priorities:**")
        for t in weak[:3]:
            st.markdown(f"- {t} ({mastery[t]:.0f}%)")

st.markdown("---")

# ── Per-topic mastery bars ────────────────────────────────────────────────────

st.markdown('<div class="section-header">Topic breakdown</div>', unsafe_allow_html=True)

WEIGHTS = {
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
        color = "#1B7F4F" if pct >= 70 else ("#C9A84C" if pct >= 50 else "#B52B2B")
        row = next((r for r in progress_rows if r.get("topic") == topic), {})
        att = row.get("total_attempted", 0)
        cor = row.get("total_correct", 0)
        st.markdown(
            f'<div style="margin-bottom:0.2rem;">'
            f'<b>{topic}</b> <span style="color:#888;font-size:0.8rem;">({WEIGHTS.get(topic,"")})</span> — '
            f'<span style="color:{color};font-weight:700;">{pct:.0f}%</span>'
            f'<span style="color:#aaa;font-size:0.78rem;margin-left:8px;">{cor}/{att}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.progress(pct / 100)

st.markdown("---")

# ── Score history ─────────────────────────────────────────────────────────────

if sessions:
    st.markdown('<div class="section-header">Session history</div>', unsafe_allow_html=True)

    _TYPE_LABELS = {
        "quiz": "Quiz", "diagnostic": "Diagnostic", "flashcard": "Flashcards",
        "mock_partial": "Partial exam", "mock_full": "Full exam",
    }

    dates = []
    scores = []
    types = []
    for s in reversed(sessions[:30]):
        dates.append(s.get("completed_at", "")[:10])
        scores.append(s.get("score_pct", 0))
        types.append(_TYPE_LABELS.get(s.get("session_type", "quiz"), s.get("session_type", "quiz")))

    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=dates, y=scores, mode="lines+markers",
        line=dict(color="#C9A84C", width=2),
        marker=dict(size=6, color="#0B2545"),
        name="Score",
        text=types,
        hovertemplate="%{x}: %{y:.1f}% (%{text})<extra></extra>",
    ))
    fig_hist.add_hline(y=70, line_dash="dash", line_color="#1B7F4F",
                       annotation_text="70% target", annotation_position="right")
    fig_hist.update_layout(
        yaxis=dict(range=[0, 105], title="Score (%)"),
        xaxis=dict(title="Date"),
        paper_bgcolor="#F8F9FB",
        plot_bgcolor="#F8F9FB",
        margin=dict(l=40, r=20, t=20, b=40),
        height=280,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    # Session table
    with st.expander("All sessions"):
        rows = ["| Date | Type | Topic | Score | Questions |", "|------|------|-------|-------|-----------|"]
        for s in sessions[:20]:
            dt = s.get("completed_at", "")[:16].replace("T", " ")
            tp = _TYPE_LABELS.get(s.get("session_type", ""), s.get("session_type", ""))
            topic = s.get("topic", "")
            score = s.get("score_pct", 0)
            total_q = s.get("total_questions", 0)
            dot = "🟢" if score >= 70 else ("🟡" if score >= 50 else "🔴")
            rows.append(f"| {dt} | {tp} | {topic} | {dot} {score:.1f}% | {total_q} |")
        st.markdown("\n".join(rows))
else:
    st.info("No sessions recorded. Start a quiz or the exam simulator to begin.")

# ── Quick actions ─────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown('<div class="section-header">Continue training</div>', unsafe_allow_html=True)
cta1, cta2, cta3 = st.columns(3)
cta1.page_link("pages/2_Quiz.py", label="Start a Quiz", icon="🎯", use_container_width=True)
cta2.page_link("pages/5_Exam_Simulator.py", label="Simulate exam", icon="⏱️", use_container_width=True)
cta3.page_link("pages/1_Study.py", label="Review notes", icon="📖", use_container_width=True)
