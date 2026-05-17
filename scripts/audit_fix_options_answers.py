#!/usr/bin/env python3
"""
Audit + fix question options (A/B/C) and correct_answer against original PDFs.

Sources audited:
  - UWorld    (1,897 Q) — options from ONLY QSTN PDFs, correct via checkmark
  - Kaplan    (3,717 Q) — options + correct via QSTN WITH ANS + Mock Answers PDFs
  - Extra_QB  (  333 Q) — options + correct via EXTRA 700 MCQs.pdf
  - Kevin_Mock(  180 Q) — options via MOCK-Q PDFs, correct via MOCK-A PDFs
  - CFA_WEB: SKIPPED (scanned — Vision-extracted, cannot byte-verify)

Usage:
    cd D:\\CLAUDE\\Projet CFA\\wib-cfa
    python scripts/audit_fix_options_answers.py [--dry-run] [--source uworld|kaplan|extra|kevin|all]
"""
import sys, re, argparse, warnings, logging, tomllib, threading
from pathlib import Path
import pdfplumber

_PDF_TIMEOUT = 60  # seconds before giving up on a hanging PDF

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)
for _n in list(logging.Logger.manager.loggerDict):
    logging.getLogger(_n).setLevel(logging.CRITICAL)

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE         = Path(r"D:\CLAUDE\Projet CFA\CFA L1")
UWORLD_ROOT  = BASE / "6. TOUGH QB UWORLD-2000 MCQs"
KAPLAN_ROOT  = BASE / "2. QB KAPLAN-3000 MCQs"
MOCK_ROOT    = BASE / "8. KAPLAN MOCK-1100 MCQs"
EXTRA_PDF    = BASE / "7. EXTRA QB-700MCQs" / "EXTRA 700 MCQs.pdf"
KEVIN_Q1     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 1 MOCK-Q.pdf"
KEVIN_A1     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 1 MOCK-A.pdf"
KEVIN_Q2     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 2 MOCK-Q.pdf"
KEVIN_A2     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 2 MOCK-A.pdf"
SECRETS_PATH = Path(".streamlit/secrets.toml")

UWORLD_TOPIC_MAP = {
    "1. Quantitative Methods":          "Quantitative Methods",
    "2. Economics":                     "Economics",
    "3. Portfolio Management":          "Portfolio Management",
    "4. Corporate Issuers":             "Corporate Issuers",
    "5. Financial Statement Analysis":  "Financial Statement Analysis",
    "6. Equity Investments":            "Equity Investments",
    "7. Fixed Income":                  "Fixed Income",
    "8. Derivatives":                   "Derivatives",
    "9. Alternative Investments":       "Alternative Investments",
    "10. Ethics":                       "Ethics & Professional Standards",
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

# UWorld Answers PDFs that cause pdfplumber to hang (skip correct_answer check)
_UWORLD_ANSWERS_SKIP = {
    "1.03 Statistical Measures of Asset Returns",
    "5.12 Introduction to Financial Statement Modeling",
    "11.03 Guidance For Standards I–VII",
}

_CHECKMARK = ""  # FontAwesome Pro Light checkmark used by UWorld

# ── Text helpers ──────────────────────────────────────────────────────────────

def _sanitize(s):
    return (s or "").replace("\x00", "").replace("�", "").strip()

def _strip_tables(text):
    """Remove markdown table rows so table-injected DB questions match PDF stems."""
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
    """Normalize option text for comparison (collapse whitespace)."""
    return re.sub(r"\s+", " ", (text or "").strip())

_LENS = [120, 80, 60]

def _opts_avg_sim(db_row, pdf_item):
    """Average word-overlap sim between DB and PDF options — used to resolve ambiguous stem matches."""
    total = 0.0
    for field in ("option_a", "option_b", "option_c"):
        total += _sim(_norm_opt(db_row.get(field, "")), _norm_opt(pdf_item.get(field, "")))
    return total / 3.0

def _build_lookup(items, min_length=60):
    """Build {(length, norm_key): [items]} — stores ALL items sharing the same stem."""
    lut = {}
    for item in items:
        for L in _LENS:
            if L < min_length:
                continue
            key = (L, _norm(item["q_text"], L))
            lut.setdefault(key, []).append(item)
    return lut

def _lookup(lut, db_q_text, min_length=60, db_row=None):
    """Return (item, match_length) or (None, 0).
    When multiple PDF items share the same stem, pick the one with highest option similarity
    to the DB row (resolves false positives from generic short stems like 'most likely accurate?').
    """
    for L in _LENS:
        if L < min_length:
            continue
        key = (L, _norm(db_q_text, L))
        candidates = lut.get(key)
        if not candidates:
            continue
        if len(candidates) == 1 or db_row is None:
            return candidates[0], L
        # Multiple PDF items share this stem — pick the best option match
        best = max(candidates, key=lambda x: _opts_avg_sim(db_row, x))
        return best, L
    return None, 0

# ── Supabase connection ───────────────────────────────────────────────────────

def _connect():
    print("Connecting to Supabase …", flush=True)
    with open(SECRETS_PATH, "rb") as f:
        s = tomllib.load(f)
    from supabase import create_client
    sb = create_client(
        s["supabase"]["SUPABASE_URL"],
        s["supabase"].get("SUPABASE_SERVICE_KEY") or s["supabase"]["SUPABASE_ANON_KEY"],
    )
    print("Connected.\n", flush=True)
    return sb

def _fetch_source(sb, source):
    rows = []
    offset = 0
    while True:
        r = sb.table("questions").select(
            "id,question_en,option_a,option_b,option_c,correct_answer,subtopic"
        ).eq("source", source).range(offset, offset + 999).execute()
        rows.extend(r.data)
        if len(r.data) < 1000:
            break
        offset += 1000
    return rows

# ── PDF text helpers ──────────────────────────────────────────────────────────

def _pdf_text(path):
    chunks = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    chunks.append(t)
    except Exception as e:
        print(f"    [WARN] text error {path.name}: {e}", flush=True)
    return "\n".join(chunks)

def _pdf_text_safe(path):
    """Text extraction with timeout — returns '' on hang."""
    buf = []
    err = []
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
    t.start()
    t.join(timeout=_PDF_TIMEOUT)
    if t.is_alive():
        print(f"    [SKIP timeout] {path.name}", flush=True)
        return ""
    if err:
        print(f"    [WARN] {path.name}: {err[0]}", flush=True)
    return "\n".join(buf)

def _pdf_words_safe(path):
    """Word extraction with fontname, with timeout — returns [] on hang."""
    buf = []
    err = []
    def _run():
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    buf.extend(page.extract_words(extra_attrs=["fontname"]))
        except Exception as e:
            err.append(str(e))
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=_PDF_TIMEOUT)
    if t.is_alive():
        print(f"    [SKIP timeout] {path.name}", flush=True)
        return []
    if err:
        print(f"    [WARN] {path.name}: {err[0]}", flush=True)
    return buf

