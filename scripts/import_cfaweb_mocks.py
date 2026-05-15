#!/usr/bin/env python3
"""
Import CFA WEB MOCKS (9. CFA WEB MOCKS-900 MCQs) into Supabase.
ANS files are scanned screenshots showing full Q+A on each page → Vision only.
Q text files are skipped (ANS files contain the same question text + answer).

Run: python scripts/import_cfaweb_mocks.py [--dry-run]
"""
import sys, json, time, uuid, base64, re, argparse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import fitz
import anthropic

# ── Paths ────────────────────────────────────────────────────────────────────

BASE_PDF = Path(r"D:\CLAUDE\Projet CFA\CFA L1\9. CFA WEB MOCKS-900 MCQs")
CACHE_DIR = Path(__file__).parent / "_cache_cfaweb_mocks"
CACHE_DIR.mkdir(exist_ok=True)

# ANS files only — each page shows Q stem + options + "A. Correct because..."
ANS_FILES = sorted(BASE_PDF.glob("*ANS*.pdf")) + sorted(BASE_PDF.glob("*Ans*.pdf"))
# Deduplicate
ANS_FILES = list(dict.fromkeys(ANS_FILES))

print("ANS files found:", [f.name for f in ANS_FILES])

# ── Topic normalisation ───────────────────────────────────────────────────────

TOPIC_MAP = {
    "alternative investments": "Alternative Investments",
    "alternative investment": "Alternative Investments",
    "corporate issuers": "Corporate Issuers",
    "corporate finance": "Corporate Issuers",
    "corporate issuer": "Corporate Issuers",
    "derivatives": "Derivatives",
    "economics": "Economics",
    "equity investments": "Equity Investments",
    "equity": "Equity Investments",
    "ethics & professional standards": "Ethics & Professional Standards",
    "ethics and professional standards": "Ethics & Professional Standards",
    "ethical and professional standards": "Ethics & Professional Standards",
    "ethics": "Ethics & Professional Standards",
    "fixed income": "Fixed Income",
    "financial statement analysis": "Financial Statement Analysis",
    "financial reporting and analysis": "Financial Statement Analysis",
    "fsa": "Financial Statement Analysis",
    "portfolio management": "Portfolio Management",
    "quantitative methods": "Quantitative Methods",
    "quantitative": "Quantitative Methods",
}

KEYWORD_TOPIC = [
    (["gips", "cfa institute", "code of ethics", "standard", "fiduciary", "referral", "mosaic"], "Ethics & Professional Standards"),
    (["present value", "future value", "interest rate", "probability", "hypothesis", "regression", "standard deviation", "correlation", "portfolio variance"], "Quantitative Methods"),
    (["gdp", "inflation", "monetary policy", "fiscal policy", "supply", "demand", "elasticity", "exchange rate", "currency"], "Economics"),
    (["revenue recognition", "income statement", "balance sheet", "cash flow", "depreciation", "inventory", "deferred", "ifrs", "gaap"], "Financial Statement Analysis"),
    (["dividend", "capital structure", "wacc", "leverage", "cost of capital", "buyback", "m&a", "merger"], "Corporate Issuers"),
    (["p/e", "price-to-earnings", "ddm", "gordon growth", "intrinsic value", "ipo", "secondary market", "market efficiency"], "Equity Investments"),
    (["duration", "convexity", "bond", "coupon", "yield to maturity", "spread", "credit rating", "mortgage", "securitization"], "Fixed Income"),
    (["option", "forward", "future", "swap", "call", "put", "payoff", "hedge", "derivative"], "Derivatives"),
    (["hedge fund", "private equity", "real estate", "reit", "commodity", "infrastructure", "alternative"], "Alternative Investments"),
    (["portfolio", "efficient frontier", "sharpe", "capm", "systematic risk", "asset allocation", "diversification", "beta"], "Portfolio Management"),
]

def _infer_topic(text: str) -> str:
    if not text:
        return None
    low = text.lower()
    for kws, topic in KEYWORD_TOPIC:
        if any(kw in low for kw in kws):
            return topic
    return None

def _norm_topic(raw: str) -> str:
    if not raw:
        return None
    s = raw.lower().strip()
    for k, v in TOPIC_MAP.items():
        if k in s:
            return v
    return None

def _sanitize(s: str) -> str:
    if not s:
        return ""
    return s.replace("\x00", "").replace("�", "").strip()

# ── Claude Vision ─────────────────────────────────────────────────────────────

ANS_PROMPT = """You are extracting a CFA Level 1 mock exam question from a scanned answer-key page.

Each page shows ONE question with its full text, answer options A/B/C, and the solution.
The correct answer is marked as "Correct" (bolded) next to the letter, or prefixed with "A. Correct because..."

Return ONLY valid JSON — no markdown, no explanation:

{
  "qnum": <integer question number from "Question N of M", or null if not found>,
  "topic": "<CFA topic if visible in 'Guidance for...' section or page header, else null>",
  "stem": "<full question text>",
  "A": "<option A text>",
  "B": "<option B text>",
  "C": "<option C text>",
  "correct": "<exactly 'A', 'B', or 'C'>",
  "expl": "<one sentence explaining why the correct answer is right>"
}

If the page is blank, a cover page, or doesn't contain a complete question with answer:
{"page_type": "other"}

KEY RULES:
- The correct answer is the one labelled 'Correct' in the Solution section
- Include the full question stem (may span multiple paragraphs)
- topic examples: 'Ethics & Professional Standards', 'Fixed Income', 'Economics', etc.
"""

