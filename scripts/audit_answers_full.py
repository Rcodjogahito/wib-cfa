#!/usr/bin/env python3
"""
Full answer-consistency audit.

Two passes:
  1. NLP audit  — detect_correct() on explanation_en vs stored correct_answer
  2. PDF audit  — compare options + correct_answer against source PDFs
                  (UWorld, Kaplan, Extra_QB, Kevin_Mock)

Usage:
    python scripts/audit_answers_full.py --dump C:\\Users\\codjo\\AppData\\Local\\Temp\\wib_questions_dump.json
    python scripts/audit_answers_full.py --dump ... --apply   # write corrections JSON
"""
import sys, re, json, argparse, warnings, logging, threading
from pathlib import Path
import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)
for _n in list(logging.Logger.manager.loggerDict):
    logging.getLogger(_n).setLevel(logging.CRITICAL)

BASE         = Path(r"D:\CLAUDE\Projet CFA\CFA L1")
UWORLD_ROOT  = BASE / "6. TOUGH QB UWORLD-2000 MCQs"
KAPLAN_ROOT  = BASE / "2. QB KAPLAN-3000 MCQs"
MOCK_ROOT    = BASE / "8. KAPLAN MOCK-1100 MCQs"
EXTRA_PDF    = BASE / "7. EXTRA QB-700MCQs" / "EXTRA 700 MCQs.pdf"
KEVIN_Q1     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 1 MOCK-Q.pdf"
KEVIN_A1     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 1 MOCK-A.pdf"
KEVIN_Q2     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 2 MOCK-Q.pdf"
KEVIN_A2     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 2 MOCK-A.pdf"

_PDF_TIMEOUT = 60
_CHECKMARK   = ""  # FontAwesome Pro Light checkmark used by UWorld

_UWORLD_ANSWERS_SKIP = {
    "1.03 Statistical Measures of Asset Returns",
    "5.12 Introduction to Financial Statement Modeling",
    "11.03 Guidance For Standards I–VII",
}

UWORLD_TOPIC_MAP = {
    "1. Quantitative Methods":         "Quantitative Methods",
    "2. Economics":                    "Economics",
    "3. Portfolio Management":         "Portfolio Management",
    "4. Corporate Issuers":            "Corporate Issuers",
    "5. Financial Statement Analysis": "Financial Statement Analysis",
    "6. Equity Investments":           "Equity Investments",
    "7. Fixed Income":                 "Fixed Income",
    "8. Derivatives":                  "Derivatives",
    "9. Alternative Investments":      "Alternative Investments",
    "10. Ethics":                      "Ethics & Professional Standards",
}

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

# ── Text helpers ───────────────────────────────────────────────────────────────

def _sanitize(s):
    return (s or "").replace("\x00", "").replace("�", "").strip()

def _strip_tables(text):
    lines = [l for l in (text or "").split("\n") if not l.strip().startswith("|")]
    return " ".join(l.strip() for l in lines if l.strip())

def _norm(text, length=120):
    flat = _strip_tables(text)
    flat = re.sub(r"\s+", " ", flat.lower()).strip()
    return flat[:length]

def _sim(a, b):
    wa = set(re.findall(r"[a-z]+", a.lower()))
    wb = set(re.findall(r"[a-z]+", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))

def _norm_opt(text):
    return re.sub(r"\s+", " ", (text or "").strip())

_LENS = [120, 80, 60]

def _build_lookup(items, min_length=60):
    lut = {}
    for item in items:
        for L in _LENS:
            if L < min_length:
                continue
            key = (L, _norm(item["q_text"], L))
            lut.setdefault(key, []).append(item)
    return lut

def _opts_avg_sim(db_row, pdf_item):
    total = 0.0
    for field in ("option_a", "option_b", "option_c"):
        total += _sim(_norm_opt(db_row.get(field, "")), _norm_opt(pdf_item.get(field, "")))
    return total / 3.0

def _lookup(lut, db_q_text, min_length=60, db_row=None):
    for L in _LENS:
        if L < min_length:
            continue
        key = (L, _norm(db_q_text, L))
        candidates = lut.get(key)
        if not candidates:
            continue
        if len(candidates) == 1 or db_row is None:
            return candidates[0], L
        best = max(candidates, key=lambda x: _opts_avg_sim(db_row, x))
        return best, L
    return None, 0

# ── PDF helpers ────────────────────────────────────────────────────────────────