# ── UWorld parsers ────────────────────────────────────────────────────────────

def _parse_uworld_qstn(path):
    """Parse ONLY QSTN PDF → list of {num, q_text, option_a, option_b, option_c}."""
    text = _pdf_text_safe(path)
    results = []
    parts = re.split(r"Question\s+(\d+)\n", text)
    for i in range(1, len(parts), 2):
        num   = int(parts[i])
        block = (parts[i + 1] if i + 1 < len(parts) else "").strip()
        m = re.match(r"(.+?)\nA\.\s+(.+?)\nB\.\s+(.+?)\nC\.\s+(.+)", block, re.DOTALL)
        if not m:
            continue
        q_text = _sanitize(" ".join(m.group(1).split()))
        opt_a  = _sanitize(" ".join(m.group(2).split()))
        opt_b  = _sanitize(" ".join(m.group(3).split()))
        opt_c  = _sanitize(" ".join(m.group(4).split("\n")[0].split()))
        if len(q_text) < 15 or len(opt_a) < 2 or len(opt_b) < 2 or len(opt_c) < 2:
            continue
        if len(opt_c) <= 2 and opt_c.isupper():
            continue
        results.append({"num": num, "q_text": q_text,
                         "option_a": opt_a, "option_b": opt_b, "option_c": opt_c})
    return results

def _parse_uworld_answers_correct(path):
    """Parse Answers PDF → {q_num: correct_letter} via checkmark detection."""
    words = _pdf_words_safe(path)
    text  = _pdf_text_safe(path)
    correct_in_order = []
    for i, w in enumerate(words):
        if _CHECKMARK in w["text"]:
            for j in range(i + 1, min(i + 6, len(words))):
                if re.match(r"^[ABC]\.$", words[j]["text"]):
                    correct_in_order.append(words[j]["text"][0])
                    break
    q_nums = [
        int(m.group(1))
        for m in re.finditer(r"^(\d+)\.\s*([A-Z][^.])", text, re.MULTILINE)
    ]
    result = {}
    for idx, qnum in enumerate(q_nums):
        if idx < len(correct_in_order):
            result[qnum] = correct_in_order[idx]
    return result

