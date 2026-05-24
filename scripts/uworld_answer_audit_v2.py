#!/usr/bin/env python3
"""
UWorld Answer Audit v2 — Reliable checkmark-based verification.

Strategy:
1. For each topic (e.g., "1.01 Rates and Returns"):
   - Parse QSTN PDF (ONLY QSTN subfolder) to get question stems in order
   - Parse Answers PDF for checkmarks in order (FontAwesome font detection)
   - Validate counts match
   - Pair: stem_k <-> correct_letter_k
2. Match pairs against DB questions by stem similarity
3. Flag any stored correct_answer != pdf correct_letter

Handles both QSTN stem formats:
  - Standard: stem on own line, then '\nA. ...'
  - Compact: stem ends with '?'/':', options directly after: '...?A. ...'
"""
import json, re, sys, threading
from pathlib import Path

DUMP      = r"C:\Users\codjo\AppData\Local\Temp\wib_dump_fresh.json"
RESULTS_OUT = r"C:\Users\codjo\AppData\Local\Temp\uworld_v2_audit_results.json"
FIXES_OUT   = r"C:\Users\codjo\AppData\Local\Temp\uworld_v2_fixes.json"
PS1_OUT     = r"C:\Users\codjo\AppData\Local\Temp\apply_uworld_v2_fixes.ps1"

UWORLD_ROOT = Path(r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs")
SUPABASE_URL = "https://qlcakqtrambahrofnhho.supabase.co/rest/v1/questions"
API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ"
    ".epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8"
)
PDF_TIMEOUT = 45

import pdfplumber

def _sanitize(text):
    return re.sub(r'\s+', ' ', (text or '')).strip()

def _make_key(text, length=120):
    return re.sub(r'\s+', ' ', (text or '').lower()).strip()[:length]

def _pdf_text(path, timeout=PDF_TIMEOUT):
    buf, err = [], []
    def _r():
        try:
            with pdfplumber.open(path) as pdf:
                buf.append(''.join(p.extract_text() or '' for p in pdf.pages))
        except Exception as e:
            err.append(str(e))
    t = threading.Thread(target=_r, daemon=True); t.start(); t.join(timeout=timeout)
    if t.is_alive() or err:
        return ''
    return buf[0] if buf else ''

def _pdf_words(path, timeout=PDF_TIMEOUT):
    buf, err = [], []
    def _r():
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    buf.extend(page.extract_words(extra_attrs=['fontname']))
        except Exception as e:
            err.append(str(e))
    t = threading.Thread(target=_r, daemon=True); t.start(); t.join(timeout=timeout)
    if t.is_alive():
        return []
    return buf

def extract_stem(block):
    """Extract question stem from a question block, handling both layout formats."""
    # Format 1: options on own lines (\nA. ...)
    m = re.match(r'(.+?)\nA\.\s+\S', block, re.DOTALL)
    if m:
        return _sanitize(m.group(1))
    # Format 2: options directly after ?: with no leading newline
    m = re.match(r'(.+?)[?:]\s*A\.\s+\S', block, re.DOTALL)
    if m:
        stem_raw = m.group(1) + m.group(0)[len(m.group(1))]  # include trailing ? or :
        return _sanitize(m.group(1))
    return None

def parse_qstn_pdf(path):
    """
    Parse QSTN PDF → list of question stems in order (Q1, Q2, ...).
    """
    text = _pdf_text(path)
    if not text:
        return []
    parts = re.split(r'Question\s+(\d+)\n', text)
    stems = []
    for i in range(1, len(parts), 2):
        block = (parts[i+1] if i+1 < len(parts) else '').strip()
        stem = extract_stem(block)
        if stem and len(stem) > 10:
            stems.append(stem)
        else:
            # Keep None to preserve index alignment with checkmarks
            stems.append(None)
    return stems

def parse_answers_checkmarks(path):
    """
    Parse Answers PDF → list of correct letters (A/B/C) in question order.
    Detects FontAwesome Pro Light checkmarks that appear before the correct option letter.
    """
    words = _pdf_words(path)
    if not words:
        return []
    correct_in_order = []
    for i, w in enumerate(words):
        if 'FontAwesome' in (w.get('fontname') or ''):
            for j in range(i+1, min(i+5, len(words))):
                nxt = words[j]['text'].strip()
                if re.match(r'^[ABC]\.$', nxt):
                    correct_in_order.append(nxt[0])
                    break
                elif re.match(r'^[ABC]$', nxt):
                    correct_in_order.append(nxt)
                    break
    return correct_in_order

# ── Build topic file pairs ─────────────────────────────────────────────────────
def find_topic_pairs():
    """
    Match QSTN PDFs to Answers PDFs by stripping " - Answers" suffix.
    Returns list of (qstn_path, answers_path, label).
    """
    pairs = []
    for topic_dir in sorted(UWORLD_ROOT.iterdir()):
        if not topic_dir.is_dir():
            continue
        qstn_dir = topic_dir / "ONLY QSTN"
        if not qstn_dir.exists():
            continue
        for qstn_pdf in sorted(qstn_dir.glob("*.pdf")):
            stem_name = qstn_pdf.stem  # e.g., "1.01 Rates and Returns"
            answers_pdf = topic_dir / (stem_name + " - Answers.pdf")
            if answers_pdf.exists():
                pairs.append((qstn_pdf, answers_pdf, stem_name))
    return pairs