def _pdf_text(path):
    chunks = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    chunks.append(t)
    except Exception as e:
        print(f"    [WARN] {path.name}: {e}", flush=True)
    return "\n".join(chunks)

def _pdf_text_safe(path):
    buf, err = [], []
    def _run():
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        buf.append(t)
        except Exception as e:
            err.append(str(e))
    t = threading.Thread(target=_run, daemon=True)
    t.start(); t.join(timeout=_PDF_TIMEOUT)
    if t.is_alive():
        print(f"    [SKIP timeout] {path.name}", flush=True)
        return ""
    if err:
        print(f"    [WARN] {path.name}: {err[0]}", flush=True)
    return "\n".join(buf)

def _pdf_words_safe(path):
    buf, err = [], []
    def _run():
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    buf.extend(page.extract_words(extra_attrs=["fontname"]))
        except Exception as e:
            err.append(str(e))
    t = threading.Thread(target=_run, daemon=True)
    t.start(); t.join(timeout=_PDF_TIMEOUT)
    if t.is_alive():
        print(f"    [SKIP timeout] {path.name}", flush=True)
        return []
    return buf

# ── NLP audit (Pass 1 + 2 = high-confidence) ──────────────────────────────────

_STOPS = {
    'the','a','an','and','or','but','is','are','was','were','be','been','being',
    'have','has','had','do','does','did','to','of','in','for','on','with','as',
    'at','by','from','that','this','which','who','it','its','will','would',
    'could','should','may','might','can','not','no','more','than','less','most',
    'least','such','also','both','all','any','each','if','when','then','they',
    'their','them','there','these','those','we','our','you','your','he','she',
    'his','her','what','how','why','about','into','through','after','before',
    'between','same','other','however','therefore','because','since','while',
    'although','only','typically','generally','usually','often','always','never',
    'sometimes','relatively','compared','similar','different','another',
    'include','includes','included','using','used','use','known','based',
}

def _stem(w):
    for suf in ('ations','ation','tions','tion','ments','ment','ness',
                'ing','ings','ed','ers','er','es','s'):
        if len(w) > len(suf) + 4 and w.endswith(suf):
            return w[:-len(suf)]
    return w

def _tokenize(text):
    return [_stem(w) for w in re.findall(r'[a-z]+', text.lower())
            if w not in _STOPS and len(w) > 3]

def _fuzzy(opt_word, expl_words):
    if len(opt_word) < 5:
        return opt_word in expl_words
    for ew in expl_words:
        if ew.startswith(opt_word) or opt_word.startswith(ew):
            return True
        if len(opt_word) >= 6 and len(ew) >= 6:
            common = sum(a == b for a, b in zip(opt_word, ew))
            if common / max(len(opt_word), len(ew)) >= 0.85:
                return True
    return False

def detect_correct_nlp(q_text, opt_a, opt_b, opt_c, explanation):
    if not explanation or len(explanation.strip()) < 15:
        return None, 0, 0.0
    expl = explanation.strip()
    opts = {"A": (opt_a or "").strip(), "B": (opt_b or "").strip(), "C": (opt_c or "").strip()}

    # Pass 1: explicit letter
    for letter in ("A", "B", "C"):
        if re.search(
            rf'\b(correct\s+answer\s+is\s+{letter}|answer\s+is\s+{letter}|'
            rf'{letter}\s+is\s+(the\s+)?(correct|right|best|answer)|'
            rf'(choose|select)\s+{letter}\b|'
            rf'(answer|option|choice)\s*:\s*{letter}\b|'
            rf'{letter}\s+is\s+correct)\b',
            expl, re.IGNORECASE,
        ):
            return letter, 1, 1.0

    # Pass 2: exact option text in first sentence
    first_sent = (re.split(r'(?<=[.!?])\s+', expl) or [""])[0].lower()
    for letter in ("A", "B", "C"):
        opt_clean = opts[letter].lower().rstrip(".").strip()
        if opt_clean and len(opt_clean) > 8 and opt_clean in first_sent:
            return letter, 2, 0.9

    # Pass 3: stemmed overlap (advisory)
    focus = " ".join(re.split(r'(?<=[.!?])\s+', expl)[:3])
    expl_stems = set(_tokenize(focus))
    expl_raw = re.findall(r'[a-z]+', focus.lower())
    scores = {}
    for letter in ("A", "B", "C"):
        opt_stems = list(_tokenize(opts[letter]))
        if not opt_stems:
            scores[letter] = 0.0
            continue
        matched = sum(1 for ow in opt_stems if ow in expl_stems or _fuzzy(ow, expl_raw))
        scores[letter] = matched / len(opt_stems)
    max_s = max(scores.values())
    if max_s >= 0.5:
        winners = [l for l, s in scores.items() if s == max_s]
        if len(winners) == 1:
            return winners[0], 3, max_s
        abs_m = {l: sum(1 for ow in _tokenize(opts[l]) if ow in expl_stems or _fuzzy(ow, expl_raw)) for l in winners}
        best = max(abs_m, key=abs_m.get)
        if abs_m[best] > min(abs_m.values()):
            return best, 3, max_s

    return None, 0, 0.0

