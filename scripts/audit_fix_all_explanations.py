#!/usr/bin/env python3
"""
Audit + fix ALL explanations for text-based sources:
  - UWorld    (1,897 Q) — Answers PDFs, extraction via fontname checkmark
  - Kaplan    (3,717 Q) — QSTN WITH ANS PDFs + Mock PDFs
  - Extra_QB  (  333 Q) — EXTRA 700 MCQs.pdf pages 128-214
  - Kevin_Mock(  180 Q) — SESSION 1/2 MOCK-A.pdf

CFA_WEB: skipped (scanned PDFs, no text extraction possible without Vision).

Strategy per source:
  1. Re-parse source PDFs (same logic as original import scripts)
  2. Build normalized stem → explanation lookup
  3. Fetch all DB questions for that source
  4. Match each DB question to extracted explanation via multi-tier normalized stem
  5. If stored explanation DIFFERS from extracted → update DB

Usage:
    cd D:\\CLAUDE\\Projet CFA\\wib-cfa
    python scripts/audit_fix_all_explanations.py [--dry-run] [--source uworld|kaplan|extra|kevin|all]
"""
import sys, re, argparse, warnings, logging
from pathlib import Path
import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)
for _name in list(logging.Logger.manager.loggerDict):
    logging.getLogger(_name).setLevel(logging.CRITICAL)


# ── Paths ─────────────────────────────────────────────────────────────────────
BASE         = Path(r"D:\CLAUDE\Projet CFA\CFA L1")
UWORLD_ROOT  = BASE / "6. TOUGH QB UWORLD-2000 MCQs"
KAPLAN_ROOT  = BASE / "2. QB KAPLAN-3000 MCQs"
MOCK_ROOT    = BASE / "8. KAPLAN MOCK-1100 MCQs"
EXTRA_PDF    = BASE / "7. EXTRA QB-700MCQs" / "EXTRA 700 MCQs.pdf"
KEVIN_A1     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 1 MOCK-A.pdf"
KEVIN_Q1     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 1 MOCK-Q.pdf"
KEVIN_A2     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 2 MOCK-A.pdf"
KEVIN_Q2     = BASE / "11. KEVIN SIR_s MOCK" / "SESSION 2 MOCK-Q.pdf"
SECRETS_PATH = Path(".streamlit/secrets.toml")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _sanitize(s):
    return (s or "").replace("\x00", "").strip()

def _norm(text, length=120):
    return re.sub(r"\s+", " ", (text or "").lower().strip())[:length]

def _sim(a, b):
    """Rough word-overlap similarity between two strings."""
    wa = set(re.findall(r"\w+", (a or "").lower()))
    wb = set(re.findall(r"\w+", (b or "").lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))

def _load_secrets():
    result = {}; section = None
    with open(SECRETS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]; result[section] = {}
            elif "=" in line and section:
                k, _, v = line.partition("=")
                result[section][k.strip()] = v.strip().strip('"').strip("'")
    return result

def get_sb():
    secrets = _load_secrets()
    url = secrets["supabase"]["SUPABASE_URL"]
    key = secrets["supabase"].get("SUPABASE_SERVICE_KEY") or secrets["supabase"]["SUPABASE_ANON_KEY"]
    from supabase import create_client
    return create_client(url, key)

def _pdf_text(path):
    chunks = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                try:
                    t = page.extract_text()
                    if t:
                        chunks.append(t)
                except Exception:
                    pass
    except Exception as e:
        print(f"  [WARN] {Path(path).name}: {e}")
        sys.stdout.flush()
    return "\n".join(chunks)

def _pdf_words(path):
    words = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                words.extend(page.extract_words(extra_attrs=["fontname"]))
    except Exception as e:
        print(f"  [WARN] words error {path.name}: {e}")
    return words

def _build_lookup(items, min_length=25):
    """Build multi-tier normalized lookup: {(length, norm_key): (expl_text, pdf_stem)}"""
    lut = {}
    for stem, expl in items:
        for length in [120, 80, 60, 40, 25]:
            if length < min_length:
                continue
            k = _norm(stem, length)
            if k and (length, k) not in lut:
                lut[(length, k)] = (expl, stem)
    return lut

