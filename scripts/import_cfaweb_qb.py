#!/usr/bin/env python3
"""
Import CFA WEB PAID QB (3. QB CFA WEB PAID-1000 MCQs) into Supabase.
4 scanned PDFs → Claude Vision (Haiku) → Supabase.

Structure per PDF:
  QUESTION PAGES: multiple Qs per page, "Question N of M" numbering (local per topic)
  ANSWER PAGES:   one answer per page, "Answer N of M" + "Answer: X" explicit

Run: python scripts/import_cfaweb_qb.py [--dry-run]
"""
import sys, json, time, uuid, base64, re, argparse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import fitz
import anthropic

# ── Paths ────────────────────────────────────────────────────────────────────

BASE_PDF = Path(r"D:\CLAUDE\Projet CFA\CFA L1\3. QB CFA WEB PAID-1000 MCQs")
CACHE_DIR = Path(__file__).parent / "_cache_cfaweb_qb"
CACHE_DIR.mkdir(exist_ok=True)

PDFS = [
    BASE_PDF / "AI, Corporate, Deriv, Eco.pdf",
    BASE_PDF / "Equity, Ethics.pdf",
    BASE_PDF / "Fixed income, FSA.pdf",
    BASE_PDF / "Portfolio, Quants.pdf",
]

# ── Topic normalisation ───────────────────────────────────────────────────────

TOPIC_MAP = {
    "alternative investments": "Alternative Investments",
    "alternative investment":  "Alternative Investments",
    "alt inv":                 "Alternative Investments",
    "corporate issuers":       "Corporate Issuers",
    "corporate finance":       "Corporate Issuers",
    "corporate issuer":        "Corporate Issuers",
    "derivatives":             "Derivatives",
    "derivative investments":  "Derivatives",
    "derivative":              "Derivatives",
    "economics":               "Economics",
    "equity investments":      "Equity Investments",
    "equity investment":       "Equity Investments",
    "equity":                  "Equity Investments",
    "ethics & professional standards": "Ethics & Professional Standards",
    "ethics and professional standards": "Ethics & Professional Standards",
    "ethical and professional standards": "Ethics & Professional Standards",
    "ethics":                  "Ethics & Professional Standards",
    "fixed income":            "Fixed Income",
    "financial statement analysis": "Financial Statement Analysis",
    "financial reporting and analysis": "Financial Statement Analysis",
    "fsa":                     "Financial Statement Analysis",
    "portfolio management":    "Portfolio Management",
    "portfolio":               "Portfolio Management",
    "quantitative methods":    "Quantitative Methods",
    "quantitative":            "Quantitative Methods",
    "quant":                   "Quantitative Methods",
}

CFA_TOPICS = [
    "Ethics & Professional Standards", "Quantitative Methods", "Economics",
    "Financial Statement Analysis", "Corporate Issuers", "Equity Investments",
    "Fixed Income", "Derivatives", "Alternative Investments", "Portfolio Management",
]

def _norm_topic(raw: str) -> str:
    if not raw:
        return None
    s = raw.lower().strip()
    # Remove suffixes like "Practice Pack", "Practice Pack - Answers", etc.
    s = re.sub(r"\s*(practice pack|– answers|-\s*answers|answers)\s*", "", s).strip()
    for k, v in TOPIC_MAP.items():
        if k in s:
            return v
    # Try individual words
    for k, v in TOPIC_MAP.items():
        if any(w in s for w in k.split()):
            return v
    return None

def _sanitize(s: str) -> str:
    if not s:
        return ""
    return s.replace("\x00", "").replace("�", "").strip()

# ── Claude Vision ─────────────────────────────────────────────────────────────

Q_PROMPT = """You are extracting CFA Level 1 exam content from a scanned PDF page.

RETURN ONLY VALID JSON — no markdown, no explanation.

Determine the page type and extract accordingly:

QUESTION PAGE (shows questions with A/B/C choices, no correct answer marked):
{
  "page_type": "questions",
  "topic": "<section header visible at top, e.g. 'Alternative Investments', or null>",
  "items": [
    {"n": <integer from 'Question N of M'>, "stem": "<question text>", "A": "<option A>", "B": "<option B>", "C": "<option C>"}
  ]
}

ANSWER PAGE (shows 'Answer: X' or '[Letter]. Correct because...', or 'Answer N of M'):
{
  "page_type": "answers",
  "topic": "<section header like 'Alternative Investments Practice Pack - Answers', or null>",
  "items": [
    {"n": <integer from 'Answer N of M'>, "correct": "<letter A/B/C>", "expl": "<one sentence why>"}
  ]
}

OTHER (cover, blank, table of contents, etc.):
{"page_type": "other"}

KEY RULES:
- Use the LOCAL number from "Question N of M" or "Answer N of M"
- If multiple questions or answers appear on the same page, include ALL in items[]
- correct must be exactly "A", "B", or "C"
- If "Correct" is bolded next to a letter in the solution, that is the correct letter
- If you see "Answer: C" explicitly, use that letter
"""

def _page_to_png(page, zoom=2.0) -> bytes:
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")

_RETRY_DELAYS = [30, 60, 120, 180]  # seconds to wait on 429 before each retry

def _call_vision(client: anthropic.Anthropic, img_bytes: bytes, attempt=0) -> dict:
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64.b64encode(img_bytes).decode(),
                        },
                    },
                    {"type": "text", "text": Q_PROMPT},
                ],
            }],
        )
        text = r.content[0].text.strip()
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except Exception as e:
        err_str = str(e)
        is_rate_limit = "429" in err_str or "rate_limit" in err_str
        if is_rate_limit and attempt < len(_RETRY_DELAYS):
            wait = _RETRY_DELAYS[attempt]
            print(f"  [RATE LIMIT] waiting {wait}s before retry {attempt+1}...")
            time.sleep(wait)
            return _call_vision(client, img_bytes, attempt + 1)
        if not is_rate_limit and attempt < 2:
            time.sleep(5)
            return _call_vision(client, img_bytes, attempt + 1)
        print(f"  [WARN] Vision parse failed: {e}")
        return {"page_type": "other"}

