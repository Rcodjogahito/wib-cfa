#!/usr/bin/env python3
"""
Kaplan Mock Answer audit using the xa0xa0 (non-breaking space) marker.

Kaplan Mock ANS PDFs encode the correct answer by appending xa0xa0
to the last line of the correct option text. 100% coverage confirmed.

Run:
  python scripts/kaplan_mock_xa0_audit.py [--dry-run]

Outputs:
  Temp/kaplan_mock_fixes.json
  Temp/apply_kaplan_mock_fixes.ps1
"""
import sys, json, re, argparse
from pathlib import Path
from difflib import SequenceMatcher
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import fitz

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

MOCK_DIR  = Path(r"D:\CLAUDE\Projet CFA\CFA L1\8. KAPLAN MOCK-1100 MCQs")
DUMP_FILE = Path(r"C:\Users\codjo\AppData\Local\Temp\wib_dump_fresh.json")
OUT_FIXES = Path(r"C:\Users\codjo\AppData\Local\Temp\kaplan_mock_fixes.json")
OUT_PS1   = Path(r"C:\Users\codjo\AppData\Local\Temp\apply_kaplan_mock_fixes.ps1")

API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ"
    ".epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8"
)
SUPABASE_URL = "https://qlcakqtrambahrofnhho.supabase.co/rest/v1/questions"

MOCK_FILES = [
    "Mock Exam 1 - Answers.pdf",
    "Mock Exam 2 - Answers.pdf",
    "Mock Exam 3 - Answers.pdf",
    "Mock Exam 4 - Answers.pdf",
    "Mock Exam 5 - Answers.pdf",
    "Mock Exam 6 - Answers.pdf",
]

