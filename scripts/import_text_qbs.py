#!/usr/bin/env python3
"""
Import text-based question banks into Supabase:
  - Folder 7:  EXTRA QB-700MCQs  (source="Extra_QB",   difficulty=medium)
  - Folder 11: KEVIN SIR's MOCK  (source="Kevin_Mock",  difficulty=hard)

Both PDFs have clean text — no Vision needed.

Run: python scripts/import_text_qbs.py [--dry-run] [--source extra|kevin|all]
"""
import sys, re, uuid, json, argparse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import pdfplumber

# ── Paths ────────────────────────────────────────────────────────────────────

BASE = Path(r"D:\CLAUDE\Projet CFA\CFA L1")
EXTRA_PDF  = BASE / "7. EXTRA QB-700MCQs" / "EXTRA 700 MCQs.pdf"
KEVIN_Q1   = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 1 MOCK-Q.pdf"
KEVIN_A1   = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 1 MOCK-A.pdf"
KEVIN_Q2   = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 2 MOCK-Q.pdf"
KEVIN_A2   = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 2 MOCK-A.pdf"

# ── Topic normalisation ───────────────────────────────────────────────────────

CFA_TOPICS = [
    "Ethics & Professional Standards", "Quantitative Methods", "Economics",
    "Financial Statement Analysis", "Corporate Issuers", "Equity Investments",
    "Fixed Income", "Derivatives", "Alternative Investments", "Portfolio Management",
]

SECTION_MAP = {
    r"ethical\s+and\s+professional": "Ethics & Professional Standards",
    r"ethics":                        "Ethics & Professional Standards",
    r"quantitative\s+method":         "Quantitative Methods",
    r"quant":                         "Quantitative Methods",
    r"economic":                      "Economics",
    r"financial\s+report":            "Financial Statement Analysis",
    r"financial\s+statement":         "Financial Statement Analysis",
    r"fsa":                           "Financial Statement Analysis",
    r"corporate\s+(finance|issuer)":  "Corporate Issuers",
    r"equity\s+invest":               "Equity Investments",
    r"equity":                        "Equity Investments",
    r"derivative":                    "Derivatives",
    r"fixed\s+income":                "Fixed Income",
    r"alternative":                   "Alternative Investments",
    r"portfolio":                     "Portfolio Management",
}

KEYWORD_TOPIC = [
    (["gips", "code of ethics", "standard i", "standard ii", "standard iii",
      "standard iv", "standard v", "standard vi", "standard vii", "fiduciary",
      "referral fee", "mosaic theory", "cfa charterholder", "material nonpublic"], "Ethics & Professional Standards"),
    (["present value", "future value", "irr", "npv", "standard deviation",
      "probability", "hypothesis test", "regression", "time series", "covariance",
      "correlation", "geometric mean", "harmonic mean", "z-score", "t-test"], "Quantitative Methods"),
    (["gdp", "inflation", "monetary policy", "fiscal policy", "supply curve",
      "demand curve", "elasticity", "exchange rate", "purchasing power parity",
      "currency", "balance of payments", "trade deficit"], "Economics"),
    (["income statement", "balance sheet", "cash flow statement", "revenue recognition",
      "inventory", "depreciation", "deferred tax", "ifrs", "us gaap", "goodwill",
      "impairment", "operating profit", "ebitda", "accounts receivable"], "Financial Statement Analysis"),
    (["dividend policy", "capital structure", "wacc", "leverage", "cost of equity",
      "cost of debt", "buyback", "m&a", "merger", "acquisition", "capital budgeting",
      "project", "irr", "payback"], "Corporate Issuers"),
    (["p/e ratio", "price-to-book", "ddm", "gordon growth", "intrinsic value",
      "efficient market hypothesis", "ipo", "secondary offering", "market cap",
      "eps", "earnings per share"], "Equity Investments"),
    (["duration", "convexity", "yield to maturity", "coupon bond", "zero coupon",
      "credit spread", "mortgage-backed", "asset-backed", "securitization",
      "collateralized", "floating rate", "term structure"], "Fixed Income"),
    (["call option", "put option", "forward contract", "futures contract",
      "swap", "payoff diagram", "delta", "gamma", "option pricing",
      "binomial model", "black-scholes"], "Derivatives"),
    (["hedge fund", "private equity", "venture capital", "real estate",
      "reit", "commodity", "infrastructure", "natural resource",
      "alternative investment"], "Alternative Investments"),
    (["portfolio management", "efficient frontier", "sharpe ratio",
      "capm", "systematic risk", "unsystematic risk", "asset allocation",
      "rebalancing", "investment policy statement", "risk tolerance"], "Portfolio Management"),
]