def _lookup(lut, db_stem, min_length=25):
    """Returns (explanation, pdf_stem, match_length) or (None, None, 0)."""
    for length in [120, 80, 60, 40, 25]:
        if length < min_length:
            continue
        k = _norm(db_stem, length)
        if (length, k) in lut:
            expl, pdf_stem = lut[(length, k)]
            return expl, pdf_stem, length
    return None, None, 0

def _fetch_source(sb, source):
    """Fetch all questions for a source from Supabase (paginated)."""
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (sb.table("questions")
                .select("id,question_en,subtopic,explanation_en,source")
                .eq("source", source)
                .range(offset, offset + page_size - 1)
                .execute())
        rows = resp.data or []
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size
    return all_rows

def _apply_updates(sb, updates, source, dry_run):
    if dry_run:
        print(f"  [DRY RUN] Would update {len(updates)} {source} explanations")
        for u in updates[:20]:
            sim = _sim(u['stem'], u.get('pdf_stem', u['stem']))
            print(f"    [sim={sim:.2f} match@{u.get('match_len',0)}] Q: {u['stem'][:80]}")
            print(f"    OLD: {(u['old'] or '')[:120]}")
            print(f"    NEW: {u['new'][:120]}")
            print()
        if len(updates) > 20:
            print(f"    ... and {len(updates)-20} more")
        return

    updated = 0
    errors = 0
    for i in range(0, len(updates), 50):
        batch = updates[i:i+50]
        for upd in batch:
            try:
                sb.table("questions").update(
                    {"explanation_en": upd["new"]}
                ).eq("id", upd["id"]).execute()
                updated += 1
            except Exception as e:
                print(f"  [ERROR] {upd['id']}: {e}")
                errors += 1
        print(f"  Updated {min(i+50, len(updates))}/{len(updates)}", end="\r")
    print()
    print(f"  Done — {updated} updated, {errors} errors")


# ═══════════════════════════════════════════════════════════════════════════════
# UWORLD
# ═══════════════════════════════════════════════════════════════════════════════

UWORLD_TOPIC_MAP = {
    "1. Quantitative Methods":           "Quantitative Methods",
    "2. Economics":                      "Economics",
    "3. Portfolio Management":           "Portfolio Management",
    "4. Corporate Issuers":              "Corporate Issuers",
    "5. Financial Statement Analysis":   "Financial Statement Analysis",
    "6. Equity Investments":             "Equity Investments",
    "7. Fixed Income":                   "Fixed Income",
    "8. Derivatives":                    "Derivatives",
    "9. Alternative Investments":        "Alternative Investments",
    "10. Ethics":                        "Ethics & Professional Standards",
}

_CHECKMARK = ""

# PDFs confirmed to hang in pdfplumber (complex font encoding on specific pages).
# Explanations for these subtopics were correctly imported; skip re-audit for them.
_UWORLD_PDF_SKIP = {
    "1.03 Statistical Measures of Asset Returns",
    "5.12 Introduction to Financial Statement Modeling",
    "11.03 Guidance For Standards I–VII",
}

def _parse_uworld_answers_pdf(path):
    """
    Re-parse one UWorld Answers PDF.
    Returns list of (question_stem, explanation).
    NOTE: skip checkmark detection (_pdf_words) — only need explanations for the audit.
    """
    # Skip PDFs known to cause pdfplumber hangs
    stem_base = path.stem.replace(" - Answers", "")
    if stem_base in _UWORLD_PDF_SKIP:
        print(f"    [SKIP] {path.name} — known hang")
        sys.stdout.flush()
        return []

    q_pdf_name = stem_base + ".pdf"
    topic_folder = path.parent
    q_pdf = topic_folder / "ONLY QSTN" / q_pdf_name
    if not q_pdf.exists():
        return []

    # Parse question stems from ONLY QSTN PDF
    q_text = _pdf_text(q_pdf)
    questions = []
    parts = re.split(r"Question\s+(\d+)\n", q_text)
    for i in range(1, len(parts), 2):
        try:
            num = int(parts[i])
        except ValueError:
            continue
        block = (parts[i+1] if i+1 < len(parts) else "").strip()
        m = re.match(r"(.+?)\nA\.\s+(.+?)\nB\.\s+(.+?)\nC\.\s+(.+)", block, re.DOTALL)
        if not m:
            continue
        q_text_clean = " ".join(m.group(1).split())
        if len(q_text_clean) < 15:
            continue
        questions.append({"num": num, "question": q_text_clean})

    # Parse explanations from Answers PDF (text only — no word extraction needed)
    text = _pdf_text(path)

    q_nums = []
    for m in re.finditer(r"^(\d+)\.\s*([A-Z][^.])", text, re.MULTILINE):
        try:
            q_nums.append(int(m.group(1)))
        except ValueError:
            pass

    explanations = []
    for m in re.finditer(r"Explanation\n(.+?)(?=\n\d+\.\s+[A-Z]|\Z)", text, re.DOTALL):
        expl = m.group(1)
        expl = re.split(r"Things to remember:|LOS\s*\n|Copyright", expl)[0]
        expl = _sanitize(" ".join(expl.split()))
        explanations.append(expl)

    answers = {}
    for idx, qnum in enumerate(q_nums):
        answers[qnum] = {
            "explanation": explanations[idx] if idx < len(explanations) else "",
        }

    result = []
    for q in questions:
        ans = answers.get(q["num"])
        if ans and ans["explanation"]:
            result.append((_sanitize(q["question"]), _sanitize(ans["explanation"])))
    return result


