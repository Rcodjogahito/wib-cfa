"""
WIB CFA — Database layer.
Uses Supabase when credentials are available, falls back to SQLite.
"""

import json
import sqlite3
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import streamlit as st


# ── Connection helpers ────────────────────────────────────────────────────────

def _get_supabase_client():
    """Return a Supabase client if credentials exist, else None."""
    try:
        url = st.secrets.get("supabase", {}).get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
        key = st.secrets.get("supabase", {}).get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_ANON_KEY")
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

class Database:
    """Thin wrapper that routes calls to Supabase or SQLite."""

    def __init__(self):
        self.sb = _get_supabase_client()
        if not self.sb:
            init_sqlite()

    # ── Users ──────────────────────────────────────────────────────────────

    def get_or_create_user(self, email: str, first_name: str) -> Dict:
        email = email.strip().lower()
        if self.sb:
            res = self.sb.table("users").select("*").eq("email", email).execute()
            if res.data:
                return res.data[0]
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

    # ── Questions ──────────────────────────────────────────────────────────

    def get_questions(self, topic: Optional[str] = None,
                      difficulty: Optional[str] = None,
                      n: Optional[int] = None) -> List[Dict]:
        if self.sb:
            q = self.sb.table("questions").select("*")
            if topic and topic != "All":
                q = q.eq("topic", topic)
            if difficulty and difficulty != "All":
                q = q.eq("difficulty", difficulty.lower())
            res = q.execute()
            data = res.data or []
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
        import random
        random.shuffle(data)
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
                   .order("completed_at", desc=True)
                   .execute())
            return res.data or []
        conn = _get_sqlite()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM user_sessions WHERE user_id=? ORDER BY completed_at DESC",
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


@st.cache_resource
def get_db() -> Database:
    return Database()