def infer_topic(text: str) -> str:
    low = text.lower()
    for kws, topic in KEYWORD_TOPIC:
        if any(kw in low for kw in kws):
            return topic
    return "Ethics & Professional Standards"

def _sanitize(s: str) -> str:
    return (s or "").replace("\x00", "").replace("�", "").strip()

# ── PDF text extraction ───────────────────────────────────────────────────────

def _extract_text(pdf_path: Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

# ── EXTRA 700 parser ─────────────────────────────────────────────────────────
# Pages 1-127 (0-indexed 0-126): questions
# Pages 128-216 (0-indexed 127-215): solutions
# Some solution pages have tripled characters due to PDF font substitution

def _de_triple(s: str) -> str:
    """'QQQUUUAAANNNTTT' → 'QUANT' (PDF font artefact)."""
    if not s or len(s) < 9:
        return s
    sample = s[:60].replace(" ", "")
    if not sample:
        return s
    triples = sum(1 for i in range(0, len(sample)-2, 3) if sample[i] == sample[i+1] == sample[i+2])
    if triples > 0 and triples >= len(sample) // 6:
        return re.sub(r"(.)\1\1", r"\1", s)
    return s

def _extract_text_pages(pdf_path: Path, page_start: int, page_end: int) -> str:
    """Extract text from a range of pages (0-indexed, exclusive end)."""
    with pdfplumber.open(pdf_path) as pdf:
        parts = []
        for i in range(page_start, min(page_end, len(pdf.pages))):
            t = pdf.pages[i].extract_text() or ""
            t = _de_triple(t)
            parts.append(t)
        return "\n".join(parts)

def _parse_extra700() -> list[dict]:
    # Questions: pages 0-126; Solutions: pages 127-215
    q_text = _extract_text_pages(EXTRA_PDF, 0, 127)
    a_text = _extract_text_pages(EXTRA_PDF, 127, 216)
    q_lines = q_text.split("\n")
    a_lines = a_text.split("\n")

    # ── Parse questions ──
    # Each topic section has its OWN numbering 1..N — key by (topic, num)
    raw_questions = {}  # (topic, num) -> {stem, A, B, C}
    current_topic = "Ethics & Professional Standards"
    i = 0
    while i < len(q_lines):
        line = q_lines[i].strip()

        # Topic section header: all-caps line
        if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", line) and not re.match(r"^\d", line):
            t = _match_section(line)
            if t:
                current_topic = t
            i += 1
            continue

        # Question start: "N. [text]"
        m = re.match(r"^(\d+)\.\s+(.+)", line)
        if m:
            qnum = int(m.group(1))
            stem_parts = [m.group(2)]
            i += 1
            while i < len(q_lines):
                nxt = q_lines[i].strip()
                if re.match(r"^[A-C]\.\s+", nxt):
                    break
                if re.match(r"^\d+\.\s+\S", nxt):
                    break
                # Section header — break so outer loop can update topic
                if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", nxt) and _match_section(nxt):
                    break
                stem_parts.append(nxt)
                i += 1
            stem = " ".join(s for s in stem_parts if s)

            opts = {}
            while i < len(q_lines) and len(opts) < 3:
                nxt = q_lines[i].strip()
                om = re.match(r"^([A-C])\.\s+(.+)", nxt)
                if om:
                    letter = om.group(1)
                    opt_parts = [om.group(2)]
                    i += 1
                    while i < len(q_lines):
                        cont = q_lines[i].strip()
                        if re.match(r"^[A-C]\.\s+", cont) or re.match(r"^\d+\.\s+\S", cont):
                            break
                        # Section header — break so outer loop can update topic
                        if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", cont) and _match_section(cont):
                            break
                        if cont and not re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", cont):
                            opt_parts.append(cont)
                        i += 1
                    opts[letter] = " ".join(opt_parts)
                else:
                    break

            if stem and "A" in opts and "B" in opts and "C" in opts:
                key = (current_topic, qnum)
                if key not in raw_questions:  # keep first occurrence
                    raw_questions[key] = {
                        "stem": stem,
                        "A": opts["A"],
                        "B": opts.get("B", ""),
                        "C": opts.get("C", ""),
                    }
        else:
            i += 1

    # ── Parse solutions ──
    # Format: "N. Answer: X [explanation]" or "N. Answer = X ..."
    # Solutions also use per-topic numbering — track topic from section headers
    raw_answers = {}  # (topic, num) -> {correct, expl}
    sol_current_topic = "Ethics & Professional Standards"
    for sol_line in a_lines:
        sl = sol_line.strip()
        # Topic headers in solutions
        if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", sl) and not re.match(r"^\d", sl):
            t = _match_section(sl)
            if t:
                sol_current_topic = t
            continue

    # Now scan solution text with topic tracking via page-by-page approach
    raw_answers = {}
    with pdfplumber.open(EXTRA_PDF) as pdf:
        sol_current_topic = "Ethics & Professional Standards"
        for i in range(127, len(pdf.pages)):
            page_txt = _de_triple(pdf.pages[i].extract_text() or "")
            # Detect FIRST topic header on this page only (prevents mid-page overwrite)
            for ln in page_txt.split("\n"):
                ln = ln.strip()
                if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", ln) and not re.match(r"^\d", ln):
                    t = _match_section(ln)
                    if t:
                        sol_current_topic = t
                        break  # stop at first recognised topic header per page
            # Find all answers on this page
            for am in re.finditer(
                r"(\d{1,3})\.\s+[Aa]nswer\s*[=:]\s*([A-C])\b",
                page_txt,
            ):
                qnum = int(am.group(1))
                letter = am.group(2).upper()
                key = (sol_current_topic, qnum)
                if key not in raw_answers:
                    raw_answers[key] = {"correct": letter, "expl": ""}

    # ── Merge by (topic, num) ──
    questions = []
    for (topic, _), q in sorted(raw_questions.items()):
        key = (topic, _)
        a = raw_answers.get(key)
        if not a:
            continue
        stem = _sanitize(q["stem"])
        inferred = infer_topic(stem + " " + q["A"] + " " + q["B"] + " " + q["C"])
        questions.append({
            "id": str(uuid.uuid4()),
            "topic": inferred or topic,
            "subtopic": None,
            "question_en": stem,
            "option_a": _sanitize(q["A"]),
            "option_b": _sanitize(q["B"]),
            "option_c": _sanitize(q["C"]),
            "correct_answer": a["correct"],
            "explanation_en": _sanitize(a.get("expl", "")),
            "explanation_fr": "",
            "difficulty": "medium",
            "source": "Extra_QB",
        })

    return questions

def _match_section(line: str) -> str:
    low = line.lower()
    for pattern, topic in SECTION_MAP.items():
        if re.search(pattern, low):
            return topic
    return None

# ── KEVIN MOCK parser ─────────────────────────────────────────────────────────
# Q files: "1. [stem]\nA. ...\nB. ...\nC. ..."
# A files: "1. A\n[explanation...]" or "1. A\n..."

def _parse_kevin_session(q_pdf: Path, a_pdf: Path, session: int) -> list[dict]:
    q_text = _extract_text(q_pdf)
    a_text = _extract_text(a_pdf)

    # ── Parse questions ──
    raw_questions = {}
    q_lines = q_text.split("\n")
    current_topic = "Ethics & Professional Standards"
    i = 0
    while i < len(q_lines):
        line = q_lines[i].strip()

        # Section headers
        t = _match_section(line)
        if t and len(line) > 3:
            current_topic = t

        m = re.match(r"^(\d+)\.\s+(.+)", line)
        if m:
            qnum = int(m.group(1))
            stem_parts = [m.group(2)]
            i += 1
            while i < len(q_lines):
                nxt = q_lines[i].strip()
                if re.match(r"^[A-C]\.\s+", nxt):
                    break
                if re.match(r"^\d+\.\s+", nxt):
                    break
                stem_parts.append(nxt)
                i += 1
            stem = " ".join(s for s in stem_parts if s)

            opts = {}
            while i < len(q_lines) and len(opts) < 3:
                nxt = q_lines[i].strip()
                om = re.match(r"^([A-C])\.\s+(.+)", nxt)
                if om:
                    letter = om.group(1)
                    opt_parts = [om.group(2)]
                    i += 1
                    while i < len(q_lines):
                        cont = q_lines[i].strip()
                        if re.match(r"^[A-C]\.\s+", cont) or re.match(r"^\d+\.\s+", cont):
                            break
                        if cont:
                            opt_parts.append(cont)
                        i += 1
                    opts[letter] = " ".join(opt_parts)
                else:
                    break

            if stem and "A" in opts and "B" in opts and "C" in opts:
                raw_questions[qnum] = {
                    "stem": stem,
                    "A": opts["A"],
                    "B": opts.get("B", ""),
                    "C": opts.get("C", ""),
                    "topic": current_topic,
                }
        else:
            i += 1

    # ── Parse answers ──
    raw_answers = {}
    a_lines = a_text.split("\n")
    i = 0
    while i < len(a_lines):
        line = a_lines[i].strip()
        m = re.match(r"^(\d+)\.\s+([A-C])\b", line)
        if m:
            qnum = int(m.group(1))
            letter = m.group(2)
            expl_parts = [line[m.end():].strip()]
            i += 1
            while i < len(a_lines):
                nxt = a_lines[i].strip()
                if re.match(r"^\d+\.\s+[A-C]\b", nxt):
                    break
                expl_parts.append(nxt)
                i += 1
            raw_answers[qnum] = {
                "correct": letter,
                "expl": " ".join(s for s in expl_parts if s)[:400],
            }
        else:
            i += 1

    # ── Merge ──
    questions = []
    for qnum, q in sorted(raw_questions.items()):
        a = raw_answers.get(qnum)
        if not a:
            continue
        stem = _sanitize(q["stem"])
        questions.append({
            "id": str(uuid.uuid4()),
            "topic": infer_topic(stem + " " + q["A"] + " " + q["B"] + " " + q["C"]) or q["topic"],
            "subtopic": None,
            "question_en": stem,
            "option_a": _sanitize(q["A"]),
            "option_b": _sanitize(q["B"]),
            "option_c": _sanitize(q["C"]),
            "correct_answer": a["correct"],
            "explanation_en": _sanitize(a["expl"]),
            "explanation_fr": "",
            "difficulty": "hard",
            "source": "Kevin_Mock",
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
    parser.add_argument("--source", choices=["extra", "kevin", "all"], default="all")
    args = parser.parse_args()

    if not args.dry_run:
        secrets = load_secrets()
        from supabase import create_client
        sb = create_client(secrets["supabase"]["SUPABASE_URL"], secrets["supabase"]["SUPABASE_SERVICE_KEY"])

    total_inserted = 0
    all_questions = []

    if args.source in ("extra", "all"):
        print("\n=== EXTRA 700 MCQs ===")
        qs = _parse_extra700()
        print(f"  Parsed: {len(qs)} questions")
        by_topic = {}
        for q in qs:
            by_topic[q["topic"]] = by_topic.get(q["topic"], 0) + 1
        for t, c in sorted(by_topic.items()):
            print(f"    {t}: {c}")
        all_questions.extend(qs)

    if args.source in ("kevin", "all"):
        print("\n=== KEVIN MOCK Session 1 ===")
        qs1 = _parse_kevin_session(KEVIN_Q1, KEVIN_A1, 1)
        print(f"  Parsed: {len(qs1)} questions")
        all_questions.extend(qs1)

        print("\n=== KEVIN MOCK Session 2 ===")
        qs2 = _parse_kevin_session(KEVIN_Q2, KEVIN_A2, 2)
        print(f"  Parsed: {len(qs2)} questions")
        all_questions.extend(qs2)

    print(f"\nTotal: {len(all_questions)} questions")

    if args.dry_run:
        print("[DRY RUN] Not inserting")
        for src in set(q["source"] for q in all_questions):
            n = sum(1 for q in all_questions if q["source"] == src)
            print(f"  {src}: {n}")
        if all_questions:
            q = all_questions[0]
            print(f"\nSample [{q['source']}][{q['topic']}]: {q['question_en'][:80]}")
            print(f"  A: {q['option_a'][:60]}")
            print(f"  Correct: {q['correct_answer']}")
        return

    for i in range(0, len(all_questions), 100):
        batch = all_questions[i:i+100]
        resp = sb.table("questions").insert(batch).execute()
        total_inserted += len(resp.data)
        print(f"  Inserted {len(resp.data)} (total: {total_inserted})")

    print(f"\nDONE — Inserted: {total_inserted}")

if __name__ == "__main__":
    main()
