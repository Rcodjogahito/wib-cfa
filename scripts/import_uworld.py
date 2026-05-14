#!/usr/bin/env python3
"""
Import UWorld CFA Level 1 questions from PDF into Supabase.

Run from project root:
    python scripts/import_uworld.py [--dry-run]

--dry-run  Parse PDFs and print counts without inserting into DB.
"""

import re
import sys
import uuid
import os
from pathlib import Path

import pdfplumber

# ── Config ────────────────────────────────────────────────────────────────────

UWORLD_ROOT = Path(r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs")
SECRETS_PATH = Path(r"D:\CLAUDE\Projet CFA\wib-cfa\.streamlit\secrets.toml")

# UWorld folder name → CFA app topic (10 topics)
TOPIC_MAP = {
    "1. Quantitative Methods":      "Quantitative Methods",
    "2. Economics":                 "Economics",
    "3. Portfolio Management":      "Portfolio Management",
    "4. Corporate Issuers":         "Corporate Issuers",
    "5. Financial Statement Analysis": "Financial Statement Analysis",
    "6. Equity Investments":        "Equity Investments",
    "7. Fixed Income":              "Fixed Income",
    "8. Derivatives":               "Derivatives",
    "9. Alternative Investments":   "Alternative Investments",
    "10. Ethics":                   "Ethics & Professional Standards",
}

BATCH_SIZE = 50
DRY_RUN  = "--dry-run" in sys.argv
SQL_MODE = "--sql"     in sys.argv

# ── Credentials ───────────────────────────────────────────────────────────────

def _load_secrets(path: Path) -> dict:
    """Minimal TOML parser — reads [section] / key = "value" pairs."""
    result: dict = {}
    section = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                result[section] = {}
            elif "=" in line and section:
                k, _, v = line.partition("=")
                result[section][k.strip()] = v.strip().strip('"').strip("'")
    return result


def get_supabase_client():
    secrets = _load_secrets(SECRETS_PATH)
    url = secrets["supabase"]["SUPABASE_URL"]
    # Prefer service role key (bypasses RLS) for admin imports
    key = (secrets["supabase"].get("SUPABASE_SERVICE_KEY")
           or secrets["supabase"]["SUPABASE_ANON_KEY"])
    from supabase import create_client
    return create_client(url, key)


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _pdf_text(path: Path) -> str:
    """Concatenate text from all pages of a PDF."""
    chunks = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    chunks.append(t)
    except Exception as e:
        print(f"    [WARN] text error {path.name}: {e}")
    return "\n".join(chunks)


def _pdf_words(path: Path) -> list:
    """Extract words with fontname from all pages."""
    words = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                words.extend(page.extract_words(extra_attrs=["fontname"]))
    except Exception as e:
        print(f"    [WARN] words error {path.name}: {e}")
    return words


# ── Question PDF parser ───────────────────────────────────────────────────────

def parse_question_pdf(path: Path) -> list:
    """
    Parse questions from a UWorld 'ONLY QSTN' PDF.
    Format: 'Question N\\n[text]\\nA. [opt]\\nB. [opt]\\nC. [opt]'
    Returns list of {num, question, option_a, option_b, option_c}.
    """
    text = _pdf_text(path)
    questions = []

    # Split on "Question N" markers — produces [preamble, num1, block1, num2, block2, ...]
    parts = re.split(r"Question\s+(\d+)\n", text)

    for i in range(1, len(parts), 2):
        num = int(parts[i])
        block = (parts[i + 1] if i + 1 < len(parts) else "").strip()

        # Match: question text, then A. B. C. options
        m = re.match(
            r"(.+?)\nA\.\s+(.+?)\nB\.\s+(.+?)\nC\.\s+(.+)",
            block,
            re.DOTALL,
        )
        if not m:
            continue

        q_text   = " ".join(m.group(1).split())
        opt_a    = " ".join(m.group(2).split())
        opt_b    = " ".join(m.group(3).split())
        # Option C: first line only (next Question may follow immediately)
        opt_c    = " ".join(m.group(4).split("\n")[0].split())

        # Basic quality filter
        if len(q_text) < 15 or len(opt_a) < 2 or len(opt_b) < 2 or len(opt_c) < 2:
            continue

        questions.append({
            "num":      num,
            "question": q_text,
            "option_a": opt_a,
            "option_b": opt_b,
            "option_c": opt_c,
        })

    return questions


# ── Answer PDF parser ─────────────────────────────────────────────────────────

_CHECKMARK = ""   # FontAwesome Pro Light checkmark used by UWorld

def parse_answer_pdf(path: Path) -> dict:
    """
    Parse correct answers and explanations from a UWorld answers PDF.

    Correct answer detection: the FontAwesome checkmark (\\uf00c) always appears
    immediately before the correct option letter (A. / B. / C.) in the word stream.

    Returns dict: {q_num: {"correct": "A"|"B"|"C", "explanation": str}}
    """
    words = _pdf_words(path)
    text  = _pdf_text(path)

    # ── Correct answers (checkmark → next option letter) ──────────────────────
    correct_in_order = []
    for i, w in enumerate(words):
        if _CHECKMARK in w["text"]:
            for j in range(i + 1, min(i + 6, len(words))):
                if re.match(r"^[ABC]\.$", words[j]["text"]):
                    correct_in_order.append(words[j]["text"][0])  # 'A', 'B', or 'C'
                    break

    # ── Question numbers ──────────────────────────────────────────────────────
    # Format can be "1. An analyst" OR "1.An analyst" (no space after dot).
    # Require uppercase letter after optional whitespace; exclude option letters
    # A/B/C (they would be "A. text" with exactly one letter then dot+space).
    q_nums = [
        int(m.group(1))
        for m in re.finditer(r"^(\d+)\.\s*([A-Z][^.])", text, re.MULTILINE)
    ]

    # ── Explanations (text between "Explanation" and next question / end) ─────
    explanations = []
    for m in re.finditer(
        r"Explanation\n(.+?)(?=\n\d+\.\s+[A-Z]|\Z)", text, re.DOTALL
    ):
        expl = m.group(1)
        # Strip supplementary blocks (Things to remember, LOS, Copyright …)
        expl = re.split(r"Things to remember:|LOS\s*\n|Copyright", expl)[0]
        # Collapse whitespace
        expl = " ".join(expl.split())
        explanations.append(expl)

    # ── Zip together ──────────────────────────────────────────────────────────
    answers: dict = {}
    for idx, qnum in enumerate(q_nums):
        answers[qnum] = {
            "correct":     correct_in_order[idx] if idx < len(correct_in_order) else None,
            "explanation": explanations[idx]      if idx < len(explanations)     else "",
        }

    return answers


# ── Topic processor ───────────────────────────────────────────────────────────

def process_topic(topic_folder: Path, topic_name: str) -> list:
    """
    Process one UWorld topic folder.
    Pairs each question PDF (in ONLY QSTN/) with its answer PDF (in topic root).
    Returns list of question dicts ready for Supabase insertion.
    """
    q_dir = topic_folder / "ONLY QSTN"
    if not q_dir.exists():
        print(f"  [WARN] 'ONLY QSTN' missing in {topic_folder.name}")
        return []

    results = []
    for q_pdf in sorted(q_dir.glob("*.pdf")):
        subtopic = q_pdf.stem   # e.g. "8.01 Derivative Instrument and Derivative Market Features"
        a_pdf    = topic_folder / (subtopic + " - Answers.pdf")

        if not a_pdf.exists():
            print(f"    [WARN] answer PDF not found: {subtopic} - Answers.pdf")
            continue

        questions = parse_question_pdf(q_pdf)
        answers   = parse_answer_pdf(a_pdf)

        merged = 0
        for q in questions:
            ans = answers.get(q["num"])
            if not ans or not ans["correct"]:
                continue   # skip if correct answer undetectable

            # Clean option text — strip stray single-letter artifacts that
            # sometimes appear at the end of option C in multi-page PDFs
            opt_c = q["option_c"]
            if len(opt_c) <= 2 and opt_c.isupper():
                continue   # clearly truncated

            results.append({
                "id":             str(uuid.uuid4()),
                "topic":          topic_name,
                "subtopic":       subtopic,
                "difficulty":     "hard",
                "question_en":    q["question"],
                "option_a":       q["option_a"],
                "option_b":       q["option_b"],
                "option_c":       opt_c,
                "correct_answer": ans["correct"],
                "explanation_en": ans["explanation"],
                "explanation_fr": "",
                "source":         "UWorld",
            })
            merged += 1

        print(f"    {subtopic}: {len(questions)} Q | {len(answers)} A | {merged} merged")

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def _escape_sql(s: str) -> str:
    """Escape a string value for SQL (double single-quotes)."""
    return str(s).replace("'", "''")


def write_sql(questions: list, out_path: Path) -> None:
    """Write questions as SQL INSERT statements (bypasses RLS via SQL editor)."""
    lines = [
        "-- WIB CFA — UWorld import",
        "-- Run in Supabase SQL Editor (Settings > SQL Editor > New query)",
        "",
    ]
    chunk = 200  # rows per INSERT to stay under SQL editor size limits
    for start in range(0, len(questions), chunk):
        batch = questions[start : start + chunk]
        rows = []
        for q in batch:
            rows.append(
                "('{id}','{topic}','{subtopic}','{difficulty}','{question_en}',"
                "'{option_a}','{option_b}','{option_c}','{correct_answer}',"
                "'{explanation_en}','{explanation_fr}','{source}')".format(
                    id=q["id"],
                    topic=_escape_sql(q["topic"]),
                    subtopic=_escape_sql(q["subtopic"]),
                    difficulty=q["difficulty"],
                    question_en=_escape_sql(q["question_en"]),
                    option_a=_escape_sql(q["option_a"]),
                    option_b=_escape_sql(q["option_b"]),
                    option_c=_escape_sql(q["option_c"]),
                    correct_answer=q["correct_answer"],
                    explanation_en=_escape_sql(q["explanation_en"]),
                    explanation_fr=_escape_sql(q.get("explanation_fr", "")),
                    source=q["source"],
                )
            )
        lines.append(
            "INSERT INTO questions "
            "(id,topic,subtopic,difficulty,question_en,option_a,option_b,option_c,"
            "correct_answer,explanation_en,explanation_fr,source) VALUES"
        )
        lines.append(",\n".join(rows) + ";")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"SQL written -> {out_path}  ({len(questions)} rows, {out_path.stat().st_size // 1024} KB)")


