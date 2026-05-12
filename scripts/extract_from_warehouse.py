"""
WIB CFA — Warehouse Extraction Script
======================================
Run this script ONCE to populate the local SQLite database (wib_cfa.db)
with all questions extracted from the Kaplan Schweser PDF warehouse.

Usage (from the wib-cfa/ project root):
    python scripts/extract_from_warehouse.py

Output:
    data/extracted_questions.json   — raw JSON dump
    wib_cfa.db                      — SQLite database populated with questions
"""

import json
import os
import sys
import uuid
from pathlib import Path

# ── Make sure project root is on PYTHONPATH ────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Configure warehouse path ───────────────────────────────────────────────
WAREHOUSE_PATH = Path(r"D:/CLAUDE/Projet CFA/CFA L1")
OUTPUT_JSON    = PROJECT_ROOT / "data" / "extracted_questions.json"


def main():
    # Check pdfplumber is installed
    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        print("ERROR: pdfplumber is not installed.")
        print("  Run: pip install pdfplumber>=0.11.0")
        sys.exit(1)

    # Check warehouse exists
    if not WAREHOUSE_PATH.exists():
        print(f"ERROR: Warehouse not found at {WAREHOUSE_PATH}")
        print("  Please update WAREHOUSE_PATH in this script.")
        sys.exit(1)

    print(f"Warehouse: {WAREHOUSE_PATH}")
    print(f"Output JSON: {OUTPUT_JSON}")

    # ── Extract questions ──────────────────────────────────────────────────
    from src.pdf_extractor import extract_all_topics
    questions = extract_all_topics(WAREHOUSE_PATH, verbose=True)

    if not questions:
        print("\nWARNING: No questions extracted. Check PDF format / paths.")
        sys.exit(0)

    # ── Write JSON output ──────────────────────────────────────────────────
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {len(questions)} questions to {OUTPUT_JSON}")

    # ── Populate SQLite DB ─────────────────────────────────────────────────
    import sqlite3

    db_path = PROJECT_ROOT / "wib_cfa.db"

    # Init schema if needed
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
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
            source TEXT DEFAULT 'Kaplan Schweser'
        );
    """)
    conn.commit()

    inserted = 0
    skipped  = 0

    for q in questions:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO questions
                   (id, topic, subtopic, difficulty, question_en, option_a, option_b, option_c,
                    correct_answer, explanation_en, explanation_fr, source)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    q["topic"], q.get("subtopic", ""), q.get("difficulty", "medium"),
                    q["question_en"], q["option_a"], q["option_b"], q["option_c"],
                    q["correct_answer"],
                    q.get("explanation_en", ""), q.get("explanation_fr", ""),
                    q.get("source", "Kaplan Schweser"),
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    conn.close()

    print(f"Inserted {inserted} questions into {db_path}")
    if skipped:
        print(f"Skipped {skipped} duplicates.")
    print("\nDone! Run `streamlit run streamlit_app.py` to start the app.")


if __name__ == "__main__":
    main()
