"""
WIB CFA — Database layer.
Uses Supabase when credentials are available, falls back to SQLite.
"""

import json
import sqlite3
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any


import streamlit as st


# ── Connection helpers ────────────────────────────────────────────────────────

def _get_supabase_client():
    """Return a Supabase client if credentials exist, else None.

    Prefers the service key (bypasses RLS, needed for DELETE/UPDATE) and falls
    back to the anon key. Anon key can SELECT and INSERT but RLS silently blocks
    DELETE, causing clear_diagnostic_progress / save_leitner_ids cleanup to fail.
    """
    try:
        url = st.secrets.get("supabase", {}).get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        key = (
            st.secrets.get("supabase", {}).get("SUPABASE_SERVICE_KEY")
            or os.environ.get("SUPABASE_SERVICE_KEY")
            or st.secrets.get("supabase", {}).get("SUPABASE_ANON_KEY")
            or os.environ.get("SUPABASE_ANON_KEY")
        )
        if url and key:
            from supabase import create_client
            return create_client(url, key)
    except Exception:
        pass
    return None


def _sqlite_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "wib_cfa.db")


def _get_sqlite() -> sqlite3.Connection:
    conn = sqlite3.connect(_sqlite_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ── SQLite initialisation ────────────────────────────────────────────────────

def init_sqlite():
    """Create all tables and seed question/flashcard data if the DB is new."""
    conn = _get_sqlite()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            target_exam_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            diagnostic_done INTEGER DEFAULT 0,
            diagnostic_score REAL
        );

        CREATE TABLE IF NOT EXISTS questions (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            subtopic TEXT,
            difficulty TEXT DEFAULT 'medium',
            question_en TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation_en TEXT,
            explanation_fr TEXT,
            source TEXT DEFAULT 'WIB Internal'
        );

        CREATE TABLE IF NOT EXISTS flashcards (
            id TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            concept_en TEXT NOT NULL,
            definition_en TEXT NOT NULL,
            definition_fr TEXT,
            example_en TEXT,
            formula TEXT
        );

        CREATE TABLE IF NOT EXISTS user_attempts (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            question_id TEXT,
            selected_answer TEXT,
            is_correct INTEGER,
            time_spent_sec INTEGER,
            session_type TEXT,
            attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            session_type TEXT,
            topic TEXT,
            total_questions INTEGER,
            correct_answers INTEGER,
            score_pct REAL,
            duration_sec INTEGER,
            domain_scores_json TEXT,
            completed_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_progress (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            topic TEXT,
            total_attempted INTEGER DEFAULT 0,
            total_correct INTEGER DEFAULT 0,
            mastery_pct REAL DEFAULT 0,
            last_attempted TEXT,
            UNIQUE(user_id, topic)
        );

        CREATE TABLE IF NOT EXISTS user_flashcard_state (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            card_id TEXT NOT NULL,
            box INTEGER NOT NULL DEFAULT 1,
            next_review_at TEXT NOT NULL,
            times_correct INTEGER NOT NULL DEFAULT 0,
            times_wrong INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(user_id, card_id)
        );
    """)
    conn.commit()

    # Seed questions if empty
    cur.execute("SELECT COUNT(*) FROM questions")
    if cur.fetchone()[0] == 0:
        _seed_questions(conn)

    # Seed flashcards if empty
    cur.execute("SELECT COUNT(*) FROM flashcards")
    if cur.fetchone()[0] == 0:
        _seed_flashcards(conn)

    conn.close()


def _seed_questions(conn: sqlite3.Connection):
    from src.content.questions import QUESTIONS
    cur = conn.cursor()
    for q in QUESTIONS:
        cur.execute(
            """INSERT OR IGNORE INTO questions
               (id, topic, subtopic, difficulty, question_en, option_a, option_b, option_c,
                correct_answer, explanation_en, explanation_fr, source)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                q["topic"], q.get("subtopic", ""), q.get("difficulty", "medium"),
                q["question_en"], q["option_a"], q["option_b"], q["option_c"],
                q["correct_answer"], q.get("explanation_en", ""), q.get("explanation_fr", ""),
                q.get("source", "WIB Internal"),
            ),
        )
    conn.commit()