# ── Text normalization ────────────────────────────────────────────────────────
def _norm(t: str) -> str:
    if not t: return ""
    t = t.lower().strip()
    t = re.sub(r'[^a-z0-9 ]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()

# ── PDF parser ────────────────────────────────────────────────────────────────
def extract_mock_pdf(pdf_path: Path) -> list:
    """Extract all questions from a Kaplan Mock ANS PDF.
    Returns list of dicts: {qnum, qid, stem, opt_a, opt_b, opt_c, detected, expl}
    """
    doc = fitz.open(str(pdf_path))
    full_text = "".join(page.get_text("text") + "\n" for page in doc)
    doc.close()

    # Total questions: "of NNN" at header of each question
    total_m = re.search(r'Question #1 of (\d+)', full_text)
    total = int(total_m.group(1)) if total_m else 180
    pattern = rf'Question #(\d+) of {total}\n'

    parts = re.split(pattern, full_text)
    results = []

    for i in range(1, len(parts), 2):
        qnum = int(parts[i])
        content = parts[i+1] if i+1 < len(parts) else ""

        # Extract Question ID
        m_id = re.search(r'Question ID: (\d+)', content)
        qid = m_id.group(1) if m_id else None

        # Remove "Question ID: XXXX\n" from body
        body = re.sub(r'Question ID: \d+\n?', '', content)

        # Split into sections by option marker: "A)\n" or "A) text"
        # Pattern: letter at start of line, followed by ) and optional space/newline
        sections = re.split(r'(?m)^([ABC])\)\s*\n?', body)
        # sections[0] = stem, then alternating: letter, text_block

        stem = sections[0].strip()
        opts = {}
        expl = ""
        detected = None

        for j in range(1, len(sections), 2):
            letter = sections[j]
            text_block = sections[j+1] if j+1 < len(sections) else ""

            # Split off Explanation
            if 'Explanation\n' in text_block:
                opt_part, expl_part = text_block.split('Explanation\n', 1)
                opts[letter] = opt_part
                expl = expl_part
            else:
                opts[letter] = text_block

            # Detect marker: any line ending with \xa0 (non-breaking space)
            # Do NOT rstrip — the marker is trailing \xa0 chars
            lines = text_block.split('\n')
            for line in lines:
                if '\xa0' in line and line.rstrip(' \t').endswith('\xa0'):
                    detected = letter
                    break

        # Clean option text
        def clean_opt(t):
            return re.sub(r'\xa0', ' ', t).strip()

        results.append({
            "qnum": qnum,
            "qid": qid,
            "stem": stem[:200],
            "opt_a": clean_opt(opts.get("A", "")),
            "opt_b": clean_opt(opts.get("B", "")),
            "opt_c": clean_opt(opts.get("C", "")),
            "detected": detected,
            "expl": expl[:300],
        })

    return results, total

# ── Fast n-gram index for DB matching ────────────────────────────────────────
def build_ngram_index(rows: list, n=4) -> dict:
    """Build inverted n-gram index: ngram -> list of (idx, row)."""
    from collections import defaultdict
    idx = defaultdict(list)
    for i, row in enumerate(rows):
        words = _norm(row.get("question_en", "")).split()
        grams = {" ".join(words[j:j+n]) for j in range(len(words)-n+1)} if len(words) >= n else set()
        for g in grams:
            idx[g].append(i)
    return idx

_DB_IDX: dict = {}
_DB_ROWS: list = []

def init_index(db_kaplan: list):
    global _DB_IDX, _DB_ROWS
    _DB_ROWS = db_kaplan
    _DB_IDX = build_ngram_index(db_kaplan)

def match_to_db(pdf_q: dict, threshold=0.78) -> tuple:
    """Match PDF question to DB row via n-gram index + SequenceMatcher on top candidates."""
    from collections import defaultdict
    stem = pdf_q["stem"]
    if not stem or len(stem) < 15:
        return None, 0.0

    words = _norm(stem).split()
    n = 4
    grams = [" ".join(words[j:j+n]) for j in range(len(words)-n+1)] if len(words) >= n else []

    # Count gram overlaps
    candidate_hits = defaultdict(int)
    for g in grams:
        for idx in _DB_IDX.get(g, []):
            candidate_hits[idx] += 1

    # Sort by hits, take top 30
    top = sorted(candidate_hits.items(), key=lambda x: -x[1])[:30]
    if not top:
        # Fallback: use shorter n-gram
        grams2 = [" ".join(words[j:j+2]) for j in range(len(words)-1)] if len(words) >= 2 else []
        for g in grams2:
            for idx in _DB_IDX.get(g, []):
                candidate_hits[idx] += 1
        top = sorted(candidate_hits.items(), key=lambda x: -x[1])[:30]

    best_row, best_score, second_score = None, 0.0, 0.0
    for idx, _ in top:
        row = _DB_ROWS[idx]
        s = sim(stem, row.get("question_en", ""))
        if s > best_score:
            second_score = best_score
            best_score = s
            best_row = row
        elif s > second_score:
            second_score = s

    if best_score < threshold:
        return None, best_score
    if best_score - second_score < 0.05:
        return None, best_score  # ambiguous
    return best_row, best_score

# ── P2 validation on DB explanation ──────────────────────────────────────────
def p2_validate(detected: str, opts: dict, db_expl: str) -> bool:
    """Check if detected option text appears in DB explanation (brief check)."""
    if not db_expl or not detected:
        return False
    opt_text = opts.get(detected, "")
    if not opt_text or len(opt_text) < 8:
        return False
    clean = _norm(opt_text)
    key = clean[:30].rstrip()
    if len(key) < 6:
        return False
    return key in db_expl.lower()

# ── Main ──────────────────────────────────────────────────────────────────────
print("Loading DB dump...")
with open(DUMP_FILE, encoding='utf-8') as f:
    dump = json.load(f)
db_kaplan = [r for r in dump if r.get("source") == "Kaplan"]
print(f"Kaplan rows in DB: {len(db_kaplan)}")
print("Building n-gram index...")
init_index(db_kaplan)
print("Index ready.")
print()

all_pdf_questions = []
for fname in MOCK_FILES:
    path = MOCK_DIR / fname
    if not path.exists():
        print(f"[SKIP] {fname}")
        continue
    qs, total = extract_mock_pdf(path)
    marker_count = sum(1 for q in qs if q["detected"])
    print(f"{fname}: {len(qs)} Q, {marker_count} with \\xa0\\xa0 marker")
    for q in qs:
        q["_pdf_file"] = fname
    all_pdf_questions.extend(qs)

print(f"\nTotal PDF questions: {len(all_pdf_questions)}")
print(f"With \\xa0\\xa0 detected: {sum(1 for q in all_pdf_questions if q['detected'])}")
print()

# Match and compare
matched = 0
no_match = 0
no_marker = 0
ok = 0
fixes = []
seen_db_uuids = set()

for pdf_q in all_pdf_questions:
    if not pdf_q["detected"]:
        no_marker += 1
        continue

    db_row, score = match_to_db(pdf_q)
    if db_row is None:
        no_match += 1
        continue

    uid = db_row["id"]
    if uid in seen_db_uuids:
        continue  # dedup: keep only first match per UUID
    seen_db_uuids.add(uid)
    matched += 1

    stored   = (db_row.get("correct_answer") or "").upper().strip()
    detected = pdf_q["detected"].upper()

    if stored == detected:
        ok += 1
        continue

    # Mismatch found — gather info
    opts = {"A": pdf_q["opt_a"], "B": pdf_q["opt_b"], "C": pdf_q["opt_c"]}
    p2_ok = p2_validate(detected, opts, db_row.get("explanation_en", ""))

    entry = {
        "id":       uid,
        "q_text":   pdf_q["stem"][:80],
        "stored":   stored,
        "detected": detected,
        "score":    round(score, 3),
        "p2_ok":    p2_ok,
        "pdf_file": pdf_q["_pdf_file"],
        "qnum":     pdf_q["qnum"],
        "expl_db":  (db_row.get("explanation_en") or "")[:200],
    }
    fixes.append(entry)

print(f"Results:")
print(f"  Matched:      {matched}")
print(f"  No match:     {no_match}")
print(f"  No marker:    {no_marker}")
print(f"  OK (agree):   {ok}")
print(f"  Mismatches:   {len(fixes)}")
print()

if fixes:
    print(f"=== {len(fixes)} mismatches ===")
    p2_hits = sum(1 for f in fixes if f["p2_ok"])
    print(f"  P2 confirmed: {p2_hits} / {len(fixes)}")
    print()
    for f in fixes:
        p2_tag = "[P2✓]" if f["p2_ok"] else "[P2?]"
        print(f"  {f['id'][:8]}  {f['stored']}->{f['detected']}  {p2_tag}  sim={f['score']}  {f['pdf_file']} Q{f['qnum']}")
        print(f"    Q: {f['q_text'][:80]}")
        print(f"    Expl: {f['expl_db'][:120]}")

with open(OUT_FIXES, "w", encoding="utf-8") as f:
    json.dump(fixes, f, indent=2, ensure_ascii=False)
print(f"\nFixes -> {OUT_FIXES}")

if not fixes:
    print("No mismatches — Kaplan Mocks fully consistent.")
    sys.exit(0)

if args.dry_run:
    print("[DRY RUN] PS1 not written.")
    sys.exit(0)

# Generate PS1
lines = [
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8",
    "$headers = @{",
    f'    "apikey"        = "{API_KEY}"',
    f'    "Authorization" = "Bearer {API_KEY}"',
    '    "Content-Type"  = "application/json"',
    '    "Prefer"        = "return=minimal"',
    "}",
    "$ok = 0; $err = 0",
    "",
]
for fix in fixes:
    url  = f"{SUPABASE_URL}?id=eq.{fix['id']}"
    desc = fix["q_text"][:60].replace("'", "''").encode("ascii", errors="replace").decode()
    p2_tag = "P2ok" if fix["p2_ok"] else "P2?"
    lines.append(f"# [{p2_tag}] {fix['stored']}->{fix['detected']}  {fix['pdf_file']} Q{fix['qnum']}  {desc}")
    lines.append(f'$body = \'{{"correct_answer":"{fix["detected"]}"}}\' ')
    lines.append("try {")
    lines.append(f'    Invoke-WebRequest -Uri "{url}" -Method PATCH -Headers $headers -Body $body -SkipCertificateCheck -UseBasicParsing | Out-Null')
    lines.append(f'    $ok++; Write-Host "OK  {fix["id"][:8]}  {fix["stored"]}->{fix["detected"]}"')
    lines.append("} catch {")
    lines.append(f'    $err++; Write-Host "ERR {fix["id"][:8]}: $_"')
    lines.append("}")
    lines.append("")
lines += ['Write-Host ""', 'Write-Host "Done: $ok OK, $err errors"']
with open(OUT_PS1, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"PS1 -> {OUT_PS1}")