def audit_uworld(sb, dry_run):
    print("\n" + "="*60)
    print("UWORLD AUDIT")
    print("="*60)

    # Build full PDF lookup: stem → explanation
    pairs = []
    total_pdfs = 0
    for folder_name in UWORLD_TOPIC_MAP:
        folder = UWORLD_ROOT / folder_name
        if not folder.exists():
            print(f"  [SKIP] folder not found: {folder_name}")
            sys.stdout.flush()
            continue
        ans_pdfs = sorted(folder.glob("*- Answers.pdf"))
        print(f"  {folder_name}: {len(ans_pdfs)} answer PDFs")
        sys.stdout.flush()
        for ans_pdf in ans_pdfs:
            print(f"    parsing {ans_pdf.name} …", end=" ")
            sys.stdout.flush()
            parsed = _parse_uworld_answers_pdf(ans_pdf)
            pairs.extend(parsed)
            total_pdfs += 1
            print(f"{len(parsed)} pairs")
            sys.stdout.flush()

    print(f"Parsed {len(pairs)} Q+expl pairs from {total_pdfs} UWorld PDFs")
    sys.stdout.flush()
    # min_length=120: only match on 120-char prefixes to avoid false positives from
    # generic question openings like "An analyst gathers the following information..."
    lut = _build_lookup(pairs, min_length=120)

    db_qs = _fetch_source(sb, "UWorld")
    print(f"Fetched {len(db_qs)} UWorld questions from DB")

    matched = 0
    no_match = 0
    same = 0
    updates = []
    empty_in_pdf = 0
    low_sim_skipped = 0

    for row in db_qs:
        stem = row.get("question_en") or ""
        fresh, pdf_stem, match_len = _lookup(lut, stem, min_length=120)
        if fresh is None:
            no_match += 1
            continue
        if not fresh.strip():
            empty_in_pdf += 1
            continue
        # Validate: DB stem must have ≥40% word overlap with matched PDF stem
        sim = _sim(stem, pdf_stem)
        if sim < 0.40:
            low_sim_skipped += 1
            continue
        matched += 1
        stored = (row.get("explanation_en") or "").strip()
        if _norm(stored, 120) == _norm(fresh, 120):
            same += 1
        else:
            updates.append({
                "id": row["id"],
                "stem": stem,
                "pdf_stem": pdf_stem,
                "match_len": match_len,
                "old": stored,
                "new": fresh,
            })

    print(f"  Matched: {matched} | No match: {no_match} | Empty in PDF: {empty_in_pdf} | Low-sim skipped: {low_sim_skipped}")
    print(f"  Already correct: {same} | Need update: {len(updates)}")

    if updates:
        _apply_updates(sb, updates, "UWorld", dry_run)
    else:
        print("  Nothing to update.")

    return {"matched": matched, "no_match": no_match, "same": same, "updated": len(updates)}


# ═══════════════════════════════════════════════════════════════════════════════
# KAPLAN
# ═══════════════════════════════════════════════════════════════════════════════

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