def main():
    mode = "SQL EXPORT" if SQL_MODE else ("DRY RUN" if DRY_RUN else "LIVE INSERT")
    print(f"Mode: {mode}\n")

    all_questions: list = []

    for folder_name, topic_name in TOPIC_MAP.items():
        folder = UWORLD_ROOT / folder_name
        if not folder.exists():
            print(f"[WARN] folder not found: {folder_name}")
            continue

        print(f"{topic_name}:")
        qs = process_topic(folder, topic_name)
        all_questions.extend(qs)
        print(f"  -> {len(qs)} questions\n")

    total = len(all_questions)
    print(f"{'='*50}")
    print(f"Total parsed: {total} questions")

    if DRY_RUN or total == 0:
        print("Dry run — no DB writes.")
        return

    if SQL_MODE:
        sql_out = Path(__file__).parent / "uworld_insert.sql"
        write_sql(all_questions, sql_out)
        return

    # Insert into Supabase
    sb = get_supabase_client()
    inserted = 0
    errors   = 0

    print("Inserting into Supabase...")
    for i in range(0, total, BATCH_SIZE):
        batch = all_questions[i : i + BATCH_SIZE]
        try:
            sb.table("questions").insert(batch).execute()
            inserted += len(batch)
            print(f"  {inserted}/{total}", end="\r")
        except Exception as e:
            print(f"\n  [ERROR] batch {i // BATCH_SIZE}: {e}")
            errors += 1

    print(f"\nDone — inserted: {inserted} | errors: {errors}")


if __name__ == "__main__":
    main()