def run_nlp_audit(questions):
    p1, p2, p3, ok, nosig = [], [], [], 0, 0
    for row in questions:
        expl = (row.get("explanation_en") or "").strip()
        if len(expl) < 15:
            nosig += 1
            continue
        detected, pass_num, conf = detect_correct_nlp(
            row.get("question_en",""), row.get("option_a",""),
            row.get("option_b",""),   row.get("option_c",""), expl,
        )
        if detected is None:
            nosig += 1
            continue
        stored = (row.get("correct_answer") or "").strip().upper()
        snippet = f"Q: {row.get('question_en','')[:70]}… stored={stored} detected={detected} | Expl: {expl[:80]}…"
        if detected == stored:
            ok += 1
        elif pass_num == 1:
            p1.append({"id": row["id"], "source": row.get("source",""), "stored": stored, "detected": detected, "pass": 1, "conf": conf, "snippet": snippet})
        elif pass_num == 2:
            p2.append({"id": row["id"], "source": row.get("source",""), "stored": stored, "detected": detected, "pass": 2, "conf": conf, "snippet": snippet})
        elif pass_num == 3:
            p3.append({"id": row["id"], "source": row.get("source",""), "stored": stored, "detected": detected, "pass": 3, "conf": conf, "snippet": snippet})
        else:
            ok += 1
    return p1, p2, p3, ok, nosig

# ── UWorld PDF audit ───────────────────────────────────────────────────────────

_QNUM_RE = re.compile(r"^(\d+)\.\s+(.+)", re.DOTALL)
_OPT_RE  = re.compile(r"^([A-C])\.\s+(.+)", re.DOTALL)

def _parse_uworld_qstn(text):
    items = []
    current_q = None
    current_opts = {}
    for raw_line in text.split("\n"):
        line = _sanitize(raw_line)
        m = _QNUM_RE.match(line)
        if m:
            if current_q and len(current_opts) == 3:
                items.append({"q_text": current_q, "option_a": current_opts.get("A",""),
                               "option_b": current_opts.get("B",""), "option_c": current_opts.get("C","")})
            current_q = m.group(2).strip()
            current_opts = {}
            continue
        m2 = _OPT_RE.match(line)
        if m2 and current_q:
            current_opts[m2.group(1)] = m2.group(2).strip()
            continue
        if current_q and line and not m2:
            if len(current_opts) == 0:
                current_q += " " + line
            elif len(current_opts) < 3:
                last_key = list(current_opts)[-1]
                current_opts[last_key] += " " + line
    if current_q and len(current_opts) == 3:
        items.append({"q_text": current_q, "option_a": current_opts.get("A",""),
                       "option_b": current_opts.get("B",""), "option_c": current_opts.get("C","")})
    return items

def _parse_uworld_ans(words):
    ans_map = {}
    i = 0
    while i < len(words):
        if _CHECKMARK in words[i].get("text",""):
            for j in range(max(0,i-4), i):
                m = re.match(r"^(\d+)\.$", words[j].get("text","").strip())
                if m:
                    qnum = int(m.group(1))
                    for k in range(i+1, min(i+4, len(words))):
                        letter = words[k].get("text","").strip().rstrip(".")
                        if letter in ("A","B","C"):
                            ans_map[qnum] = letter
                            break
                    break
        i += 1
    return ans_map

