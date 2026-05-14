#!/usr/bin/env python3
"""
Import Kaplan CFA Level 1 questions from PDF into Supabase.

Handles two Kaplan sets:
  - 2. QB KAPLAN-3000 MCQs  (per-reading PDFs in QSTN WITH ANS/)
  - 8. KAPLAN MOCK-1100 MCQs (Mock Exam N - Answers.pdf)

Both share the same format:
  Question #N of M
  Question ID: XXXXXXX
  [question text]
  A) option
  B) option
  C) option
  Explanation
  [explanation text]
  (Module X.Y, LOS Z.a)

Correct answer is inferred from explanation via word overlap.

Run from project root:
    python scripts/import_kaplan.py [--dry-run] [--sql]
"""

import re
import sys
import uuid
import os
from pathlib import Path

import pdfplumber

# ── Config ────────────────────────────────────────────────────────────────────

KAPLAN_ROOT  = Path(r"D:\CLAUDE\Projet CFA\CFA L1\2. QB KAPLAN-3000 MCQs")
MOCK_ROOT    = Path(r"D:\CLAUDE\Projet CFA\CFA L1\8. KAPLAN MOCK-1100 MCQs")
SECRETS_PATH = Path(r"D:\CLAUDE\Projet CFA\wib-cfa\.streamlit\secrets.toml")

# Map Kaplan folder names to app topics
KAPLAN_TOPIC_MAP = {
    "Alternative Investment":            "Alternative Investments",
    "Corporate issuers":                 "Corporate Issuers",
    "Derivatives":                       "Derivatives",
    "Economics":                         "Economics",
    "Equity Investments":                "Equity Investments",
    "Ethical and professional standard": "Ethics & Professional Standards",
    "Financial statement analysis":      "Financial Statement Analysis",
    "Fixed income":                      "Fixed Income",
    "Portofolio management part 1":      "Portfolio Management",
    "Portofolio management part 2":      "Portfolio Management",
    "Quantitative Method":               "Quantitative Methods",
}

BATCH_SIZE = 50
DRY_RUN  = "--dry-run" in sys.argv
SQL_MODE = "--sql"     in sys.argv

# ── Stopwords ─────────────────────────────────────────────────────────────────

_STOPS = {
    'the','a','an','and','or','but','is','are','was','were','be','been',
    'being','have','has','had','do','does','did','to','of','in','for',
    'on','with','as','at','by','from','that','this','which','who','it',
    'its','will','would','could','should','may','might','can','not','no',
    'more','than','less','most','least','such','also','both','all','any',
    'each','if','when','then','they','their','them','there','these','those',
    'we','our','you','your','he','she','his','her','what','how','why',
    'about','into','through','after','before','between','same','other',
    'however','therefore','because','since','while','although','only',
}


def _tokenize(text: str) -> list:
    words = re.findall(r'[a-z]+', text.lower())
    return [w for w in words if w not in _STOPS and len(w) > 2]


# ── Credentials ───────────────────────────────────────────────────────────────

def _load_secrets(path: Path) -> dict:
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
    key = (secrets["supabase"].get("SUPABASE_SERVICE_KEY")
           or secrets["supabase"]["SUPABASE_ANON_KEY"])
    from supabase import create_client
    return create_client(url, key)


# ── PDF text extraction ───────────────────────────────────────────────────────

def _pdf_text(path: Path) -> str:
    chunks = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    chunks.append(t)
    except Exception as e:
        print(f"    [WARN] {path.name}: {e}")
    return "\n".join(chunks)


# ── Correct answer detection ──────────────────────────────────────────────────

_NEGATED_PATTERNS = re.compile(
    r'\b(least accurate|least likely|incorrect|not accurate|not correct|'
    r'does not|is not|is false|not true|except|inaccurate|violates)\b',
    re.IGNORECASE
)


