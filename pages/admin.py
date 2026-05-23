"""
WIB CFA — Admin panel. Access restricted to Sam.
"""

import streamlit as st

st.set_page_config(page_title="WIB Admin", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

import pandas as pd
from datetime import datetime

from src.auth import get_current_user, logout, require_auth
from src.database import get_db
from src.styles import inject_styles, metric_card, render_page_header, render_sidebar_brand, render_sidebar_user

inject_styles()

_ADMIN_EMAIL = "samto"

# ── Auth gate — silent rejection for non-admin ────────────────────────────────

if not require_auth():
    st.stop()

user = get_current_user()
if user.get("email") != _ADMIN_EMAIL:
    st.stop()

db = get_db()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    render_sidebar_brand()
    st.divider()
    render_sidebar_user(user["username"])
    st.divider()
    st.page_link("streamlit_app.py", label="Home", icon="🏠")
    st.page_link("pages/1_Study.py", label="Study Notes", icon="📖")
    st.page_link("pages/2_Quiz.py", label="Quiz", icon="🎯")
    st.page_link("pages/3_Flashcards.py", label="Flashcards", icon="🃏")
    st.page_link("pages/4_Progress.py", label="Progress", icon="📈")
    st.page_link("pages/5_Exam_Simulator.py", label="Exam Simulator", icon="⏱️")
    st.divider()
    st.page_link("pages/admin.py", label="Admin", icon="🔐")
    st.divider()
    if st.button("Sign out", use_container_width=True):
        logout()

# ── Content ───────────────────────────────────────────────────────────────────

render_page_header("Administration", "Platform analytics — restricted access")

import traceback as _tb
try:
    users = db.get_all_users()
except Exception as _e:
    st.error(f"**get_all_users() error — {type(_e).__name__}:** `{_e}`")
    st.code(_tb.format_exc())
    st.stop()

total = len(users)
diag_done = sum(1 for u in users if u.get("diagnostic_done"))
with_activity = sum(1 for u in users if u.get("session_count", 0) > 0)

# ── User metrics ──────────────────────────────────────────────────────────────

st.markdown('<div class="section-header">Users</div>', unsafe_allow_html=True)
cols = st.columns(3)
cols[0].markdown(metric_card(str(total), "Registered users"), unsafe_allow_html=True)
cols[1].markdown(metric_card(str(diag_done), "Diagnostics completed"), unsafe_allow_html=True)
cols[2].markdown(metric_card(str(with_activity), "Active users"), unsafe_allow_html=True)

# ── Question bank metrics ─────────────────────────────────────────────────────

st.markdown('<div class="section-header" style="margin-top:1.5rem;">Question bank</div>',
            unsafe_allow_html=True)
try:
    q_stats = db.get_question_stats()
    q_total = q_stats["total"]
    by_src  = q_stats["by_source"]
    src_cols = st.columns(max(len(by_src) + 1, 2))
    src_cols[0].markdown(metric_card(f"{q_total:,}", "Total questions"), unsafe_allow_html=True)
    for i, (src, cnt) in enumerate(sorted(by_src.items()), start=1):
        if i < len(src_cols):
            src_cols[i].markdown(metric_card(f"{cnt:,}", src), unsafe_allow_html=True)
except Exception:
    st.info("Question stats unavailable.")

st.divider()
st.subheader("User list")

rows = []
for u in users:
    created = u.get("created_at") or ""
    if created:
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            created = dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    last_active = u.get("last_active") or ""
    if last_active:
        try:
            dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            last_active = dt.strftime("%d/%m/%Y")
        except Exception:
            pass

    score = u.get("diagnostic_score")
    score_str = f"{score:.0f}%" if score is not None else "—"

    rows.append({
        "Pseudo": u.get("first_name") or u.get("email", ""),
        "Registered": created or "—",
        "Diagnostic": "Yes" if u.get("diagnostic_done") else "No",
        "Diag. score": score_str,
        "Sessions": u.get("session_count", 0),
        "Last active": last_active or "—",
    })

df = pd.DataFrame(rows)
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Sessions": st.column_config.NumberColumn(format="%d"),
    },
)

# ── Data Quality Audit ────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    '<div class="section-header" style="margin-top:1.5rem;">Data Quality — Answer Consistency</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Vérifie que chaque `correct_answer` (A/B/C) est cohérent avec l'explication stockée. "
    "Détecte les lettres explicitement mentionnées dans l'explication (Pass 1 — haute confiance) "
    "et les textes d'options présents dans la première phrase (Pass 2)."
)

_audit_state = st.session_state.setdefault("admin_audit", {})