def audit_uworld(db_by_source):
    rows = db_by_source.get("UWorld", [])
    if not rows:
        return []
    issues = []
    print(f"  UWorld: {len(rows)} questions in DB", flush=True)
    for topic_dir, topic_name in UWORLD_TOPIC_MAP.items():
        topic_path = UWORLD_ROOT / topic_dir
        if not topic_path.exists():
            continue
        qstn_dir = topic_path / "ONLY QSTN"
        if not qstn_dir.exists():
            continue
        topic_rows = [r for r in rows if r.get("subtopic","").startswith(topic_dir.split(".")[0].strip() + ".")]
        if not topic_rows:
            topic_rows = [r for r in rows if topic_name in (r.get("subtopic","") or "")]

        for qstn_pdf in sorted(qstn_dir.glob("*.pdf")):
            subtopic_name = qstn_pdf.stem
            if subtopic_name in _UWORLD_ANSWERS_SKIP:
                continue
            ans_pdf = topic_path / "Answers" / (subtopic_name + " - Answers.pdf")
            if not ans_pdf.exists():
                continue

            q_text_raw = _pdf_text_safe(qstn_pdf)
            if not q_text_raw:
                continue
            pdf_items = _parse_uworld_qstn(q_text_raw)
            if not pdf_items:
                continue

            ans_words = _pdf_words_safe(ans_pdf)
            ans_map = _parse_uworld_ans(ans_words)

            lut = _build_lookup(pdf_items)
            for idx, (pdf_item, correct_letter) in enumerate(
                [(pdf_items[i], ans_map.get(i+1)) for i in range(len(pdf_items))]
            ):
                if not correct_letter:
                    continue
                db_row, _ = _lookup(lut, pdf_item["q_text"], db_row=None)
                if not db_row:
                    db_row = next((r for r in rows if _sim(_norm(r.get("question_en","")), _norm(pdf_item["q_text"])) > 0.75), None)
                if not db_row:
                    continue
                stored = (db_row.get("correct_answer") or "").upper()
                if stored and stored != correct_letter:
                    issues.append({
                        "id": db_row["id"], "source": "UWorld",
                        "stored": stored, "detected": correct_letter, "pass": "PDF",
                        "snippet": f"Q: {db_row.get('question_en','')[:70]}… stored={stored} pdf={correct_letter}"
                    })
    print(f"  UWorld PDF issues found: {len(issues)}", flush=True)
    return issues

# ── Kaplan PDF audit ───────────────────────────────────────────────────────────

def _parse_kaplan_qa(text):
    items = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = _sanitize(lines[i])
        m = _QNUM_RE.match(line)
        if not m:
            i += 1
            continue
        qnum = int(m.group(1))
        q_parts = [m.group(2).strip()]
        i += 1
        opts = {}
        while i < len(lines):
            l2 = _sanitize(lines[i])
            m2 = _OPT_RE.match(l2)
            if m2:
                opts[m2.group(1)] = m2.group(2).strip()
                i += 1
                if len(opts) == 3:
                    break
            elif re.match(r"^\d+\.\s+", l2):
                break
            else:
                if len(opts) == 0:
                    q_parts.append(l2)
                elif opts:
                    last = list(opts)[-1]
                    opts[last] += " " + l2
                i += 1
        if len(opts) >= 2:
            items.append({
                "q_num": qnum,
                "q_text": " ".join(q_parts).strip(),
                "option_a": opts.get("A",""),
                "option_b": opts.get("B",""),
                "option_c": opts.get("C",""),
            })
        else:
            i += 1
    return items

_ANS_LINE_RE = re.compile(r"(\d+)\.\s+([A-C])\b")

def _parse_kaplan_ans_text(text):
    ans_map = {}
    for m in _ANS_LINE_RE.finditer(text):
        ans_map[int(m.group(1))] = m.group(2)
    return ans_map