def _parse_uworld_all():
    """Parse all UWorld QSTN+Answers PDFs → list of {q_text, option_a, option_b, option_c, correct_answer}."""
    items = []
    for folder_name in UWORLD_TOPIC_MAP:
        folder = UWORLD_ROOT / folder_name
        q_dir  = folder / "ONLY QSTN"
        if not q_dir.exists():
            continue
        q_pdfs = sorted(q_dir.glob("*.pdf"))
        total_in_folder = len(q_pdfs)
        for qi, q_pdf in enumerate(q_pdfs, 1):
            subtopic = q_pdf.stem
            print(f"  [{qi:2d}/{total_in_folder}] {subtopic[:55]}", flush=True)
            a_pdf = folder / (subtopic + " - Answers.pdf")
            q_list = _parse_uworld_qstn(q_pdf)
            correct_map = {}
            if a_pdf.exists() and subtopic not in _UWORLD_ANSWERS_SKIP:
                correct_map = _parse_uworld_answers_correct(a_pdf)
            for q in q_list:
                correct = correct_map.get(q["num"])  # None if subtopic skipped or not found
                items.append({
                    "q_text":         q["q_text"],
                    "option_a":       q["option_a"],
                    "option_b":       q["option_b"],
                    "option_c":       q["option_c"],
                    "correct_answer": correct,
                    "subtopic":       subtopic,
                })
        sys.stdout.flush()
    return items

# ── Kaplan parsers ────────────────────────────────────────────────────────────

_NEGATED_K = re.compile(
    r'\b(least\s+accurate|least\s+likely|least\s+correct|incorrect|not\s+accurate|'
    r'not\s+correct|is\s+false|not\s+true|except|inaccurate|violates|least\s+appropriate)\b',
    re.IGNORECASE,
)