def _parse_kaplan_pdf(path):
    """
    Parse one Kaplan Answers PDF.
    Returns list of (question_stem, explanation).
    """
    text = _pdf_text(path)
    pairs = []
    parts = re.split(r"Question\s+#(\d+)\s+of\s+\d+\s*\n", text)
    for i in range(1, len(parts), 2):
        block = (parts[i+1] if i+1 < len(parts) else "").strip()
        block = re.sub(r"Question\s+ID:\s*\d+\s*\n?", "", block, count=1)
        m = re.match(
            r"(.+?)\nA\)\s+(.+?)\nB\)\s+(.+?)\nC\)\s+(.+?)\nExplanation\n(.+)",
            block, re.DOTALL
        )
        if not m:
            continue
        q_text = _sanitize(" ".join(m.group(1).split()))
        expl_raw = m.group(5).strip()
        expl = re.split(r"\(Module\s+\d+|\nQuestion\s+#", expl_raw)[0].strip()
        expl = _sanitize(" ".join(expl.split()))
        if len(q_text) < 10 or not expl:
            continue
        pairs.append((q_text, expl))
    return pairs


def audit_kaplan(sb, dry_run):
    print("\n" + "="*60)
    print("KAPLAN AUDIT")
    print("="*60)

    pairs = []
    total_pdfs = 0

    # QB PDFs
    ans_dir = KAPLAN_ROOT / "QSTN WITH ANS"
    if ans_dir.exists():
        for folder_name in KAPLAN_TOPIC_MAP:
            topic_dir = ans_dir / folder_name
            if not topic_dir.exists():
                continue
            for pdf in sorted(topic_dir.glob("*- Answers.pdf")):
                parsed = _parse_kaplan_pdf(pdf)
                pairs.extend(parsed)
                total_pdfs += 1

    # Mock PDFs
    if MOCK_ROOT.exists():
        for pdf in sorted(MOCK_ROOT.glob("Mock Exam * - Answers.pdf")):
            parsed = _parse_kaplan_pdf(pdf)
            pairs.extend(parsed)
            total_pdfs += 1

    print(f"Parsed {len(pairs)} Q+expl pairs from {total_pdfs} Kaplan PDFs")
    lut = _build_lookup(pairs)

    db_qs = _fetch_source(sb, "Kaplan")
    print(f"Fetched {len(db_qs)} Kaplan questions from DB")

    matched = 0
    no_match = 0
    same = 0
    updates = []
    empty_in_pdf = 0

    for row in db_qs:
        stem = row.get("question_en") or ""
        fresh, pdf_stem, match_len = _lookup(lut, stem)
        if fresh is None:
            no_match += 1
            continue
        if not fresh.strip():
            empty_in_pdf += 1
            continue
        matched += 1
        stored = (row.get("explanation_en") or "").strip()
        if _norm(stored, 120) == _norm(fresh, 120):
            same += 1
        else:
            updates.append({
                "id": row["id"],
                "stem": stem,
                "pdf_stem": pdf_stem,
                "match_len": match_len,
                "old": stored,
                "new": fresh,
            })

    print(f"  Matched: {matched} | No match: {no_match} | Empty in PDF: {empty_in_pdf}")
    print(f"  Already correct: {same} | Need update: {len(updates)}")

    if updates:
        _apply_updates(sb, updates, "Kaplan", dry_run)
    else:
        print("  Nothing to update.")

    return {"matched": matched, "no_match": no_match, "same": same, "updated": len(updates)}


# ═══════════════════════════════════════════════════════════════════════════════
# EXTRA QB
# ═══════════════════════════════════════════════════════════════════════════════