def _page_to_png(page, zoom=2.0) -> bytes:
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")

_RETRY_DELAYS = [30, 60, 120, 180]

def _call_vision(client, img_bytes: bytes, attempt=0) -> dict:
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
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
                    {"type": "text", "text": ANS_PROMPT},
                ],
            }],
        )
        text = r.content[0].text.strip()
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
        return {"page_type": "other"}

def process_ans_file(pdf_path: Path, client) -> list[dict]:
    """Process one ANS PDF and return a list of question dicts."""
    cache = CACHE_DIR / f"{pdf_path.stem.replace(' ', '_').replace('(','').replace(')','')}.json"
    if cache.exists():
        print(f"    [cache] {cache.name}")
        return json.loads(cache.read_text(encoding="utf-8"))

    doc = fitz.open(str(pdf_path))
    results = []
    for i, page in enumerate(doc):
        img = _page_to_png(page)
        data = _call_vision(client, img)
        data["page_idx"] = i
        results.append(data)
        if (i + 1) % 10 == 0:
            print(f"      page {i+1}/{len(doc)}", end="\r")
        time.sleep(2.0)  # ~30 pages/min — stay well under rate limits

    doc.close()
    cache.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results

def pages_to_questions(pages: list[dict], mock_name: str) -> list[dict]:
    """Convert Vision page results to question rows."""
    questions = []
    for page in pages:
        if page.get("page_type") == "other":
            continue
        stem = _sanitize(page.get("stem", ""))
        A = _sanitize(page.get("A", ""))
        B = _sanitize(page.get("B", ""))
        C = _sanitize(page.get("C", ""))
        correct = (page.get("correct") or "").upper().strip()
        if not stem or not A or not B or not C or correct not in ("A", "B", "C"):
            continue

        # Topic: prefer explicit, else infer from stem
        raw_topic = page.get("topic")
        topic = _norm_topic(raw_topic) or _infer_topic(stem + " " + A + " " + B + " " + C)
        if not topic:
            topic = "Ethics & Professional Standards"  # most common in mock SS1

        questions.append({
            "id": str(uuid.uuid4()),
            "topic": topic,
            "subtopic": None,
            "question_en": stem,
            "option_a": A,
            "option_b": B,
            "option_c": C,
            "correct_answer": correct,
            "explanation_en": _sanitize(page.get("expl", "")),
            "explanation_fr": "",
            "difficulty": "hard",
            "source": "CFA_WEB",
        })
    return questions

# ── Supabase ─────────────────────────────────────────────────────────────────

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

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    import anthropic as _ant
    creds = json.loads((Path.home() / ".claude" / ".credentials.json").read_text())
    token = creds["claudeAiOauth"]["accessToken"]
    client = _ant.Anthropic(auth_token=token)

    if not args.dry_run:
        secrets = load_secrets()
        from supabase import create_client
        sb = create_client(secrets["supabase"]["SUPABASE_URL"], secrets["supabase"]["SUPABASE_SERVICE_KEY"])

    total_inserted = 0
    all_questions = []

    ans_files = sorted(BASE_PDF.glob("*ANS*.pdf")) + sorted(BASE_PDF.glob("*Ans*.pdf"))
    ans_files = list(dict.fromkeys(ans_files))
    print(f"Found {len(ans_files)} ANS files")

    for ans_pdf in ans_files:
        print(f"\n=== {ans_pdf.name} ===")
        pages = process_ans_file(ans_pdf, client)
        questions = pages_to_questions(pages, ans_pdf.stem)
        print(f"  Extracted: {len(questions)} questions")
        all_questions.extend(questions)

    # Deduplicate by (stem, correct_answer)
    seen = set()
    unique = []
    for q in all_questions:
        key = (q["question_en"][:100], q["correct_answer"])
        if key not in seen:
            seen.add(key)
            unique.append(q)

    print(f"\nTotal unique questions: {len(unique)} (deduped from {len(all_questions)})")

    # Stats by topic
    by_topic = {}
    for q in unique:
        by_topic[q["topic"]] = by_topic.get(q["topic"], 0) + 1
    for t, c in sorted(by_topic.items()):
        print(f"  {t}: {c}")

    if args.dry_run:
        print("\n[DRY RUN] Not inserting")
        if unique:
            q = unique[0]
            print(f"Sample: [{q['topic']}] {q['question_en'][:80]}")
            print(f"  A: {q['option_a'][:60]}")
            print(f"  Correct: {q['correct_answer']}")
        return

    for i in range(0, len(unique), 100):
        batch = unique[i:i+100]
        resp = sb.table("questions").insert(batch).execute()
        total_inserted += len(resp.data)
        print(f"  Inserted {len(resp.data)} (total: {total_inserted})")

    print(f"\nDONE — Inserted: {total_inserted}")

if __name__ == "__main__":
    main()
