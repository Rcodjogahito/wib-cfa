-- WIB CFA Level 1 — Initial Schema
-- Migration: 20260512060018_init_wib_cfa

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email             TEXT UNIQUE NOT NULL,
    first_name        TEXT NOT NULL,
    target_exam_date  DATE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    diagnostic_done   BOOLEAN DEFAULT FALSE,
    diagnostic_score  NUMERIC(5,2)
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ── Questions ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic           TEXT NOT NULL,
    subtopic        TEXT,
    difficulty      TEXT CHECK (difficulty IN ('easy','medium','hard')) DEFAULT 'medium',
    question_en     TEXT NOT NULL,
    option_a        TEXT NOT NULL,
    option_b        TEXT NOT NULL,
    option_c        TEXT NOT NULL,
    correct_answer  CHAR(1) CHECK (correct_answer IN ('A','B','C')) NOT NULL,
    explanation_en  TEXT,
    explanation_fr  TEXT,
    source          TEXT DEFAULT 'WIB Internal'
);
CREATE INDEX IF NOT EXISTS idx_questions_topic      ON questions(topic);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);

-- ── Flashcards ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS flashcards (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic          TEXT NOT NULL,
    concept_en     TEXT NOT NULL,
    definition_en  TEXT NOT NULL,
    definition_fr  TEXT,
    example_en     TEXT,
    formula        TEXT
);
CREATE INDEX IF NOT EXISTS idx_flashcards_topic ON flashcards(topic);

-- ── User Attempts ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_attempts (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
    question_id      UUID REFERENCES questions(id) ON DELETE CASCADE,
    selected_answer  CHAR(1),
    is_correct       BOOLEAN,
    time_spent_sec   INTEGER,
    session_type     TEXT,
    attempted_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON user_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_qid  ON user_attempts(question_id);
CREATE INDEX IF NOT EXISTS idx_attempts_date ON user_attempts(attempted_at);

-- ── User Sessions ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    session_type        TEXT,
    topic               TEXT,
    total_questions     INTEGER,
    correct_answers     INTEGER,
    score_pct           NUMERIC(5,2),
    duration_sec        INTEGER,
    domain_scores_json  JSONB,
    completed_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON user_sessions(completed_at);

-- ── User Progress ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_progress (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
    topic            TEXT NOT NULL,
    total_attempted  INTEGER DEFAULT 0,
    total_correct    INTEGER DEFAULT 0,
    mastery_pct      NUMERIC(5,2) DEFAULT 0,
    last_attempted   TIMESTAMPTZ,
    UNIQUE (user_id, topic)
);
CREATE INDEX IF NOT EXISTS idx_progress_user  ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_topic ON user_progress(topic);

-- ── Row-Level Security ────────────────────────────────────────────────────────
ALTER TABLE users          ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_attempts  ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_progress  ENABLE ROW LEVEL SECURITY;
ALTER TABLE questions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE flashcards     ENABLE ROW LEVEL SECURITY;

-- Public read access for content tables
CREATE POLICY "questions_public_read"  ON questions  FOR SELECT USING (true);
CREATE POLICY "flashcards_public_read" ON flashcards FOR SELECT USING (true);

-- App uses email-based auth (no Supabase Auth JWT), policies open for anon key
CREATE POLICY "users_insert"        ON users         FOR INSERT WITH CHECK (true);
CREATE POLICY "users_select"        ON users         FOR SELECT USING (true);
CREATE POLICY "users_update"        ON users         FOR UPDATE USING (true);
CREATE POLICY "attempts_insert"     ON user_attempts FOR INSERT WITH CHECK (true);
CREATE POLICY "attempts_select"     ON user_attempts FOR SELECT USING (true);
CREATE POLICY "sessions_insert"     ON user_sessions FOR INSERT WITH CHECK (true);
CREATE POLICY "sessions_select"     ON user_sessions FOR SELECT USING (true);
CREATE POLICY "progress_insert"     ON user_progress FOR INSERT WITH CHECK (true);
CREATE POLICY "progress_select"     ON user_progress FOR SELECT USING (true);
CREATE POLICY "progress_update"     ON user_progress FOR UPDATE USING (true);

-- ── Grant anon access (required for Data API) ─────────────────────────────────
GRANT SELECT, INSERT, UPDATE ON users          TO anon;
GRANT SELECT                  ON questions     TO anon;
GRANT SELECT                  ON flashcards    TO anon;
GRANT SELECT, INSERT          ON user_attempts TO anon;
GRANT SELECT, INSERT          ON user_sessions TO anon;
GRANT SELECT, INSERT, UPDATE  ON user_progress TO anon;