SECTION_MAP_EXTRA = {
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

def _match_section_extra(line):
    low = line.lower()
    for pattern, topic in SECTION_MAP_EXTRA.items():
        if re.search(pattern, low):
            return topic
    return None

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

def _clean_expl(text):
    text = text.replace("•", "•").replace("–", "-").replace("—", "=")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\d{1,3}\s*$", "", text, flags=re.MULTILINE)
    return text.strip()

def _parse_extra_questions():
    """Returns {(topic, qnum): stem}"""
    with pdfplumber.open(EXTRA_PDF) as pdf:
        q_parts = [pdf.pages[pi].extract_text() or "" for pi in range(0, 127)]
    q_text = "\n".join(q_parts)
    q_lines = q_text.split("\n")

    stem_map = {}
    current_topic = "Ethics & Professional Standards"
    i = 0
    while i < len(q_lines):
        line = q_lines[i].strip()
        if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", line) and not re.match(r"^\d", line):
            t = _match_section_extra(line)
            if t:
                current_topic = t
            i += 1
            continue
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
                if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", nxt) and _match_section_extra(nxt):
                    break
                stem_parts.append(nxt)
                i += 1
            stem = " ".join(s for s in stem_parts if s).strip()
            key = (current_topic, qnum)
            if key not in stem_map:
                stem_map[key] = stem
        else:
            i += 1
    return stem_map

def _parse_extra_explanations():
    """Returns {(topic, qnum): {"correct": letter, "expl": text}}"""
    TOPIC_MARKER = "\x00TOPIC\x00"
    pages_data = []
    with pdfplumber.open(EXTRA_PDF) as pdf:
        sol_topic = "Ethics & Professional Standards"
        for pi in range(127, min(214, len(pdf.pages))):
            raw = pdf.pages[pi].extract_text() or ""
            text = _de_triple(raw)
            for ln in text.split("\n"):
                ln = ln.strip()
                if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", ln) and not re.match(r"^\d", ln):
                    t = _match_section_extra(ln)
                    if t:
                        sol_topic = t
                        break
            pages_data.append((pi, sol_topic, text))

    chunks = []
    prev_topic = None
    for _, topic, text in pages_data:
        if topic != prev_topic:
            chunks.append(f"{TOPIC_MARKER}{topic}{TOPIC_MARKER}")
            prev_topic = topic
        chunks.append(text)
    full_text = "\n".join(chunks)

    topic_blocks = re.split(r"\x00TOPIC\x00([^\x00]+)\x00TOPIC\x00", full_text)
    results = {}
    i = 1
    while i < len(topic_blocks) - 1:
        topic = topic_blocks[i].strip()
        block = topic_blocks[i+1]
        i += 2
        ans_pattern = re.compile(r"(\d{1,3})\.\s+Answer\s*[=:]\s*([A-C])\b", re.IGNORECASE)
        matches = list(ans_pattern.finditer(block))
        for j, m in enumerate(matches):
            qnum = int(m.group(1))
            letter = m.group(2).upper()
            expl_start = m.end()
            expl_end = matches[j+1].start() if j+1 < len(matches) else len(block)
            expl = _clean_expl(block[expl_start:expl_end])
            key = (topic, qnum)
            if key not in results:
                results[key] = {"correct": letter, "expl": expl}
    return results


def audit_extra_qb(sb, dry_run):
    print("\n" + "="*60)
    print("EXTRA_QB AUDIT")
    print("="*60)

    stem_map = _parse_extra_questions()
    expl_map = _parse_extra_explanations()
    print(f"PDF: {len(stem_map)} stems | {len(expl_map)} answer entries")

    # Build lookup: stem → (correct, expl)
    merged_pairs = []
    for (topic, qnum), stem in stem_map.items():
        key = (topic, qnum)
        if key in expl_map and expl_map[key]["expl"]:
            merged_pairs.append((stem, expl_map[key]["expl"]))

    print(f"Merged: {len(merged_pairs)} with explanation")
    lut = _build_lookup(merged_pairs)

    db_qs = _fetch_source(sb, "Extra_QB")
    print(f"Fetched {len(db_qs)} Extra_QB questions from DB")

    matched = 0
    no_match = 0
    same = 0
    empty_db_no_pdf = 0
    updates = []

    for row in db_qs:
        stem = row.get("question_en") or ""
        fresh, pdf_stem, match_len = _lookup(lut, stem)
        stored = (row.get("explanation_en") or "").strip()

        if fresh is None:
            no_match += 1
            continue

        if not fresh.strip():
            empty_db_no_pdf += 1
            continue

        matched += 1
        if _norm(stored, 120) == _norm(fresh, 120):
            same += 1
        else:
            updates.append({
                "id": row["id"],
                "stem": stem,
                "pdf_stem": pdf_stem,
                "match_len": match_len,
                "old": stored,
                "new": fresh,
            })

    print(f"  Matched: {matched} | No match: {no_match} | Empty in PDF: {empty_db_no_pdf}")
    print(f"  Already correct: {same} | Need update: {len(updates)}")

    if updates:
        _apply_updates(sb, updates, "Extra_QB", dry_run)
    else:
        print("  Nothing to update.")

    return {"matched": matched, "no_match": no_match, "same": same, "updated": len(updates)}


# ═══════════════════════════════════════════════════════════════════════════════
# KEVIN MOCK
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_kevin_answers(q_pdf, a_pdf):
    """Returns list of (stem, explanation)"""
    q_text = _pdf_text(q_pdf)
    a_text = _pdf_text(a_pdf)

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
                if re.match(r"^[A-C]\.\s+", nxt) or re.match(r"^\d+\.\s+", nxt):
                    break
                stem_parts.append(nxt)
                i += 1
            raw_questions[qnum] = " ".join(s for s in stem_parts if s)
        else:
            i += 1

    # Parse answers + explanations
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
                "expl": " ".join(s for s in expl_parts if s),
            }
        else:
            i += 1

    pairs = []
    for qnum, stem in raw_questions.items():
        a = raw_answers.get(qnum)
        if a and a["expl"]:
            pairs.append((_sanitize(stem), _sanitize(a["expl"])))
    return pairs