def audit_kaplan(db_by_source):
    rows = db_by_source.get("Kaplan", [])
    if not rows:
        return []
    issues = []
    print(f"  Kaplan: {len(rows)} questions in DB", flush=True)
    qstn_root = KAPLAN_ROOT / "QSTN WITH ANS"
    if not qstn_root.exists():
        print("    [SKIP] QSTN WITH ANS dir not found", flush=True)
        return []
    pdf_count = 0
    for topic_dir in sorted(qstn_root.iterdir()):
        if not topic_dir.is_dir():
            continue
        for pdf_path in sorted(topic_dir.glob("*.pdf")):
            text = _pdf_text_safe(pdf_path)
            if not text:
                continue
            pdf_items = _parse_kaplan_qa(text)
            ans_map = _parse_kaplan_ans_text(text)
            if not pdf_items or not ans_map:
                continue
            pdf_count += 1
            lut = _build_lookup(pdf_items)
            for item in pdf_items:
                correct = ans_map.get(item["q_num"])
                if not correct:
                    continue
                db_row, mlen = _lookup(lut, item["q_text"], db_row=None)
                if not db_row:
                    db_row = next((r for r in rows if _sim(_norm(r.get("question_en","")), _norm(item["q_text"])) > 0.75), None)
                if not db_row:
                    continue
                stored = (db_row.get("correct_answer") or "").upper()
                if stored and stored != correct:
                    issues.append({
                        "id": db_row["id"], "source": "Kaplan",
                        "stored": stored, "detected": correct, "pass": "PDF",
                        "snippet": f"Q: {db_row.get('question_en','')[:70]}… stored={stored} pdf={correct}"
                    })
    print(f"  Kaplan: {pdf_count} PDFs scanned, {len(issues)} issues found", flush=True)
    return issues

# ── Extra_QB PDF audit ─────────────────────────────────────────────────────────

def audit_extra_qb(db_by_source):
    rows = db_by_source.get("Extra_QB", [])
    if not rows or not EXTRA_PDF.exists():
        return []
    print(f"  Extra_QB: {len(rows)} questions in DB", flush=True)
    text = _pdf_text_safe(EXTRA_PDF)
    if not text:
        return []
    pdf_items = _parse_kaplan_qa(text)
    ans_map = _parse_kaplan_ans_text(text)
    lut = _build_lookup(pdf_items)
    issues = []
    for item in pdf_items:
        correct = ans_map.get(item["q_num"])
        if not correct:
            continue
        db_row, _ = _lookup(lut, item["q_text"], db_row=None)
        if not db_row:
            db_row = next((r for r in rows if _sim(_norm(r.get("question_en","")), _norm(item["q_text"])) > 0.75), None)
        if not db_row:
            continue
        stored = (db_row.get("correct_answer") or "").upper()
        if stored and stored != correct:
            issues.append({
                "id": db_row["id"], "source": "Extra_QB",
                "stored": stored, "detected": correct, "pass": "PDF",
                "snippet": f"Q: {db_row.get('question_en','')[:70]}… stored={stored} pdf={correct}"
            })
    print(f"  Extra_QB: {len(issues)} issues found", flush=True)
    return issues

# ── Kevin Mock PDF audit ───────────────────────────────────────────────────────