_STOPS_K = {
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

def _stem_k(w):
    for suf in ('ations','ation','tions','tion','ments','ment','ness',
                'ing','ings','ed','ers','er','es','s'):
        if len(w) > len(suf) + 4 and w.endswith(suf):
            return w[:-len(suf)]
    return w

def _tok_k(text):
    return [_stem_k(w) for w in re.findall(r'[a-z]+', text.lower())
            if w not in _STOPS_K and len(w) > 3]

def _fuzzy_k(opt_word, expl_words):
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

def _detect_v2_kaplan(q_text, opt_a, opt_b, opt_c, explanation):
    """Re-implementation of fix_kaplan_v2._detect_v2."""
    if not explanation or len(explanation.strip()) < 15:
        return None
    expl = explanation.strip()
    opts = {"A": (opt_a or "").strip(), "B": (opt_b or "").strip(), "C": (opt_c or "").strip()}
    # Pass 1: explicit letter
    for letter in ("A", "B", "C"):
        if re.search(
            rf'\b(correct\s+answer\s+is\s+{letter}|answer\s+is\s+{letter}|'
            rf'{letter}\s+is\s+(the\s+)?(correct|right|best)|'
            rf'(choose|select|answer)\s*[:\s]+{letter})\b',
            expl, re.IGNORECASE,
        ):
            return letter
    # Pass 2: exact option text in first sentence
    first_sent = (re.split(r'(?<=[.!?])\s+', expl) or [""])[0].lower()
    for letter in ("A", "B", "C"):
        opt_clean = opts[letter].lower().rstrip(".").strip()
        if opt_clean and len(opt_clean) > 8 and opt_clean in first_sent:
            return letter
    # Pass 3: stemmed + fuzzy overlap
    focus = " ".join(re.split(r'(?<=[.!?])\s+', expl)[:3])
    expl_stems = set(_tok_k(focus))
    expl_raw   = re.findall(r'[a-z]+', focus.lower())
    scores = {}
    for letter in ("A", "B", "C"):
        opt_stems = list(_tok_k(opts[letter]))
        if not opt_stems:
            scores[letter] = 0.0; continue
        matched = sum(1 for ow in opt_stems
                      if ow in expl_stems or _fuzzy_k(ow, expl_raw))
        scores[letter] = matched / len(opt_stems)
    max_s = max(scores.values())
    if max_s > 0:
        winners = [l for l, s in scores.items() if s == max_s]
        if len(winners) == 1:
            return winners[0]
        abs_m = {l: sum(1 for ow in _tok_k(opts[l])
                        if ow in expl_stems or _fuzzy_k(ow, expl_raw))
                 for l in winners}
        best = max(abs_m, key=abs_m.get)
        if abs_m[best] > min(abs_m.values()):
            return best
    # Pass 4: numerical match
    def _nums(t):
        raw = re.findall(r'[\d,]+\.?\d*\s*(?:%|bps?|pp)?', t.lower())
        return {n.replace(',', '').strip() for n in raw if n.strip()}
    expl_nums = _nums(expl[:400])
    for letter in ("A", "B", "C"):
        opt_nums = _nums(opts[letter])
        if opt_nums and opt_nums <= expl_nums:
            return letter
    return None

def _parse_kaplan_pdf(path):
    """Parse Kaplan QSTN WITH ANS PDF → list of {q_text, option_a, option_b, option_c, explanation}."""
    text = _pdf_text(path)
    results = []
    parts = re.split(r"Question\s+#(\d+)\s+of\s+\d+\s*\n", text)
    for i in range(1, len(parts), 2):
        block = (parts[i + 1] if i + 1 < len(parts) else "").strip()
        block = re.sub(r"Question\s+ID:\s*\d+\s*\n?", "", block, count=1)
        m = re.match(r"(.+?)\nA\)\s+(.+?)\nB\)\s+(.+?)\nC\)\s+(.+?)\nExplanation\n(.+)",
                     block, re.DOTALL)
        if not m:
            continue
        q_text = _sanitize(" ".join(m.group(1).split()))
        opt_a  = _sanitize(" ".join(m.group(2).split()))
        opt_b  = _sanitize(" ".join(m.group(3).split()))
        opt_c  = _sanitize(" ".join(m.group(4).split()))
        expl   = m.group(5).strip()
        expl   = re.split(r"\(Module\s+\d+|\nQuestion\s+#", expl)[0].strip()
        expl   = _sanitize(" ".join(expl.split()))
        if len(q_text) < 10 or len(opt_a) < 2 or len(opt_b) < 2 or len(opt_c) < 2:
            continue
        results.append({"q_text": q_text, "option_a": opt_a, "option_b": opt_b,
                         "option_c": opt_c, "explanation": expl})
    return results

def _parse_kaplan_all():
    """Parse all Kaplan QSTN WITH ANS + Mock PDFs → list of {q_text, optA, optB, optC, correct_answer}."""
    items = []
    # QB
    ans_dir = KAPLAN_ROOT / "QSTN WITH ANS"
    for folder_name in KAPLAN_TOPIC_MAP:
        topic_dir = ans_dir / folder_name
        if not topic_dir.exists():
            continue
        for pdf in sorted(topic_dir.glob("*- Answers.pdf")):
            qs = _parse_kaplan_pdf(pdf)
            for q in qs:
                correct = _detect_v2_kaplan(q["q_text"], q["option_a"], q["option_b"],
                                             q["option_c"], q["explanation"])
                items.append({"q_text": q["q_text"], "option_a": q["option_a"],
                               "option_b": q["option_b"], "option_c": q["option_c"],
                               "correct_answer": correct})
        sys.stdout.flush()
    # Mocks
    for pdf in sorted(MOCK_ROOT.glob("Mock Exam * - Answers.pdf")):
        qs = _parse_kaplan_pdf(pdf)
        for q in qs:
            correct = _detect_v2_kaplan(q["q_text"], q["option_a"], q["option_b"],
                                         q["option_c"], q["explanation"])
            items.append({"q_text": q["q_text"], "option_a": q["option_a"],
                           "option_b": q["option_b"], "option_c": q["option_c"],
                           "correct_answer": correct})
    return items

# ── Extra_QB parser ───────────────────────────────────────────────────────────

def _de_triple(s):
    if not s or len(s) < 9:
        return s
    sample = s[:60].replace(" ", "")
    if not sample:
        return s
    triples = sum(1 for i in range(0, len(sample)-2, 3)
                  if sample[i] == sample[i+1] == sample[i+2])
    if triples > 0 and triples >= len(sample) // 6:
        return re.sub(r"(.)\1\1", r"\1", s)
    return s

_SECTION_MAP = {
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

def _match_section(line):
    low = line.lower()
    for pattern, topic in _SECTION_MAP.items():
        if re.search(pattern, low):
            return topic
    return None

def _extract_text_pages(pdf_path, page_start, page_end):
    with pdfplumber.open(pdf_path) as pdf:
        parts = []
        for i in range(page_start, min(page_end, len(pdf.pages))):
            t = pdf.pages[i].extract_text() or ""
            parts.append(_de_triple(t))
        return "\n".join(parts)

def _parse_extra700():
    """Re-parse EXTRA 700 MCQs.pdf → list of {q_text, option_a, option_b, option_c, correct_answer}."""
    q_text_raw = _extract_text_pages(EXTRA_PDF, 0, 127)
    q_lines = q_text_raw.split("\n")

    raw_questions = {}
    current_topic = "Ethics & Professional Standards"
    i = 0
    while i < len(q_lines):
        line = q_lines[i].strip()
        if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", line) and not re.match(r"^\d", line):
            t = _match_section(line)
            if t:
                current_topic = t
            i += 1; continue
        m = re.match(r"^(\d+)\.\s+(.+)", line)
        if m:
            qnum = int(m.group(1))
            stem_parts = [m.group(2)]
            i += 1
            while i < len(q_lines):
                nxt = q_lines[i].strip()
                if re.match(r"^[A-C]\.\s+", nxt): break
                if re.match(r"^\d+\.\s+\S", nxt): break
                if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", nxt) and _match_section(nxt): break
                stem_parts.append(nxt); i += 1
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
                        if re.match(r"^[A-C]\.\s+", cont) or re.match(r"^\d+\.\s+\S", cont): break
                        if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", cont) and _match_section(cont): break
                        if cont and not re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", cont):
                            opt_parts.append(cont)
                        i += 1
                    opts[letter] = " ".join(opt_parts)
                else:
                    break
            if stem and "A" in opts and "B" in opts and "C" in opts:
                key = (current_topic, qnum)
                if key not in raw_questions:
                    raw_questions[key] = {"stem": stem, "A": opts["A"], "B": opts["B"], "C": opts["C"]}
        else:
            i += 1

    # Parse answers
    raw_answers = {}
    with pdfplumber.open(EXTRA_PDF) as pdf:
        sol_topic = "Ethics & Professional Standards"
        for pi in range(127, len(pdf.pages)):
            page_txt = _de_triple(pdf.pages[pi].extract_text() or "")
            for ln in page_txt.split("\n"):
                ln = ln.strip()
                if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", ln) and not re.match(r"^\d", ln):
                    t = _match_section(ln)
                    if t:
                        sol_topic = t; break
            for am in re.finditer(r"(\d{1,3})\.\s+[Aa]nswer\s*[=:]\s*([A-C])\b", page_txt):
                qnum = int(am.group(1)); letter = am.group(2).upper()
                key = (sol_topic, qnum)
                if key not in raw_answers:
                    raw_answers[key] = letter

    items = []
    for (topic, qnum), q in sorted(raw_questions.items()):
        key = (topic, qnum)
        correct = raw_answers.get(key)
        if not correct:
            continue
        items.append({
            "q_text":    _sanitize(q["stem"]),
            "option_a":  _sanitize(q["A"]),
            "option_b":  _sanitize(q["B"]),
            "option_c":  _sanitize(q["C"]),
            "correct_answer": correct,
        })
    return items

# ── Kevin_Mock parser ─────────────────────────────────────────────────────────

def _extract_text_full(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

def _parse_kevin_session(q_pdf, a_pdf):
    """Parse one Kevin Mock session → list of {q_text, option_a, option_b, option_c, correct_answer}."""
    q_text = _extract_text_full(q_pdf)
    a_text = _extract_text_full(a_pdf)

    # Parse questions
    raw_questions = {}
    q_lines = q_text.split("\n")
    i = 0
    while i < len(q_lines):
        line = q_lines[i].strip()
        m = re.match(r"^(\d+)\.\s+(.+)", line)
        if m:
            qnum = int(m.group(1))
            stem_parts = [m.group(2)]
            i += 1
            while i < len(q_lines):
                nxt = q_lines[i].strip()
                if re.match(r"^[A-C]\.\s+", nxt): break
                if re.match(r"^\d+\.\s+", nxt): break
                stem_parts.append(nxt); i += 1
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
                        if re.match(r"^[A-C]\.\s+", cont) or re.match(r"^\d+\.\s+", cont): break
                        if cont: opt_parts.append(cont)
                        i += 1
                    opts[letter] = " ".join(opt_parts)
                else:
                    break
            if stem and "A" in opts and "B" in opts and "C" in opts:
                raw_questions[qnum] = {"stem": stem, "A": opts["A"],
                                        "B": opts["B"], "C": opts["C"]}
        else:
            i += 1

    # Parse correct answers
    raw_answers = {}
    a_lines = a_text.split("\n")
    i = 0
    while i < len(a_lines):
        line = a_lines[i].strip()
        m = re.match(r"^(\d+)\.\s+([A-C])\b", line)
        if m:
            raw_answers[int(m.group(1))] = m.group(2)
        i += 1

    items = []
    for qnum, q in sorted(raw_questions.items()):
        correct = raw_answers.get(qnum)
        if not correct:
            continue
        items.append({
            "q_text":    _sanitize(q["stem"]),
            "option_a":  _sanitize(q["A"]),
            "option_b":  _sanitize(q["B"]),
            "option_c":  _sanitize(q["C"]),
            "correct_answer": correct,
        })
    return items

# ── Comparison helpers ────────────────────────────────────────────────────────

def _opts_differ(db_row, pdf_item):
    """Return list of (field, db_val, pdf_val) for differing fields."""
    diffs = []
    for field in ("option_a", "option_b", "option_c"):
        db_val  = _norm_opt(db_row.get(field, ""))
        pdf_val = _norm_opt(pdf_item.get(field, ""))
        if db_val != pdf_val:
            diffs.append((field, db_val, pdf_val))
    return diffs

def _answer_differs(db_row, pdf_item):
    """Return (db_answer, pdf_answer) if correct_answer differs, else None."""
    pdf_ans = pdf_item.get("correct_answer")
    if pdf_ans is None:
        return None  # skip (no data from PDF)
    db_ans = db_row.get("correct_answer", "")
    if db_ans != pdf_ans:
        return db_ans, pdf_ans
    return None

# ── Apply updates ─────────────────────────────────────────────────────────────

def _apply_updates(sb, updates, source, dry_run):
    """updates: list of {id, field: new_value, ...}"""
    if not updates:
        return 0
    if dry_run:
        print(f"  [DRY RUN] Would update {len(updates)} {source} questions")
        return 0
    done = errors = 0
    for u in updates:
        qid = u.pop("id")
        try:
            sb.table("questions").update(u).eq("id", qid).execute()
            done += 1
        except Exception as e:
            print(f"  [ERROR] {qid}: {e}", flush=True)
            errors += 1
    print(f"  Updated {done}/{len(updates)+errors} ({errors} errors)", flush=True)
    return done

# ── Source audits ─────────────────────────────────────────────────────────────

def audit_uworld(sb, dry_run):
    print("=" * 60)
    print("UWORLD AUDIT — options + correct_answer")
    print("=" * 60)
    print("Parsing UWorld QSTN + Answers PDFs …", flush=True)
    pdf_items = _parse_uworld_all()
    print(f"  Parsed {len(pdf_items)} questions from QSTN PDFs", flush=True)

    lut = _build_lookup(pdf_items, min_length=80)

    db_qs = _fetch_source(sb, "UWorld")
    print(f"  Fetched {len(db_qs)} UWorld questions from DB", flush=True)

    matched = no_match = opt_ok = opt_wrong = ans_ok = ans_wrong = ans_skip = 0
    updates = []
    shown = 0

    for row in db_qs:
        item, mlen = _lookup(lut, row.get("question_en", ""), min_length=80, db_row=row)
        if item is None:
            no_match += 1
            continue

        # Validate similarity
        sim = _sim(_norm(row["question_en"], 120), _norm(item["q_text"], 120))
        if sim < 0.40:
            no_match += 1
            continue

        matched += 1
        update = {"id": row["id"]}
        changed = False

        # Check options
        opt_diffs = _opts_differ(row, item)
        if opt_diffs:
            opt_wrong += 1
            for field, db_val, pdf_val in opt_diffs:
                update[field] = pdf_val
                changed = True
                if shown < 40:
                    print(f"  [OPT DIFF sim={sim:.2f} @{mlen}] {row['question_en'][:70]}")
                    print(f"    {field} OLD: {db_val[:80]}")
                    print(f"    {field} NEW: {pdf_val[:80]}")
                    shown += 1
        else:
            opt_ok += 1

        # Check correct_answer
        ans_diff = _answer_differs(row, item)
        if item.get("correct_answer") is None:
            ans_skip += 1
        elif ans_diff:
            ans_wrong += 1
            db_ans, pdf_ans = ans_diff
            update["correct_answer"] = pdf_ans
            changed = True
            if shown < 40:
                print(f"  [ANS DIFF sim={sim:.2f} @{mlen}] {row['question_en'][:70]}")
                print(f"    correct_answer OLD={db_ans} NEW={pdf_ans}")
                shown += 1
        else:
            ans_ok += 1

        if changed:
            updates.append(update)

    print(f"\n  Matched: {matched} | No match: {no_match}")
    print(f"  Options  — OK: {opt_ok} | Wrong: {opt_wrong}")
    print(f"  Answers  — OK: {ans_ok} | Wrong: {ans_wrong} | Skipped (hang PDFs): {ans_skip}")
    print(f"  Total questions to fix: {len(updates)}", flush=True)

    applied = _apply_updates(sb, updates, "UWorld", dry_run)
    return {"matched": matched, "no_match": no_match, "opt_wrong": opt_wrong,
            "ans_wrong": ans_wrong, "updated": applied if not dry_run else len(updates)}


def audit_kaplan(sb, dry_run):
    print("\n" + "=" * 60)
    print("KAPLAN AUDIT — options + correct_answer")
    print("=" * 60)
    print("Parsing Kaplan QB + Mock PDFs …", flush=True)
    pdf_items = _parse_kaplan_all()
    print(f"  Parsed {len(pdf_items)} questions from Kaplan PDFs", flush=True)

    lut = _build_lookup(pdf_items, min_length=80)

    db_qs = _fetch_source(sb, "Kaplan")
    print(f"  Fetched {len(db_qs)} Kaplan questions from DB", flush=True)

    matched = no_match = opt_ok = opt_wrong = ans_ok = ans_wrong = ans_skip = 0
    updates = []
    shown = 0

    for row in db_qs:
        item, mlen = _lookup(lut, row.get("question_en", ""), min_length=80, db_row=row)
        if item is None:
            no_match += 1
            continue
        sim = _sim(_norm(row["question_en"], 120), _norm(item["q_text"], 120))
        if sim < 0.40:
            no_match += 1
            continue

        matched += 1
        update = {"id": row["id"]}
        changed = False

        opt_diffs = _opts_differ(row, item)
        if opt_diffs:
            opt_wrong += 1
            for field, db_val, pdf_val in opt_diffs:
                update[field] = pdf_val
                changed = True
                if shown < 40:
                    print(f"  [OPT DIFF sim={sim:.2f} @{mlen}] {row['question_en'][:70]}")
                    print(f"    {field} OLD: {db_val[:80]}")
                    print(f"    {field} NEW: {pdf_val[:80]}")
                    shown += 1
        else:
            opt_ok += 1

        ans_diff = _answer_differs(row, item)
        if item.get("correct_answer") is None:
            ans_skip += 1
        elif ans_diff:
            ans_wrong += 1
            db_ans, pdf_ans = ans_diff
            update["correct_answer"] = pdf_ans
            changed = True
            if shown < 40:
                print(f"  [ANS DIFF sim={sim:.2f} @{mlen}] {row['question_en'][:70]}")
                print(f"    correct_answer OLD={db_ans} NEW={pdf_ans}")
                shown += 1
        else:
            ans_ok += 1

        if changed:
            updates.append(update)

    print(f"\n  Matched: {matched} | No match: {no_match}")
    print(f"  Options  — OK: {opt_ok} | Wrong: {opt_wrong}")
    print(f"  Answers  — OK: {ans_ok} | Wrong: {ans_wrong} | Skipped (no signal): {ans_skip}")
    print(f"  Total questions to fix: {len(updates)}", flush=True)

    applied = _apply_updates(sb, updates, "Kaplan", dry_run)
    return {"matched": matched, "no_match": no_match, "opt_wrong": opt_wrong,
            "ans_wrong": ans_wrong, "updated": applied if not dry_run else len(updates)}


def audit_extra(sb, dry_run):
    print("\n" + "=" * 60)
    print("EXTRA_QB AUDIT — options + correct_answer")
    print("=" * 60)
    print("Parsing EXTRA 700 MCQs.pdf …", flush=True)
    pdf_items = _parse_extra700()
    print(f"  Parsed {len(pdf_items)} questions", flush=True)

    lut = _build_lookup(pdf_items, min_length=60)

    db_qs = _fetch_source(sb, "Extra_QB")
    print(f"  Fetched {len(db_qs)} Extra_QB questions from DB", flush=True)

    matched = no_match = opt_ok = opt_wrong = ans_ok = ans_wrong = 0
    updates = []
    shown = 0

    for row in db_qs:
        item, mlen = _lookup(lut, row.get("question_en", ""), min_length=60, db_row=row)
        if item is None:
            no_match += 1
            continue
        sim = _sim(_norm(row["question_en"], 120), _norm(item["q_text"], 120))
        if sim < 0.40:
            no_match += 1
            continue

        matched += 1
        update = {"id": row["id"]}
        changed = False

        opt_diffs = _opts_differ(row, item)
        if opt_diffs:
            opt_wrong += 1
            for field, db_val, pdf_val in opt_diffs:
                update[field] = pdf_val
                changed = True
                if shown < 30:
                    print(f"  [OPT DIFF sim={sim:.2f} @{mlen}] {row['question_en'][:70]}")
                    print(f"    {field} OLD: {db_val[:80]}")
                    print(f"    {field} NEW: {pdf_val[:80]}")
                    shown += 1
        else:
            opt_ok += 1

        ans_diff = _answer_differs(row, item)
        if ans_diff:
            ans_wrong += 1
            db_ans, pdf_ans = ans_diff
            update["correct_answer"] = pdf_ans
            changed = True
            if shown < 30:
                print(f"  [ANS DIFF sim={sim:.2f} @{mlen}] {row['question_en'][:70]}")
                print(f"    correct_answer OLD={db_ans} NEW={pdf_ans}")
                shown += 1
        else:
            ans_ok += 1

        if changed:
            updates.append(update)

    print(f"\n  Matched: {matched} | No match: {no_match}")
    print(f"  Options  — OK: {opt_ok} | Wrong: {opt_wrong}")
    print(f"  Answers  — OK: {ans_ok} | Wrong: {ans_wrong}")
    print(f"  Total questions to fix: {len(updates)}", flush=True)

    applied = _apply_updates(sb, updates, "Extra_QB", dry_run)
    return {"matched": matched, "no_match": no_match, "opt_wrong": opt_wrong,
            "ans_wrong": ans_wrong, "updated": applied if not dry_run else len(updates)}


def audit_kevin(sb, dry_run):
    print("\n" + "=" * 60)
    print("KEVIN_MOCK AUDIT — options + correct_answer")
    print("=" * 60)
    print("Parsing Kevin Mock SESSION 1 + 2 …", flush=True)
    pdf_items  = _parse_kevin_session(KEVIN_Q1, KEVIN_A1)
    pdf_items += _parse_kevin_session(KEVIN_Q2, KEVIN_A2)
    print(f"  Parsed {len(pdf_items)} questions", flush=True)

    lut = _build_lookup(pdf_items, min_length=80)

    db_qs = _fetch_source(sb, "Kevin_Mock")
    print(f"  Fetched {len(db_qs)} Kevin_Mock questions from DB", flush=True)

    matched = no_match = opt_ok = opt_wrong = ans_ok = ans_wrong = 0
    updates = []
    shown = 0

    for row in db_qs:
        item, mlen = _lookup(lut, row.get("question_en", ""), min_length=80, db_row=row)
        if item is None:
            no_match += 1
            continue
        sim = _sim(_norm(row["question_en"], 120), _norm(item["q_text"], 120))
        if sim < 0.40:
            no_match += 1
            continue

        matched += 1
        update = {"id": row["id"]}
        changed = False

        opt_diffs = _opts_differ(row, item)
        if opt_diffs:
            opt_wrong += 1
            for field, db_val, pdf_val in opt_diffs:
                update[field] = pdf_val
                changed = True
                if shown < 30:
                    print(f"  [OPT DIFF sim={sim:.2f} @{mlen}] {row['question_en'][:70]}")
                    print(f"    {field} OLD: {db_val[:80]}")
                    print(f"    {field} NEW: {pdf_val[:80]}")
                    shown += 1
        else:
            opt_ok += 1

        ans_diff = _answer_differs(row, item)
        if ans_diff:
            ans_wrong += 1
            db_ans, pdf_ans = ans_diff
            update["correct_answer"] = pdf_ans
            changed = True
            if shown < 30:
                print(f"  [ANS DIFF sim={sim:.2f} @{mlen}] {row['question_en'][:70]}")
                print(f"    correct_answer OLD={db_ans} NEW={pdf_ans}")
                shown += 1
        else:
            ans_ok += 1

        if changed:
            updates.append(update)

    print(f"\n  Matched: {matched} | No match: {no_match}")
    print(f"  Options  — OK: {opt_ok} | Wrong: {opt_wrong}")
    print(f"  Answers  — OK: {ans_ok} | Wrong: {ans_wrong}")
    print(f"  Total questions to fix: {len(updates)}", flush=True)

    applied = _apply_updates(sb, updates, "Kevin_Mock", dry_run)
    return {"matched": matched, "no_match": no_match, "opt_wrong": opt_wrong,
            "ans_wrong": ans_wrong, "updated": applied if not dry_run else len(updates)}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", choices=["uworld", "kaplan", "extra", "kevin", "all"],
                        default="all")
    args = parser.parse_args()

    sb = _connect()
    results = {}

    if args.source in ("uworld", "all"):
        results["UWorld"] = audit_uworld(sb, args.dry_run)
    if args.source in ("kaplan", "all"):
        results["Kaplan"] = audit_kaplan(sb, args.dry_run)
    if args.source in ("extra", "all"):
        results["Extra_QB"] = audit_extra(sb, args.dry_run)
    if args.source in ("kevin", "all"):
        results["Kevin"] = audit_kevin(sb, args.dry_run)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_opt = total_ans = total_upd = 0
    for src, r in results.items():
        print(f"  {src:<12} matched={r['matched']:5d}  opt_wrong={r['opt_wrong']:4d}  "
              f"ans_wrong={r['ans_wrong']:4d}  updated={r['updated']:4d}")
        total_opt += r["opt_wrong"]
        total_ans += r["ans_wrong"]
        total_upd += r["updated"]
    print(f"\n  Total option mismatches:  {total_opt}")
    print(f"  Total answer mismatches:  {total_ans}")
    print(f"  Total questions updated:  {total_upd}")
    if args.dry_run:
        print("\n  [DRY RUN] No changes written to DB.")
    else:
        print("\n  All changes applied to Supabase.")


if __name__ == "__main__":
    main()