def _fetch_all_questions_for_audit():
    """Fetch all questions from Supabase for audit (paginated)."""
    sb = db.sb
    if not sb:
        return [], "SQLite — audit not supported here (Supabase only)"
    rows = []
    offset = 0
    while True:
        r = (sb.table("questions")
             .select("id,source,topic,question_en,option_a,option_b,option_c,correct_answer,explanation_en")
             .range(offset, offset + 999)
             .execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows, None


col_a, col_b = st.columns(2)
run_audit = col_a.button("Run Answer Consistency Audit", type="primary", use_container_width=True)
clear_audit = col_b.button("Clear results", use_container_width=True)

if clear_audit:
    st.session_state["admin_audit"] = {}
    st.rerun()

if run_audit:
    with st.spinner("Fetching all questions…"):
        try:
            all_qs, err = _fetch_all_questions_for_audit()
        except Exception as _e:
            st.error(f"Fetch error: {_e}")
            all_qs, err = [], str(_e)

    if err:
        st.error(err)
    elif not all_qs:
        st.warning("No questions found.")
    else:
        from src.data_quality import audit_questions
        with st.spinner(f"Analysing {len(all_qs):,} questions…"):
            results = audit_questions(all_qs)

        _audit_state["results"] = results
        _audit_state["total"] = len(all_qs)
        _audit_state["pending_fixes"] = (
            [(qid, s, d, snip) for qid, s, d, snip in results["p1_fixes"]]
            + [(qid, s, d, snip) for qid, s, d, snip in results["p2_fixes"]]
        )
        st.rerun()

if _audit_state.get("results"):
    res = _audit_state["results"]
    total_q = _audit_state.get("total", 0)
    p1 = res["p1_fixes"]
    p2 = res["p2_fixes"]
    p3 = res["p3_flags"]

    high_conf = len(p1) + len(p2)
    st.markdown(f"**{total_q:,} questions analysées**")

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Cohérentes", res["ok"])
    mc2.metric("Corrections P1 (lettre explicite)", len(p1), delta_color="inverse")
    mc3.metric("Corrections P2 (texte exact)", len(p2), delta_color="inverse")
    mc4.metric("Sans signal explication", res["no_signal"])

    if p3:
        st.info(f"**{len(p3)} flags Pass 3** (overlap sémantique — advisory, non corrigés automatiquement)")

    if high_conf > 0:
        st.warning(
            f"**{high_conf} questions ont une réponse stockée incohérente avec l'explication** "
            f"(Pass 1: {len(p1)} | Pass 2: {len(p2)}). Cliquer **Apply Fixes** pour corriger."
        )

        with st.expander(f"Détail des {high_conf} corrections haute confiance", expanded=False):
            _rows = []
            for qid, stored, detected, snip in (p1 + p2):
                _rows.append({
                    "ID (8 chars)": qid[:8],
                    "Stocké": stored,
                    "Détecté": detected,
                    "Question / Expl.": snip[:120],
                })
            st.dataframe(pd.DataFrame(_rows), use_container_width=True, hide_index=True)

        if not _audit_state.get("fixes_applied"):
            if st.button(
                f"Apply {high_conf} Fixes (correct_answer → valeur cohérente avec l'explication)",
                type="primary",
                use_container_width=True,
                key="apply_fixes_btn",
            ):
                sb = db.sb
                if not sb:
                    st.error("Supabase non disponible — impossible d'appliquer les corrections.")
                else:
                    done = errors = 0
                    fix_list = _audit_state.get("pending_fixes", [])
                    pbar = st.progress(0, text="Application des corrections…")
                    for i, (qid, _stored, detected, _snip) in enumerate(fix_list):
                        try:
                            sb.table("questions").update(
                                {"correct_answer": detected}
                            ).eq("id", qid).execute()
                            done += 1
                        except Exception as _e:
                            errors += 1
                        pbar.progress((i + 1) / len(fix_list),
                                      text=f"{i+1}/{len(fix_list)} — {done} OK, {errors} erreurs")
                    _audit_state["fixes_applied"] = True
                    _audit_state["fixes_done"] = done
                    _audit_state["fixes_errors"] = errors
                    st.rerun()
        else:
            done = _audit_state.get("fixes_done", 0)
            errors = _audit_state.get("fixes_errors", 0)
            st.success(
                f"Corrections appliquées : **{done}** réussies, {errors} erreurs. "
                "Relancer l'audit pour vérifier."
            )
    else:
        st.success(
            f"Toutes les questions avec explication sont cohérentes "
            f"({res['ok']} OK, {res['no_signal']} sans explication)."
        )

    if p3:
        with st.expander(f"{len(p3)} flags Pass 3 (advisory — overlap sémantique)", expanded=False):
            _p3_rows = []
            for qid, stored, detected, snip in p3[:100]:
                _p3_rows.append({
                    "ID": qid[:8],
                    "Stocké": stored,
                    "Overlap →": detected,
                    "Extrait": snip[:100],
                })
            st.dataframe(pd.DataFrame(_p3_rows), use_container_width=True, hide_index=True)
            if len(p3) > 100:
                st.caption(f"… et {len(p3)-100} autres")