def _detect_correct(q_text: str, opt_a: str, opt_b: str, opt_c: str,
                    explanation: str) -> str:
    """
    Infer the correct answer letter from the explanation using word overlap.

    Kaplan explanations always open by stating the TRUE fact about the subject.
    For normal questions: the correct option matches these true facts (max overlap).
    For 'least accurate' questions: the wrong option (= correct answer) is the one
    that CONTRADICTS the true fact stated in the explanation (min overlap).
    """
    is_negated = bool(_NEGATED_PATTERNS.search(q_text))

    # Use first two sentences of explanation (most concentrated signal)
    sentences = re.split(r'(?<=[.!?])\s+', explanation.strip())
    expl_core = " ".join(sentences[:2]) if sentences else explanation
    expl_words = set(_tokenize(expl_core))

    scores: dict = {}
    for letter, opt in [("A", opt_a), ("B", opt_b), ("C", opt_c)]:
        opt_words = set(_tokenize(opt))
        if not opt_words:
            scores[letter] = 0.0
        else:
            scores[letter] = len(opt_words & expl_words) / len(opt_words)

    if is_negated:
        # correct answer = the option least supported by explanation (it's the wrong statement)
        return min(scores, key=scores.get)
    else:
        return max(scores, key=scores.get)


# ── Kaplan PDF parser ─────────────────────────────────────────────────────────

def parse_kaplan_pdf(path: Path) -> list:
    """
    Parse questions from a Kaplan 'QSTN WITH ANS' or Mock Answers PDF.

    Format:
        Question #N of M
        Question ID: XXXXXXX
        [question text]
        A) option_a [multiline possible]
        B) option_b [multiline possible]
        C) option_c [multiline possible]
        Explanation
        [explanation text]
        (Module X.Y, LOS Z.a)

    Returns list of {num, question, option_a, option_b, option_c, explanation}.
    """
    text = _pdf_text(path)
    questions = []

    # Split on "Question #N of M"
    parts = re.split(r"Question\s+#(\d+)\s+of\s+\d+\s*\n", text)

    for i in range(1, len(parts), 2):
        num   = int(parts[i])
        block = (parts[i + 1] if i + 1 < len(parts) else "").strip()

        # Remove "Question ID: XXXXXXX" header
        block = re.sub(r"Question\s+ID:\s*\d+\s*\n?", "", block, count=1)

        # Match: question text, then A) B) C) Explanation
        m = re.match(
            r"(.+?)\nA\)\s+(.+?)\nB\)\s+(.+?)\nC\)\s+(.+?)\nExplanation\n(.+)",
            block,
            re.DOTALL,
        )
        if not m:
            continue

        q_text  = " ".join(m.group(1).split())
        opt_a   = " ".join(m.group(2).split())
        opt_b   = " ".join(m.group(3).split())
        opt_c   = " ".join(m.group(4).split())
        expl    = m.group(5).strip()

        # Extract module number before stripping
        mod_match = re.search(r"\(Module\s+(\d+)", expl)
        module_num = int(mod_match.group(1)) if mod_match else None

        # Strip "(Module X.Y, LOS Z.a)" and beyond
        expl = re.split(r"\(Module\s+\d+|\nQuestion\s+#", expl)[0].strip()
        expl = " ".join(expl.split())

        if len(q_text) < 10 or len(opt_a) < 2 or len(opt_b) < 2 or len(opt_c) < 2:
            continue

        questions.append({
            "num":        num,
            "question":   q_text,
            "option_a":   opt_a,
            "option_b":   opt_b,
            "option_c":   opt_c,
            "explanation":expl,
            "module":     module_num,
        })

    return questions


# ── Process Kaplan QB ─────────────────────────────────────────────────────────