def _seed_flashcards(conn: sqlite3.Connection):
    from src.content.flashcards import FLASHCARDS
    cur = conn.cursor()
    for f in FLASHCARDS:
        cur.execute(
            """INSERT OR IGNORE INTO flashcards
               (id, topic, concept_en, definition_en, definition_fr, example_en, formula)
               VALUES (?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                f["topic"], f["concept_en"], f["definition_en"],
                f.get("definition_fr", ""), f.get("example_en", ""), f.get("formula", ""),
            ),
        )
    conn.commit()


# ── Public API ────────────────────────────────────────────────────────────────

_QUESTION_PATCHES = [
    # Fix 1: annuity PV — $11,872 was wrong, correct value is $11,943
    {
        "match": "%annuity that pays $2,000 per year for 8 years%",
        "fields": {
            "option_b": "$11,943",
            "explanation_en": "PV = PMT × [1 - (1+r)^-n] / r = 2,000 × [1 - (1.07)^-8] / 0.07 = 2,000 × 5.9713 = $11,943.",
        },
    },
    # Fix 2: put-call parity — option A was identical to option B
    {
        "match": "%Put-call parity states that for European options on a non-dividend-paying stock%",
        "fields": {
            "option_a": "Call + Stock Price = Put + PV(Strike).",
            "explanation_en": (
                "Put-call parity: P + S = C + PV(X). "
                "Option A is incorrect — it inverts the positions of S and PV(X), which are not interchangeable. "
                "Option C omits discounting the strike."
            ),
        },
    },
    # Fix 3: capitalise BEST in straddle question
    {
        "match": "%short a call option and short a put option on the same stock with the same strike and expiry. This is best%",
        "fields": {
            "question_en": (
                "An investor is short a call option and short a put option on the same stock "
                "with the same strike and expiry. This is BEST described as a:"
            ),
        },
    },
    # Fix 4: capitalise BEST in IRR question
    {
        "match": "%internal rate of return (IRR) of a private equity fund is best described%",
        "fields": {
            "question_en": "The internal rate of return (IRR) of a private equity fund is BEST described as:",
        },
    },
    # Fix 5: FSA D/E + coverage — convert inline data to Markdown table
    {
        "match": "%A company has total debt of $400M, total equity of $600M%",
        "fields": {
            "question_en": (
                "A company reports the following financial data:\n\n"
                "| Metric | Value |\n"
                "|---|---|\n"
                "| Total Debt | $400M |\n"
                "| Total Equity | $600M |\n"
                "| EBIT | $100M |\n"
                "| Interest Expense | $20M |\n\n"
                "Its debt-to-equity ratio and interest coverage ratio are closest to:"
            ),
        },
    },
    # Fix 6: CAPM — convert inline parameters to Markdown table
    {
        "match": "%A stock with a beta of 1.5 and a market risk premium of 6%%",
        "fields": {
            "question_en": (
                "Using CAPM, the expected return of a stock with the following characteristics is closest to:\n\n"
                "| Parameter | Value |\n"
                "|---|---|\n"
                "| Beta | 1.5 |\n"
                "| Market Risk Premium | 6% |\n"
                "| Risk-Free Rate (Rf) | 3% |"
            ),
        },
    },
    # Fix 7: Equity EV/EBITDA per share — convert inline data to Markdown table
    {
        "match": "%A company has an EV/EBITDA multiple of 8x and EBITDA of $50 million%",
        "fields": {
            "question_en": (
                "A company reports the following data:\n\n"
                "| Metric | Value |\n"
                "|---|---|\n"
                "| EV/EBITDA Multiple | 8x |\n"
                "| EBITDA | $50M |\n"
                "| Net Debt | $100M |\n"
                "| Shares Outstanding | 20M |\n\n"
                "The equity value per share is closest to:"
            ),
        },
    },
]


def _apply_question_patches(sb) -> None:
    """Apply targeted corrections to seeded question records. Idempotent."""
    if sb:
        for patch in _QUESTION_PATCHES:
            try:
                sb.table("questions").update(patch["fields"]).ilike(
                    "question_en", patch["match"]
                ).execute()
            except Exception:
                pass
    else:
        conn = _get_sqlite()
        for patch in _QUESTION_PATCHES:
            sets = ", ".join(f"{k}=?" for k in patch["fields"])
            vals = list(patch["fields"].values()) + [patch["match"]]
            conn.execute(
                f"UPDATE questions SET {sets} WHERE question_en LIKE ?", vals
            )
        conn.commit()
        conn.close()


class Database:
    """Thin wrapper that routes calls to Supabase or SQLite."""

    def __init__(self):
        self.sb = _get_supabase_client()
        if not self.sb:
            init_sqlite()
        _apply_question_patches(self.sb)

    # ── Users ──────────────────────────────────────────────────────────────

    def get_or_create_user(self, email: str, first_name: str) -> Dict:
        email = email.strip().lower()
        if self.sb:
            res = self.sb.table("users").select("*").eq("email", email).execute()
            if res.data:
                user = res.data[0]
                # Always sync first_name to the pseudo the user just typed (correct casing)
                if user.get("first_name") != first_name:
                    self.sb.table("users").update({"first_name": first_name}).eq("email", email).execute()
                    user["first_name"] = first_name
                return user
            new = {"id": str(uuid.uuid4()), "email": email, "first_name": first_name,
                   "diagnostic_done": False, "diagnostic_score": None}
            self.sb.table("users").insert(new).execute()
            return new
        else:
            conn = _get_sqlite()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email=?", (email,))
            row = cur.fetchone()
            if row:
                result = dict(row)
                if result.get("first_name") != first_name:
                    cur.execute("UPDATE users SET first_name=? WHERE email=?", (first_name, email))
                    conn.commit()
                    result["first_name"] = first_name
                conn.close()
                return result
            uid = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO users (id,email,first_name,diagnostic_done) VALUES (?,?,?,0)",
                (uid, email, first_name),
            )
            conn.commit()
            cur.execute("SELECT * FROM users WHERE id=?", (uid,))
            result = dict(cur.fetchone())
            conn.close()
            return result

    def get_all_users(self) -> List[Dict]:
        """Fetch all registered users with basic activity stats. Admin use only."""
        from collections import defaultdict
        if self.sb:
            res = (self.sb.table("users")
                   .select("id,email,first_name,created_at,diagnostic_done,diagnostic_score")
                   .order("created_at", desc=False)
                   .execute())
            users = res.data or []
            try:
                sess_res = (self.sb.table("user_sessions")
                            .select("user_id,completed_at,session_type")
                            .execute())
                sessions = [
                    s for s in (sess_res.data or [])
                    if s.get("session_type") not in ("diag_progress", "leitner_state")
                ]
            except Exception:
                sessions = []
        else:
            conn = _get_sqlite()
            cur = conn.cursor()
            cur.execute(
                "SELECT id,email,first_name,created_at,diagnostic_done,diagnostic_score "
                "FROM users ORDER BY created_at ASC"
            )
            users = [dict(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT user_id,completed_at,session_type FROM user_sessions "
                "WHERE session_type NOT IN ('diag_progress','leitner_state')"
            )
            sessions = [dict(r) for r in cur.fetchall()]
            conn.close()

        user_sessions: dict = defaultdict(list)
        for s in sessions:
            user_sessions[s["user_id"]].append(s["completed_at"])
        for u in users:
            uid = u["id"]
            u_sess = user_sessions.get(uid, [])
            u["session_count"] = len(u_sess)
            u["last_active"] = max(u_sess) if u_sess else None
        return users

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Fetch a user by primary key (used by cookie-based session restore)."""
        if self.sb:
            res = self.sb.table("users").select("*").eq("id", user_id).execute()
            return res.data[0] if res.data else None
        conn = _get_sqlite()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def update_user(self, user_id: str, **kwargs):
        if self.sb:
            self.sb.table("users").update(kwargs).eq("id", user_id).execute()
        else:
            conn = _get_sqlite()
            sets = ", ".join(f"{k}=?" for k in kwargs)
            conn.execute(f"UPDATE users SET {sets} WHERE id=?", (*kwargs.values(), user_id))
            conn.commit()
            conn.close()

    def get_question_stats(self) -> Dict:
        """Return total question count and per-source breakdown. Admin use only."""
        if self.sb:
            # Use count='exact' for total; paginate source field to handle 5k+ rows
            count_res = self.sb.table("questions").select("id", count="exact").limit(1).execute()
            total = count_res.count or 0
            by_source: Dict[str, int] = {}
            page, page_size = 0, 1000
            while True:
                rows = (self.sb.table("questions")
                        .select("source")
                        .range(page * page_size, (page + 1) * page_size - 1)
                        .execute().data or [])
                for r in rows:
                    s = r.get("source") or "Unknown"
                    by_source[s] = by_source.get(s, 0) + 1
                if len(rows) < page_size:
                    break
                page += 1
        else:
            conn = _get_sqlite()
            cur = conn.cursor()
            cur.execute("SELECT source FROM questions")
            rows = [{"source": r[0]} for r in cur.fetchall()]
            conn.close()
            total = len(rows)
            by_source = {}
            for r in rows:
                s = r.get("source") or "Unknown"
                by_source[s] = by_source.get(s, 0) + 1
        return {"total": total, "by_source": by_source}

    # ── Questions ──────────────────────────────────────────────────────────

    # All 10 CFA Level 1 topics in canonical order
    _ALL_TOPICS = [
        "Quantitative Methods", "Economics", "Portfolio Management",
        "Corporate Issuers", "Financial Statement Analysis", "Equity Investments",
        "Fixed Income", "Derivatives", "Alternative Investments",
        "Ethics & Professional Standards",
    ]

    def get_questions(self, topic: Optional[str] = None,
                      difficulty: Optional[str] = None,
                      n: Optional[int] = None) -> List[Dict]:
        import random as _r
        if self.sb:
            if topic and topic != "All":
                fetch_n = max(n * 4, 200) if n else 400
                q = self.sb.table("questions").select("*").eq("topic", topic)
                if difficulty and difficulty != "All":
                    q = q.eq("difficulty", difficulty.lower())
                data = q.limit(fetch_n).execute().data or []
            else:
                # No topic filter: fetch proportionally from every topic to avoid
                # insertion-order bias (Supabase has no ORDER BY random() support).
                per_topic = max(min((n or 30) // len(self._ALL_TOPICS) * 4, 60), 20)
                data = []
                for t in self._ALL_TOPICS:
                    q = self.sb.table("questions").select("*").eq("topic", t)
                    if difficulty and difficulty != "All":
                        q = q.eq("difficulty", difficulty.lower())
                    data.extend(q.limit(per_topic).execute().data or [])
        else:
            conn = _get_sqlite()
            sql = "SELECT * FROM questions WHERE 1=1"
            params: list = []
            if topic and topic != "All":
                sql += " AND topic=?"
                params.append(topic)
            if difficulty and difficulty != "All":
                sql += " AND difficulty=?"
                params.append(difficulty.lower())
            sql += " ORDER BY RANDOM()"
            if n:
                sql += f" LIMIT {int(n)}"
            cur = conn.cursor()
            cur.execute(sql, params)
            data = [dict(r) for r in cur.fetchall()]
            conn.close()
            return data
        _r.shuffle(data)
        return data[:n] if n else data

    def get_question_by_id(self, qid: str) -> Optional[Dict]:
        if self.sb:
            res = self.sb.table("questions").select("*").eq("id", qid).execute()
            return res.data[0] if res.data else None
        conn = _get_sqlite()
        cur = conn.cursor()
        cur.execute("SELECT * FROM questions WHERE id=?", (qid,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_questions_by_ids(self, question_ids: List[str]) -> List[Dict]:
        """Fetch questions by ID list, preserving the given order."""
        if not question_ids:
            return []
        if self.sb:
            res = self.sb.table("questions").select("*").in_("id", question_ids).execute()
            data = res.data or []
        else:
            conn = _get_sqlite()
            placeholders = ",".join("?" * len(question_ids))
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", question_ids)
            data = [dict(r) for r in cur.fetchall()]
            conn.close()
        id_to_q = {q["id"]: q for q in data}
        return [id_to_q[qid] for qid in question_ids if qid in id_to_q]

    # ── Flashcards ─────────────────────────────────────────────────────────

    def get_flashcards(self, topic: Optional[str] = None) -> List[Dict]:
        if self.sb:
            q = self.sb.table("flashcards").select("*")
            if topic and topic != "All":
                q = q.eq("topic", topic)
            res = q.execute()
            return res.data or []
        conn = _get_sqlite()
        sql = "SELECT * FROM flashcards"
        params: list = []
        if topic and topic != "All":
            sql += " WHERE topic=?"
            params.append(topic)
        cur = conn.cursor()
        cur.execute(sql, params)
        data = [dict(r) for r in cur.fetchall()]
        conn.close()
        return data

    # ── Attempts ───────────────────────────────────────────────────────────

    def save_attempt(self, user_id: str, question_id: str, selected: str,
                     is_correct: bool, time_sec: int, session_type: str):
        rec = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "question_id": question_id,
            "selected_answer": selected,
            "is_correct": is_correct,
            "time_spent_sec": time_sec,
            "session_type": session_type,
            "attempted_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.sb:
            self.sb.table("user_attempts").insert(rec).execute()
        else:
            conn = _get_sqlite()
            conn.execute(
                """INSERT INTO user_attempts (id,user_id,question_id,selected_answer,
                   is_correct,time_spent_sec,session_type,attempted_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (rec["id"], user_id, question_id, selected, int(is_correct),
                 time_sec, session_type, rec["attempted_at"]),
            )
            conn.commit()
            conn.close()

    # ── Sessions ───────────────────────────────────────────────────────────

    def save_session(self, user_id: str, session_type: str, topic: str,
                     total: int, correct: int, duration_sec: int,
                     domain_scores: Dict = None) -> str:
        score = round(correct / total * 100, 2) if total else 0
        sid = str(uuid.uuid4())
        rec = {
            "id": sid,
            "user_id": user_id,
            "session_type": session_type,
            "topic": topic,
            "total_questions": total,
            "correct_answers": correct,
            "score_pct": score,
            "duration_sec": duration_sec,
            "domain_scores_json": json.dumps(domain_scores or {}),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.sb:
            self.sb.table("user_sessions").insert(rec).execute()
        else:
            conn = _get_sqlite()
            conn.execute(
                """INSERT INTO user_sessions (id,user_id,session_type,topic,total_questions,
                   correct_answers,score_pct,duration_sec,domain_scores_json,completed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (sid, user_id, session_type, topic, total, correct, score,
                 duration_sec, rec["domain_scores_json"], rec["completed_at"]),
            )
            conn.commit()
            conn.close()
        return sid

    def get_sessions(self, user_id: str) -> List[Dict]:
        if self.sb:
            res = (self.sb.table("user_sessions").select("*")
                   .eq("user_id", user_id)
                   .neq("session_type", "diag_progress")
                   .neq("session_type", "leitner_state")
                   .order("completed_at", desc=True)
                   .execute())
            return res.data or []
        conn = _get_sqlite()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM user_sessions WHERE user_id=? "
            "AND session_type NOT IN ('diag_progress','leitner_state') "
            "ORDER BY completed_at DESC",
            (user_id,)
        )
        data = [dict(r) for r in cur.fetchall()]
        conn.close()
        return data

    # ── Progress ───────────────────────────────────────────────────────────

    def update_progress(self, user_id: str, topic: str, correct: int, attempted: int):
        if self.sb:
            res = (self.sb.table("user_progress").select("*")
                   .eq("user_id", user_id).eq("topic", topic).execute())
            now = datetime.now(timezone.utc).isoformat()
            if res.data:
                row = res.data[0]
                new_att = row["total_attempted"] + attempted
                new_cor = row["total_correct"] + correct
                mastery = round(new_cor / new_att * 100, 2) if new_att else 0
                self.sb.table("user_progress").update({
                    "total_attempted": new_att,
                    "total_correct": new_cor,
                    "mastery_pct": mastery,
                    "last_attempted": now,
                }).eq("id", row["id"]).execute()
            else:
                mastery = round(correct / attempted * 100, 2) if attempted else 0
                self.sb.table("user_progress").insert({
                    "id": str(uuid.uuid4()),
                    "user_id": user_id, "topic": topic,
                    "total_attempted": attempted, "total_correct": correct,
                    "mastery_pct": mastery, "last_attempted": now,
                }).execute()
        else:
            conn = _get_sqlite()
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM user_progress WHERE user_id=? AND topic=?",
                (user_id, topic)
            )
            row = cur.fetchone()
            now = datetime.now(timezone.utc).isoformat()
            if row:
                new_att = row["total_attempted"] + attempted
                new_cor = row["total_correct"] + correct
                mastery = round(new_cor / new_att * 100, 2) if new_att else 0
                conn.execute(
                    """UPDATE user_progress SET total_attempted=?,total_correct=?,
                       mastery_pct=?,last_attempted=? WHERE user_id=? AND topic=?""",
                    (new_att, new_cor, mastery, now, user_id, topic),
                )
            else:
                mastery = round(correct / attempted * 100, 2) if attempted else 0
                conn.execute(
                    """INSERT INTO user_progress (id,user_id,topic,total_attempted,
                       total_correct,mastery_pct,last_attempted)
                       VALUES (?,?,?,?,?,?,?)""",
                    (str(uuid.uuid4()), user_id, topic, attempted, correct, mastery, now),
                )
            conn.commit()
            conn.close()

    def get_progress(self, user_id: str) -> List[Dict]:
        if self.sb:
            res = (self.sb.table("user_progress").select("*")
                   .eq("user_id", user_id).execute())
            return res.data or []
        conn = _get_sqlite()
        cur = conn.cursor()
        cur.execute("SELECT * FROM user_progress WHERE user_id=?", (user_id,))
        data = [dict(r) for r in cur.fetchall()]
        conn.close()
        return data

    def get_wrong_question_ids(self, user_id: str, limit: int = 400) -> List[str]:
        """Return IDs of questions the user has answered incorrectly (most recent first)."""
        if self.sb:
            try:
                res = (self.sb.table("user_attempts")
                       .select("question_id")
                       .eq("user_id", user_id)
                       .eq("is_correct", False)
                       .order("attempted_at", desc=True)
                       .limit(limit)
                       .execute())
                return [r["question_id"] for r in (res.data or [])]
            except Exception:
                return []
        conn = _get_sqlite()
        cur = conn.cursor()
        cur.execute(
            """SELECT question_id FROM user_attempts
               WHERE user_id=? AND is_correct=0
               ORDER BY attempted_at DESC LIMIT ?""",
            (user_id, limit),
        )
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]

    # ── Diagnostic progress (in-progress persistence) ─────────────────────

    def save_diagnostic_progress(self, user_id: str, diag_idx: int,
                                  diag_questions: list, diag_answers: list,
                                  diag_start: float) -> None:
        """Persist in-progress diagnostic state.

        Stores question IDs only (not full objects) to keep the payload small.
        Uses insert-first-then-delete so a failed write never erases the previous
        save (avoids the delete→insert race condition).
        """
        payload = json.dumps({
            "diag_idx": diag_idx,
            "question_ids": [q["id"] for q in diag_questions],
            "diag_answers": diag_answers,
            "diag_start": diag_start,
        })
        now = datetime.now(timezone.utc).isoformat()
        new_id = str(uuid.uuid4())
        if self.sb:
            try:
                # INSERT first — old record stays safe if this call fails
                self.sb.table("user_sessions").insert({
                    "id": new_id,
                    "user_id": user_id,
                    "session_type": "diag_progress",
                    "topic": "progress",
                    "total_questions": len(diag_questions),
                    "correct_answers": len(diag_answers),
                    "score_pct": 0,
                    "duration_sec": 0,
                    "domain_scores_json": payload,
                    "completed_at": now,
                }).execute()
                # DELETE old records only after the new one is safely stored
                self.sb.table("user_sessions").delete().eq(
                    "user_id", user_id
                ).eq("session_type", "diag_progress").neq("id", new_id).execute()
            except Exception as e:
                print(f"[WIB] save_diagnostic_progress error: {e}")
        else:
            conn = _get_sqlite()
            conn.execute(
                "DELETE FROM user_sessions WHERE user_id=? AND session_type='diag_progress'",
                (user_id,),
            )
            conn.execute(
                """INSERT INTO user_sessions (id,user_id,session_type,topic,total_questions,
                   correct_answers,score_pct,duration_sec,domain_scores_json,completed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (new_id, user_id, "diag_progress", "progress",
                 len(diag_questions), len(diag_answers), 0, 0, payload, now),
            )
            conn.commit()
            conn.close()

    def load_diagnostic_progress(self, user_id: str) -> Optional[Dict]:
        """Restore in-progress diagnostic state. Returns None if not found.

        Handles both the legacy format (full question objects embedded) and the
        current format (question IDs only — re-fetches from DB).
        Orders by completed_at DESC so the most recent save wins when multiple
        records exist (can happen if the old delete failed).
        """
        raw = None
        if self.sb:
            try:
                res = (self.sb.table("user_sessions")
                       .select("domain_scores_json")
                       .eq("user_id", user_id)
                       .eq("session_type", "diag_progress")
                       .order("completed_at", desc=True)
                       .limit(1)
                       .execute())
                if res.data:
                    raw = res.data[0]["domain_scores_json"]
            except Exception as e:
                print(f"[WIB] load_diagnostic_progress error: {e}")
                return None
        else:
            conn = _get_sqlite()
            cur = conn.cursor()
            cur.execute(
                """SELECT domain_scores_json FROM user_sessions
                   WHERE user_id=? AND session_type='diag_progress'
                   ORDER BY completed_at DESC LIMIT 1""",
                (user_id,),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                raw = row[0]

        if not raw:
            return None
        try:
            saved = json.loads(raw)
        except Exception:
            return None

        # Current format: question IDs only — re-fetch full objects
        if "question_ids" in saved:
            question_ids = saved["question_ids"]
            if not question_ids:
                return None
            questions = self.get_questions_by_ids(question_ids)
            if len(questions) != len(question_ids):
                return None  # Some questions missing — unsafe to restore
            saved["diag_questions"] = questions

        # Legacy format: full question objects already embedded — use as-is
        if not saved.get("diag_questions"):
            return None

        return saved

    def clear_diagnostic_progress(self, user_id: str) -> None:
        """Remove in-progress diagnostic state (after completion or reset)."""
        if self.sb:
            try:
                self.sb.table("user_sessions").delete().eq(
                    "user_id", user_id).eq("session_type", "diag_progress").execute()
            except Exception:
                pass
        else:
            conn = _get_sqlite()
            conn.execute(
                "DELETE FROM user_sessions WHERE user_id=? AND session_type='diag_progress'",
                (user_id,),
            )
            conn.commit()
            conn.close()

    # ── Leitner state (flashcard Leitner tracking) ────────────────────────

    def save_leitner_ids(self, user_id: str, card_ids: list) -> None:
        """Persist the set of flashcard IDs marked 'study more'. Insert-then-delete."""
        payload = json.dumps({"card_ids": list(card_ids)})
        now = datetime.now(timezone.utc).isoformat()
        new_id = str(uuid.uuid4())
        if self.sb:
            try:
                self.sb.table("user_sessions").insert({
                    "id": new_id,
                    "user_id": user_id,
                    "session_type": "leitner_state",
                    "topic": "flashcards",
                    "total_questions": len(card_ids),
                    "correct_answers": 0,
                    "score_pct": 0,
                    "duration_sec": 0,
                    "domain_scores_json": payload,
                    "completed_at": now,
                }).execute()
                self.sb.table("user_sessions").delete().eq(
                    "user_id", user_id
                ).eq("session_type", "leitner_state").neq("id", new_id).execute()
            except Exception as e:
                print(f"[WIB] save_leitner_ids error: {e}")
        else:
            conn = _get_sqlite()
            conn.execute(
                "DELETE FROM user_sessions WHERE user_id=? AND session_type='leitner_state'",
                (user_id,),
            )
            conn.execute(
                """INSERT INTO user_sessions (id,user_id,session_type,topic,total_questions,
                   correct_answers,score_pct,duration_sec,domain_scores_json,completed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (new_id, user_id, "leitner_state", "flashcards",
                 len(card_ids), 0, 0, 0, payload, now),
            )
            conn.commit()
            conn.close()

    def load_leitner_ids(self, user_id: str) -> list:
        """Return the list of flashcard IDs marked 'study more', or [] if none."""
        raw = None
        if self.sb:
            try:
                res = (self.sb.table("user_sessions")
                       .select("domain_scores_json")
                       .eq("user_id", user_id)
                       .eq("session_type", "leitner_state")
                       .order("completed_at", desc=True)
                       .limit(1)
                       .execute())
                if res.data:
                    raw = res.data[0]["domain_scores_json"]
            except Exception:
                return []
        else:
            conn = _get_sqlite()
            cur = conn.cursor()
            cur.execute(
                """SELECT domain_scores_json FROM user_sessions
                   WHERE user_id=? AND session_type='leitner_state'
                   ORDER BY completed_at DESC LIMIT 1""",
                (user_id,),
            )
            row = cur.fetchone()
            conn.close()
            if row:
                raw = row[0]

        if not raw:
            return []
        try:
            return json.loads(raw).get("card_ids", [])
        except Exception:
            return []

    # ── Leitner v2 — 5-box spaced repetition ─────────────────────────────

    # Days until next review per box
    _LEITNER_DAYS: Dict[int, int] = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14}

    def get_leitner_states(self, user_id: str) -> Dict[str, Dict]:
        """Return {card_id: {box, next_review_at, times_correct, times_wrong}}."""
        if self.sb:
            try:
                res = (self.sb.table("user_flashcard_state")
                       .select("card_id,box,next_review_at,times_correct,times_wrong")
                       .eq("user_id", user_id)
                       .execute())
                return {r["card_id"]: r for r in (res.data or [])}
            except Exception:
                return {}
        conn = _get_sqlite()
        cur = conn.cursor()
        cur.execute(
            """SELECT card_id,box,next_review_at,times_correct,times_wrong
               FROM user_flashcard_state WHERE user_id=?""",
            (user_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return {r[0]: {"card_id": r[0], "box": r[1], "next_review_at": r[2],
                       "times_correct": r[3], "times_wrong": r[4]} for r in rows}

    def update_leitner_card(self, user_id: str, card_id: str, knew_it: bool) -> None:
        """Advance (knew_it=True) or reset (knew_it=False) a card's Leitner box."""
        existing = self.get_leitner_states(user_id).get(card_id)
        now = datetime.now(timezone.utc)
        if existing:
            current_box = existing["box"]
            tc = existing["times_correct"]
            tw = existing["times_wrong"]
        else:
            current_box = 1
            tc = 0
            tw = 0

        new_box = min(current_box + 1, 5) if knew_it else 1
        delta_days = self._LEITNER_DAYS[new_box]
        next_review = (now + timedelta(days=delta_days)).isoformat()
        now_iso = now.isoformat()
        new_tc = tc + (1 if knew_it else 0)
        new_tw = tw + (0 if knew_it else 1)

        if self.sb:
            try:
                if existing:
                    self.sb.table("user_flashcard_state").update({
                        "box": new_box,
                        "next_review_at": next_review,
                        "times_correct": new_tc,
                        "times_wrong": new_tw,
                        "updated_at": now_iso,
                    }).eq("user_id", user_id).eq("card_id", card_id).execute()
                else:
                    self.sb.table("user_flashcard_state").insert({
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "card_id": card_id,
                        "box": new_box,
                        "next_review_at": next_review,
                        "times_correct": new_tc,
                        "times_wrong": new_tw,
                        "updated_at": now_iso,
                    }).execute()
            except Exception as e:
                print(f"[WIB] update_leitner_card error: {e}")
        else:
            conn = _get_sqlite()
            if existing:
                conn.execute(
                    """UPDATE user_flashcard_state SET box=?,next_review_at=?,
                       times_correct=?,times_wrong=?,updated_at=?
                       WHERE user_id=? AND card_id=?""",
                    (new_box, next_review, new_tc, new_tw, now_iso, user_id, card_id),
                )
            else:
                conn.execute(
                    """INSERT INTO user_flashcard_state
                       (id,user_id,card_id,box,next_review_at,times_correct,times_wrong,updated_at)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (str(uuid.uuid4()), user_id, card_id, new_box,
                     next_review, new_tc, new_tw, now_iso),
                )
            conn.commit()
            conn.close()


@st.cache_resource
def get_db() -> Database:
    return Database()