# ── Load DB ────────────────────────────────────────────────────────────────────
print("Loading dump...")
sys.stdout.flush()
with open(DUMP, encoding='utf-8') as f:
    dump = json.load(f)

uworld_db = [r for r in dump if r.get('source') == 'UWorld']
print(f"UWorld questions in DB: {len(uworld_db)}")

# Build key lookup: {80-char key: db_row} and {60-char key: db_row}
db_by_key80 = {}
db_by_key60 = {}
for row in uworld_db:
    k = _make_key(row.get('question_en') or '')
    if k:
        db_by_key80[k[:80]] = row
        db_by_key60[k[:60]] = row

def find_db_row(stem):
    k = _make_key(stem)
    return (db_by_key80.get(k[:80]) or db_by_key60.get(k[:60]))

# ── Run audit ──────────────────────────────────────────────────────────────────
pairs = find_topic_pairs()
print(f"\nTopic pairs found: {len(pairs)}")

all_verified = []  # {id, q_text, stored, pdf_answer, match: bool}
mismatches = []

skipped_pdfs = 0
total_paired = 0

for qstn_path, answers_path, label in pairs:
    stems = parse_qstn_pdf(qstn_path)
    checkmarks = parse_answers_checkmarks(answers_path)

    n_stems = sum(1 for s in stems if s is not None)
    n_check  = len(checkmarks)

    if n_stems == 0 or n_check == 0:
        print(f"  SKIP (empty) {label}")
        skipped_pdfs += 1
        continue

    if len(stems) != n_check:
        print(f"  SKIP (mismatch) {label}: {len(stems)} stems vs {n_check} checkmarks")
        skipped_pdfs += 1
        continue

    print(f"  OK  {label}: {n_check} Q")

    for idx, (stem, letter) in enumerate(zip(stems, checkmarks)):
        if stem is None or letter is None:
            continue
        row = find_db_row(stem)
        if row is None:
            continue
        total_paired += 1
        stored = (row.get('correct_answer') or '').upper().strip()
        match = (stored == letter)
        rec = {
            'id': row['id'],
            'q_text': stem[:80],
            'stored': stored,
            'pdf_answer': letter,
            'match': match,
            'topic': label,
        }
        all_verified.append(rec)
        if not match:
            mismatches.append(rec)
            # Print safely for Windows console
            q_safe = stem[:60].encode('ascii', errors='replace').decode()
            print(f"    MISMATCH {row['id'][:8]} | stored={stored} pdf={letter} | {q_safe}")

    sys.stdout.flush()

print(f"\n{'='*60}")
print(f"Topic pairs processed : {len(pairs) - skipped_pdfs}")
print(f"Topic pairs skipped   : {skipped_pdfs}")
print(f"Total Q verified      : {total_paired}")
print(f"Correct (match)       : {sum(1 for r in all_verified if r['match'])}")
print(f"MISMATCHES to fix     : {len(mismatches)}")

with open(RESULTS_OUT, 'w', encoding='utf-8') as f:
    json.dump(all_verified, f, indent=2, ensure_ascii=False)
with open(FIXES_OUT, 'w', encoding='utf-8') as f:
    json.dump(mismatches, f, indent=2, ensure_ascii=False)

print(f"\nResults -> {RESULTS_OUT}")
print(f"Fixes   -> {FIXES_OUT}")

if mismatches:
    lines = [
        '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8',
        '$headers = @{',
        f'    "apikey"        = "{API_KEY}"',
        f'    "Authorization" = "Bearer {API_KEY}"',
        '    "Content-Type"  = "application/json"',
        '    "Prefer"        = "return=minimal"',
        '}',
        '$ok = 0; $err = 0',
        '',
    ]
    for m in mismatches:
        url = f"{SUPABASE_URL}?id=eq.{m['id']}"
        desc = m['q_text'][:60].replace("'", "''").encode('ascii', errors='replace').decode()
        lines.append(f"# stored={m['stored']} pdf={m['pdf_answer']} | {desc}")
        lines.append(f'$body = \'{{"correct_answer":"{m["pdf_answer"]}"}}\' ')
        lines.append('try {')
        lines.append(f'    Invoke-WebRequest -Uri "{url}" -Method PATCH -Headers $headers -Body $body -SkipCertificateCheck -UseBasicParsing | Out-Null')
        lines.append(f'    $ok++; Write-Host "OK  {m["id"][:8]}  {m["stored"]}->{m["pdf_answer"]}"')
        lines.append('} catch {')
        lines.append(f'    $err++; Write-Host "ERR {m["id"][:8]}: $_"')
        lines.append('}')
        lines.append('')
    lines += ['Write-Host ""', 'Write-Host "Done: $ok OK, $err errors"']
    with open(PS1_OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"PS1     -> {PS1_OUT}")
else:
    print("No mismatches found.")