def audit_kevin(db_by_source):
    rows = db_by_source.get("Kevin_Mock", [])
    if not rows:
        return []
    issues = []
    print(f"  Kevin_Mock: {len(rows)} questions in DB", flush=True)
    for q_pdf, a_pdf in [(KEVIN_Q1, KEVIN_A1), (KEVIN_Q2, KEVIN_A2)]:
        if not q_pdf.exists() or not a_pdf.exists():
            continue
        q_text = _pdf_text_safe(q_pdf)
        a_text = _pdf_text_safe(a_pdf)
        if not q_text or not a_text:
            continue
        pdf_items = _parse_kaplan_qa(q_text)
        ans_map = _parse_kaplan_ans_text(a_text)
        lut = _build_lookup(pdf_items)
        for item in pdf_items:
            correct = ans_map.get(item["q_num"])
            if not correct:
                continue
            db_row, _ = _lookup(lut, item["q_text"], db_row=None)
            if not db_row:
                db_row = next((r for r in rows if _sim(_norm(r.get("question_en","")), _norm(item["q_text"])) > 0.75), None)
            if not db_row:
                continue
            stored = (db_row.get("correct_answer") or "").upper()
            if stored and stored != correct:
                issues.append({
                    "id": db_row["id"], "source": "Kevin_Mock",
                    "stored": stored, "detected": correct, "pass": "PDF",
                    "snippet": f"Q: {db_row.get('question_en','')[:70]}… stored={stored} pdf={correct}"
                })
    print(f"  Kevin_Mock: {len(issues)} issues found", flush=True)
    return issues

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True, help="Path to questions JSON dump")
    ap.add_argument("--apply", action="store_true", help="Write corrections to corrections.json")
    ap.add_argument("--nlp-only", action="store_true", help="Skip PDF audit")
    ap.add_argument("--pdf-only", action="store_true", help="Skip NLP audit")
    args = ap.parse_args()

    print(f"\nLoading dump from {args.dump}...", flush=True)
    with open(args.dump, encoding="utf-8-sig") as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} questions.\n", flush=True)

    # Group by source for PDF audit
    db_by_source = {}
    for row in questions:
        db_by_source.setdefault(row.get("source",""), []).append(row)
    for src, rows in db_by_source.items():
        print(f"  Source '{src}': {len(rows)} questions", flush=True)

    all_corrections = {}  # id -> {"stored":..., "detected":..., "source":..., "pass":...}

    # ── NLP Audit ─────────────────────────────────────────────────────────────
    if not args.pdf_only:
        print(f"\n{'='*60}", flush=True)
        print("NLP AUDIT (explanation text → correct_answer)", flush=True)
        print(f"{'='*60}", flush=True)
        p1, p2, p3, ok, nosig = run_nlp_audit(questions)
        total = len(questions)
        print(f"\n  P1 (explicit letter, conf=1.0):  {len(p1):4d} mismatches  ← AUTO-FIX", flush=True)
        print(f"  P2 (option text match, conf=0.9): {len(p2):4d} mismatches  ← AUTO-FIX", flush=True)
        print(f"  P3 (stemmed overlap, advisory):   {len(p3):4d} flags", flush=True)
        print(f"  OK (agree):                       {ok:4d}", flush=True)
        print(f"  No signal (short expl):           {nosig:4d}", flush=True)
        print(f"  Total:                            {total:4d}", flush=True)

        if p1:
            print(f"\n  P1 details ({len(p1)}):", flush=True)
            for item in p1[:30]:
                print(f"    [{item['source']}] stored={item['stored']} -> {item['detected']} | {item['snippet'][:120]}", flush=True)

        if p2:
            print(f"\n  P2 details ({len(p2)}):", flush=True)
            for item in p2[:30]:
                print(f"    [{item['source']}] stored={item['stored']} -> {item['detected']} | {item['snippet'][:120]}", flush=True)

        for item in p1 + p2:
            if item["id"] not in all_corrections:
                all_corrections[item["id"]] = item

        # P3 advisory summary by source
        p3_by_src = {}
        for item in p3:
            p3_by_src.setdefault(item["source"], 0)
            p3_by_src[item["source"]] += 1
        if p3_by_src:
            print(f"\n  P3 advisory by source: {p3_by_src}", flush=True)

    # ── PDF Audit ─────────────────────────────────────────────────────────────
    if not args.nlp_only:
        print(f"\n{'='*60}", flush=True)
        print("PDF AUDIT (source PDFs → correct_answer)", flush=True)
        print(f"{'='*60}", flush=True)

        pdf_issues = []
        print("\n[UWorld]", flush=True)
        pdf_issues += audit_uworld(db_by_source)
        print("\n[Kaplan]", flush=True)
        pdf_issues += audit_kaplan(db_by_source)
        print("\n[Extra_QB]", flush=True)
        pdf_issues += audit_extra_qb(db_by_source)
        print("\n[Kevin_Mock]", flush=True)
        pdf_issues += audit_kevin(db_by_source)

        # Deduplicate vs NLP fixes — only add PDF issues not already caught
        new_pdf = 0
        confirm_pdf = 0
        for item in pdf_issues:
            if item["id"] in all_corrections:
                confirm_pdf += 1
            else:
                all_corrections[item["id"]] = item
                new_pdf += 1

        print(f"\n  PDF issues: {len(pdf_issues)} total", flush=True)
        print(f"    Already in NLP fixes: {confirm_pdf}", flush=True)
        print(f"    New (PDF-only):       {new_pdf}", flush=True)

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{'='*60}", flush=True)
    print("COMBINED CORRECTIONS", flush=True)
    print(f"{'='*60}", flush=True)
    by_src = {}
    by_pass = {}
    for item in all_corrections.values():
        by_src.setdefault(item["source"], 0)
        by_src[item["source"]] += 1
        by_pass.setdefault(str(item["pass"]), 0)
        by_pass[str(item["pass"])] += 1
    print(f"  Total unique corrections: {len(all_corrections)}", flush=True)
    print(f"  By source: {by_src}", flush=True)
    print(f"  By pass:   {by_pass}", flush=True)

    if args.apply:
        out_path = "C:\\Users\\codjo\\AppData\\Local\\Temp\\wib_corrections.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(list(all_corrections.values()), f, ensure_ascii=False, indent=2)
        print(f"\n  Corrections saved to: {out_path}", flush=True)

if __name__ == "__main__":
    main()