def process_kaplan_qb() -> list:
    """Process 2. QB KAPLAN — per-topic QSTN WITH ANS PDFs."""
    ans_dir = KAPLAN_ROOT / "QSTN WITH ANS"
    if not ans_dir.exists():
        print(f"[WARN] Not found: {ans_dir}")
        return []

    all_qs: list = []
    print("Kaplan QB:")

    for folder_name, topic_name in KAPLAN_TOPIC_MAP.items():
        topic_dir = ans_dir / folder_name
        if not topic_dir.exists():
            print(f"  [WARN] Missing: {folder_name}")
            continue

        topic_total = 0
        for pdf in sorted(topic_dir.glob("*.pdf")):
            # Skip standalone question-only PDFs (no answers)
            if not pdf.name.endswith("- Answers.pdf"):
                continue

            subtopic = pdf.stem.replace(" - Answers", "")
            qs = parse_kaplan_pdf(pdf)
            merged = 0

            for q in qs:
                correct = _detect_correct(
                    q["question"], q["option_a"], q["option_b"], q["option_c"],
                    q["explanation"]
                )
                all_qs.append({
                    "id":             str(uuid.uuid4()),
                    "topic":          topic_name,
                    "subtopic":       subtopic,
                    "difficulty":     "medium",
                    "question_en":    q["question"],
                    "option_a":       q["option_a"],
                    "option_b":       q["option_b"],
                    "option_c":       q["option_c"],
                    "correct_answer": correct,
                    "explanation_en": q["explanation"],
                    "explanation_fr": "",
                    "source":         "Kaplan",
                })
                merged += 1
            topic_total += merged
            print(f"    {subtopic}: {merged} questions")

        print(f"  {folder_name}: {topic_total} questions")

    return all_qs


# ── Module → Topic mapping (Kaplan L1 2024 module numbering) ─────────────────

def _module_to_topic(module: int | None) -> str:
    """Map Kaplan module number to CFA app topic."""
    if module is None:
        return "Quantitative Methods"
    if module <= 11:
        return "Quantitative Methods"
    if module <= 19:
        return "Economics"
    if module <= 21:
        return "Portfolio Management"
    if module <= 28:
        return "Corporate Issuers"
    if module <= 40:
        return "Financial Statement Analysis"
    if module <= 48:
        return "Equity Investments"
    if module <= 67:
        return "Fixed Income"
    if module <= 77:
        return "Derivatives"
    if module <= 84:
        return "Alternative Investments"
    return "Ethics & Professional Standards"


# ── Process Kaplan Mocks ──────────────────────────────────────────────────────

def process_kaplan_mocks() -> list:
    """Process 8. KAPLAN MOCK — Mock Exam N - Answers.pdf files."""
    if not MOCK_ROOT.exists():
        print(f"[WARN] Not found: {MOCK_ROOT}")
        return []

    all_qs: list = []
    print("Kaplan Mocks:")

    for pdf in sorted(MOCK_ROOT.glob("Mock Exam * - Answers.pdf")):
        exam_name = pdf.stem.replace(" - Answers", "")
        qs = parse_kaplan_pdf(pdf)
        merged = 0

        for q in qs:
            correct = _detect_correct(
                q["question"], q["option_a"], q["option_b"], q["option_c"],
                q["explanation"]
            )
            topic = _module_to_topic(q.get("module"))
            all_qs.append({
                "id":             str(uuid.uuid4()),
                "topic":          topic,
                "subtopic":       exam_name,
                "difficulty":     "hard",
                "question_en":    q["question"],
                "option_a":       q["option_a"],
                "option_b":       q["option_b"],
                "option_c":       q["option_c"],
                "correct_answer": correct,
                "explanation_en": q["explanation"],
                "explanation_fr": "",
                "source":         "Kaplan",
            })
            merged += 1

        print(f"  {exam_name}: {merged} questions")

    return all_qs


# ── SQL export ────────────────────────────────────────────────────────────────

def _escape_sql(s: str) -> str:
    return str(s).replace("'", "''")


def write_sql(questions: list, out_path: Path) -> None:
    lines = [
        "-- WIB CFA — Kaplan import",
        "-- Run in Supabase SQL Editor",
        "",
    ]
    chunk = 100
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
                    explanation_fr=q.get("explanation_fr", ""),
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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    mode = "SQL EXPORT" if SQL_MODE else ("DRY RUN" if DRY_RUN else "LIVE INSERT")
    print(f"Mode: {mode}\n")

    all_questions: list = []
    all_questions.extend(process_kaplan_qb())
    all_questions.extend(process_kaplan_mocks())

    total = len(all_questions)
    print(f"\n{'='*50}")
    print(f"Total parsed: {total} questions")

    if DRY_RUN or total == 0:
        print("Dry run — no DB writes.")
        return

    if SQL_MODE:
        sql_out = Path(__file__).parent / "kaplan_insert.sql"
        write_sql(all_questions, sql_out)
        return

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