def audit_kevin(sb, dry_run):
    print("\n" + "="*60)
    print("KEVIN_MOCK AUDIT")
    print("="*60)

    pairs = []
    for q_pdf, a_pdf in [(KEVIN_Q1, KEVIN_A1), (KEVIN_Q2, KEVIN_A2)]:
        parsed = _parse_kevin_answers(q_pdf, a_pdf)
        pairs.extend(parsed)
        print(f"  {a_pdf.name}: {len(parsed)} pairs")

    print(f"Total: {len(pairs)} Q+expl pairs")
    # min_length=60: prevents false positives from short common question openings
    lut = _build_lookup(pairs, min_length=60)

    db_qs = _fetch_source(sb, "Kevin_Mock")
    print(f"Fetched {len(db_qs)} Kevin_Mock questions from DB")

    matched = 0
    no_match = 0
    same = 0
    updates = []
    low_sim_skipped = 0

    for row in db_qs:
        stem = row.get("question_en") or ""
        fresh, pdf_stem, match_len = _lookup(lut, stem, min_length=60)
        if fresh is None:
            no_match += 1
            continue
        if not fresh.strip():
            continue
        # Validate: DB stem must have ≥40% word overlap with matched PDF stem
        sim = _sim(stem, pdf_stem)
        if sim < 0.40:
            low_sim_skipped += 1
            continue
        matched += 1
        stored = (row.get("explanation_en") or "").strip()
        content_differs = _norm(stored, 120) != _norm(fresh, 120)
        fresh_is_fuller = _norm(stored, 120) == _norm(fresh, 120) and len(fresh) > len(stored) + 30
        if content_differs or fresh_is_fuller:
            updates.append({
                "id": row["id"],
                "stem": stem,
                "pdf_stem": pdf_stem,
                "match_len": match_len,
                "old": stored,
                "new": fresh,
            })
        else:
            same += 1

    print(f"  Matched: {matched} | No match: {no_match} | Low-sim skipped: {low_sim_skipped}")
    print(f"  Already correct: {same} | Need update: {len(updates)}")

    if updates:
        _apply_updates(sb, updates, "Kevin_Mock", dry_run)
    else:
        print("  Nothing to update.")

    return {"matched": matched, "no_match": no_match, "same": same, "updated": len(updates)}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would change, don't write")
    parser.add_argument("--source", choices=["uworld","kaplan","extra","kevin","all"], default="all")
    args = parser.parse_args()

    print("Connecting to Supabase …")
    sb = get_sb()
    print("Connected.\n")

    results = {}

    if args.source in ("uworld", "all"):
        results["uworld"] = audit_uworld(sb, args.dry_run)

    if args.source in ("kaplan", "all"):
        results["kaplan"] = audit_kaplan(sb, args.dry_run)

    if args.source in ("extra", "all"):
        results["extra"] = audit_extra_qb(sb, args.dry_run)

    if args.source in ("kevin", "all"):
        results["kevin"] = audit_kevin(sb, args.dry_run)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    total_updated = 0
    total_no_match = 0
    for src, r in results.items():
        print(f"  {src.upper():12s} matched={r['matched']:4d}  no_match={r['no_match']:4d}  "
              f"same={r['same']:4d}  updated={r['updated']:4d}")
        total_updated += r['updated']
        total_no_match += r['no_match']

    print(f"\n  Total explanations updated: {total_updated}")
    print(f"  Total unmatched (no PDF entry found): {total_no_match}")
    if args.dry_run:
        print("\n  [DRY RUN] No changes written to DB.")
    else:
        print("\n  All changes applied to Supabase.")


if __name__ == "__main__":
    main()