# ── Per-PDF processing ────────────────────────────────────────────────────────

def process_pdf(pdf_path: Path, client: anthropic.Anthropic) -> list[dict]:
    """Extract all questions from one PDF (with cache)."""
    cache = CACHE_DIR / f"{pdf_path.stem.replace(' ', '_')}.json"
    if cache.exists():
        print(f"  [cache] {cache.name}")
        return json.loads(cache.read_text(encoding="utf-8"))

    doc = fitz.open(str(pdf_path))
    n_pages = len(doc)
    print(f"  Processing {n_pages} pages...")

    pages_raw = []
    for i in range(n_pages):
        page = doc[i]
        img = _page_to_png(page)
        data = _call_vision(client, img)
        data["page_idx"] = i
        pages_raw.append(data)
        if (i + 1) % 10 == 0:
            print(f"    {i+1}/{n_pages}", end="\r")
        time.sleep(2.0)  # ~30 pages/min — stay well under rate limits

    doc.close()
    cache.write_text(json.dumps(pages_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved cache: {cache.name}")
    return pages_raw

def merge_qa(pages_raw: list[dict]) -> list[dict]:
    """Match questions to answers by (topic, local_number)."""
    questions = {}  # (topic, n) -> {stem, A, B, C}
    answers = {}    # (topic, n) -> {correct, expl}
    current_topic = None

    for page in pages_raw:
        raw_topic = page.get("topic")
        if raw_topic:
            t = _norm_topic(raw_topic)
            if t:
                current_topic = t

        pt = page.get("page_type")
        items = page.get("items") or []

        if pt == "questions":
            for item in items:
                n = item.get("n")
                if not n or not item.get("stem"):
                    continue
                key = (current_topic, int(n))
                questions[key] = {
                    "stem": _sanitize(item.get("stem", "")),
                    "A": _sanitize(item.get("A", "")),
                    "B": _sanitize(item.get("B", "")),
                    "C": _sanitize(item.get("C", "")),
                }
        elif pt == "answers":
            for item in items:
                n = item.get("n")
                correct = (item.get("correct") or "").upper().strip()
                if not n or correct not in ("A", "B", "C"):
                    continue
                key = (current_topic, int(n))
                answers[key] = {
                    "correct": correct,
                    "expl": _sanitize(item.get("expl", "")),
                }

    merged = []
    for (topic, n), q in sorted(questions.items(), key=lambda x: (x[0][0] or "", x[0][1])):
        a = answers.get((topic, n))
        if not a:
            continue
        if not q["stem"] or not q["A"] or not q["B"] or not q["C"]:
            continue
        merged.append({
            "id": str(uuid.uuid4()),
            "topic": topic or "Quantitative Methods",
            "subtopic": None,
            "question_en": q["stem"],
            "option_a": q["A"],
            "option_b": q["B"],
            "option_c": q["C"],
            "correct_answer": a["correct"],
            "explanation_en": a["expl"],
            "explanation_fr": "",
            "difficulty": "hard",
            "source": "CFA_WEB",
        })

    return merged

# ── Supabase insert ───────────────────────────────────────────────────────────

def load_secrets():
    p = Path(".streamlit/secrets.toml")
    result = {}; section = None
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]; result[section] = {}
            elif "=" in line and section:
                k, _, v = line.partition("=")
                result[section][k.strip()] = v.strip().strip('"').strip("'")
    return result

def insert_batch(sb, rows: list[dict]) -> int:
    if not rows:
        return 0
    resp = sb.table("questions").insert(rows).execute()
    return len(resp.data)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Setup clients
    import anthropic as _ant
    creds = json.loads((Path.home() / ".claude" / ".credentials.json").read_text())
    token = creds["claudeAiOauth"]["accessToken"]
    client = _ant.Anthropic(auth_token=token)

    if not args.dry_run:
        secrets = load_secrets()
        from supabase import create_client
        sb = create_client(secrets["supabase"]["SUPABASE_URL"], secrets["supabase"]["SUPABASE_SERVICE_KEY"])

    total_inserted = 0

    for pdf_path in PDFS:
        print(f"\n=== {pdf_path.name} ===")
        pages_raw = process_pdf(pdf_path, client)
        questions = merge_qa(pages_raw)
        print(f"  Matched: {len(questions)} questions")

        # Stats by topic
        by_topic = {}
        for q in questions:
            by_topic[q["topic"]] = by_topic.get(q["topic"], 0) + 1
        for t, c in sorted(by_topic.items()):
            print(f"    {t}: {c}")

        if args.dry_run:
            print(f"  [DRY RUN] Would insert {len(questions)}")
            if questions:
                q = questions[0]
                print(f"  Sample: [{q['topic']}] {q['question_en'][:80]}")
                print(f"    A: {q['option_a'][:60]}")
                print(f"    Correct: {q['correct_answer']}")
            continue

        # Insert in batches of 100
        for i in range(0, len(questions), 100):
            batch = questions[i:i+100]
            n = insert_batch(sb, batch)
            total_inserted += n
            print(f"  Inserted {n} (total: {total_inserted})")

    print(f"\n{'='*50}")
    print(f"DONE — Total inserted: {total_inserted}")

if __name__ == "__main__":
    main()
