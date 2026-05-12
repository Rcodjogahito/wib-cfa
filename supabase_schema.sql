-- WIB CFA Level 1 — Supabase Schema
-- Run this in your Supabase SQL editor to initialise the database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────────────────────────────────────────
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

-- ─────────────────────────────────────────────────────────────────────────────
-- QUESTIONS
-- ─────────────────────────────────────────────────────────────────────────────
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

CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions(difficulty);

-- ─────────────────────────────────────────────────────────────────────────────
-- FLASHCARDS
-- ─────────────────────────────────────────────────────────────────────────────
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

-- ─────────────────────────────────────────────────────────────────────────────
-- USER ATTEMPTS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_attempts (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
    question_id      UUID REFERENCES questions(id) ON DELETE CASCADE,
    selected_answer  CHAR(1),
    is_correct       BOOLEAN,
    time_spent_sec   INTEGER,
    session_type     TEXT,   -- 'quiz', 'diagnostic', 'exam_partial', 'exam_full'
    attempted_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attempts_user  ON user_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_qid   ON user_attempts(question_id);
CREATE INDEX IF NOT EXISTS idx_attempts_date  ON user_attempts(attempted_at);

-- ─────────────────────────────────────────────────────────────────────────────
-- USER SESSIONS
-- ─────────────────────────────────────────────────────────────────────────────
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

-- ─────────────────────────────────────────────────────────────────────────────
-- USER PROGRESS
-- ─────────────────────────────────────────────────────────────────────────────
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

-- ─────────────────────────────────────────────────────────────────────────────
-- Row-Level Security (enable after setting up auth)
-- ─────────────────────────────────────────────────────────────────────────────
-- ALTER TABLE users          ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_attempts  ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_sessions  ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_progress  ENABLE ROW LEVEL SECURITY;
