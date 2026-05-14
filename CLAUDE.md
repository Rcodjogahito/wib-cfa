# WIB CFA — Claude Code Instructions

## Project overview
CFA Level 1 prep platform built with Streamlit + Supabase.  
**Repo**: https://github.com/Rcodjogahito/wib-cfa (branch: `master`)  
**Live**: https://wib-cfa.streamlit.app/ (Streamlit Cloud, auto-deploys on push to master)  
**DB**: Supabase (prod) + SQLite fallback (local dev)

## Stack
- Python 3.11, Streamlit 1.38+
- supabase-py, Plotly, pdfplumber
- Auth: cookie-based (`wib_uid`, 90 days) via `st.context.cookies` + `st.components.v1.html()`

## File map
```
streamlit_app.py          Home dashboard + diagnostic test
pages/1_Study.py          Study notes (read-only)
pages/2_Quiz.py           Quiz — immediate bilingual feedback
pages/3_Flashcards.py     Flashcards — Leitner system
pages/4_Progress.py       Progress dashboard (reads from Supabase only)
pages/5_Exam_Simulator.py Mock exam (45Q or 180Q, timed)
src/auth.py               Cookie session + user helpers
src/database.py           Supabase/SQLite dual-path ORM
src/styles.py             CSS injection + UI helpers (render_question, metric_card, …)
src/adaptive.py           Weighted question selection based on mastery
src/progress.py           Mastery + readiness score computation
src/content/questions.py  220+ seeded MCQ questions
src/content/flashcards.py Seeded flashcard bank
```

## Progress persistence — all levels

| Level | save_attempt | save_session | update_progress | Extra |
|---|---|---|---|---|
| Diagnostic | per question | on finish | per topic | save_diagnostic_progress() after every answer |
| Quiz | per question | on finish | per topic | — |
| Flashcards | — | on finish | per topic | save_leitner_ids() after every card flip |
| Exam Simulator | per question on submit | on submit | per topic | — |

Progress is NEVER held only in session_state — always written to Supabase immediately.

## Key patterns

### DB writes — always use insert-first-then-delete
For any "single live record" pattern (diagnostic progress, Leitner state):
```python
# 1. INSERT new record (old record stays safe if this fails)
# 2. DELETE old records with .neq("id", new_id)
```
Never delete-then-insert (race condition risk on Streamlit Cloud free tier).

### Question rendering — use render_question()
```python
from src.styles import render_question, question_first_line
render_question(q["question_en"])          # bold first line, raw Markdown rest (enables tables)
question_first_line(q["question_en"])      # safe truncated preview for result lists
```
Do NOT use `st.markdown(f"**{q['question_en']}**")` — it breaks Markdown table rendering.

### Question patches
`_apply_question_patches()` in `database.py` runs idempotently on every `Database.__init__()`.
Add patches there (ILIKE match + field dict) whenever fixing seeded question data in Supabase.
Always mirror the fix in `src/content/questions.py` too (for fresh SQLite seeds).

### Leitner state (Flashcards)
- `fc_study_ids` loaded from DB via `db.load_leitner_ids(user["id"])` on first load
- Saved to DB via `db.save_leitner_ids()` after every card flip
- Storage: `user_sessions` table, `session_type = 'leitner_state'`
- Per-session outcomes tracked in `state["fc_outcomes"]` dict `{card_id: True/False}`

### Diagnostic in-progress save
- Storage: `user_sessions` table, `session_type = 'diag_progress'`
- Payload: `{"diag_idx": N, "question_ids": [...], "diag_answers": [...], "diag_start": T}`
- Stores IDs only (not full question objects) to keep payload small

## Streamlit Cloud constraints
- Free tier restarts server multiple times per day → session_state is wiped
- `@st.cache_resource` persists the `Database` instance within a server process only
- All user state that must survive restarts must go to Supabase

## Deployment
```bash
git add <files>
git commit -m "..."
git push origin master   # triggers auto-redeploy on Streamlit Cloud (~1 min)
```

## Common pitfalls
- `st.context.cookies` is frozen per WebSocket session — read once, cache in session_state
- After logout, suppress cookie restore with `_logged_out_uid` in session_state
- Windows console (cp1252) rejects Greek/math chars (β, ×) in question text — use ASCII equivalents
- `bypassPermissions` is set in `~/.claude/settings.json` — no permission prompts needed
- Do NOT use `runtime.txt` — not supported by Streamlit Cloud Community tier

## Streamlit Cloud stale cache — known issue + fix

**Symptom:** `ImportError: cannot import name 'X' from 'src.styles'` on the live app even though GitHub has the correct file.

**Diagnosis:** Wrap the failing imports in try/except + `st.error()` + `st.code(traceback.format_exc())` in `streamlit_app.py` to bypass Streamlit's redacted error page.

**Fix (in order):**
1. Move the missing function to the **top of the file** (right after `import streamlit as st`) — first lines are less likely to be stale-cached
2. Modify `requirements.txt` (any change, e.g. add a version upper bound) → forces Streamlit Cloud to rebuild venv AND re-clone code
3. Push and wait ~3 min for full rebuild
