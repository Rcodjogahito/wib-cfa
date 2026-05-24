#!/usr/bin/env python3
"""
Direct Answer Audit — extracts correct answers directly from source PDFs
(no NLP inference) for Extra_QB and Kevin_Mock.

Extra_QB  : "N. Answer: A" pattern in answers section
Kevin_Mock: "N. A\n"       pattern in separate MOCK-A PDFs

Kaplan    : no explicit marker → NLP already done, skip
UWorld    : checkmark-based → already audited by uworld_answer_audit_v2.py
CFA_WEB   : scanned images  → not extractable
"""
import json, re, sys, threading
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUMP        = r"C:\Users\codjo\AppData\Local\Temp\wib_dump_fresh.json"
RESULTS_OUT = r"C:\Users\codjo\AppData\Local\Temp\direct_audit_results.json"
FIXES_OUT   = r"C:\Users\codjo\AppData\Local\Temp\direct_audit_fixes.json"
PS1_OUT     = r"C:\Users\codjo\AppData\Local\Temp\apply_direct_fixes.ps1"

EXTRA_QB_PDF = Path(r"D:\CLAUDE\Projet CFA\CFA L1\7. EXTRA QB-700MCQs\EXTRA 700 MCQs.pdf")
KEVIN_ROOT   = Path(r"D:\CLAUDE\Projet CFA\CFA L1\11. KEVIN SIR_s MOCK")

SUPABASE_URL = "https://qlcakqtrambahrofnhho.supabase.co/rest/v1/questions"
API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ"
    ".epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8"
)
PDF_TIMEOUT = 60

import pdfplumber

# ── Helpers ────────────────────────────────────────────────────────────────────

def _pdf_text_pages(path, timeout=PDF_TIMEOUT):
    """Return list of page texts."""
    buf, err = [], []
    def _r():
        try:
            with pdfplumber.open(path) as pdf:
                buf.extend(p.extract_text() or "" for p in pdf.pages)
        except Exception as e:
            err.append(str(e))
    t = threading.Thread(target=_r, daemon=True)
    t.start(); t.join(timeout=timeout)
    if t.is_alive() or err:
        if err: print(f"  [ERROR] {path.name}: {err[0]}")
        else:   print(f"  [TIMEOUT] {path.name}")
        return []
    return buf

def _norm(text, length=80):
    return re.sub(r'\s+', ' ', (text or '').lower()).strip()[:length]

def _stem_from_block(block):
    """Extract question stem (text before first option label A. or A))."""
    m = re.match(r'(.+?)\n\s*A[\.\)]', block, re.DOTALL)
    if m:
        return re.sub(r'\s+', ' ', m.group(1)).strip()
    # Compact: stem ends with ? or : then A. directly
    m = re.match(r'(.+?[?:])\s*A[\.\)]', block, re.DOTALL)
    if m:
        return re.sub(r'\s+', ' ', m.group(1)).strip()
    return None

# ── Load DB ────────────────────────────────────────────────────────────────────

print("Loading dump...")
with open(DUMP, encoding='utf-8') as f:
    dump = json.load(f)

extra_db   = [r for r in dump if r.get('source') == 'Extra_QB']
kevin_db   = [r for r in dump if r.get('source') == 'Kevin_Mock']
print(f"Extra_QB in DB  : {len(extra_db)}")
print(f"Kevin_Mock in DB: {len(kevin_db)}")

def build_lookup(rows):
    """Build {80-char key: row, 60-char key: row} lookup."""
    d80, d60 = {}, {}
    for r in rows:
        k = _norm(r.get('question_en') or '')
        if k:
            d80[k[:80]] = r
            d60[k[:60]] = r
    return d80, d60

extra_d80, extra_d60 = build_lookup(extra_db)
kevin_d80, kevin_d60 = build_lookup(kevin_db)

def find_row(stem, d80, d60):
    k = _norm(stem)
    return d80.get(k[:80]) or d60.get(k[:60])

# ── Parse Extra_QB ─────────────────────────────────────────────────────────────

_TOPIC_HEADER_RE = re.compile(
    r'^([A-Z][A-Z\s&,\-]{5,})$', re.MULTILINE
)
_TOPIC_ALIASES = {
    'ETHICAL AND PROFESSIONAL STANDARDS': 'ETHICS',
    'QUANTITATIVE METHODS': 'QUANT',
    'ECONOMICS': 'ECON',
    'FINANCIAL REPORTING AND ANALYSIS': 'FSA',
    'CORPORATE FINANCE': 'CORP',
    'EQUITY INVESTMENTS': 'EQUITY',
    'DERIVATIVE INVESTMENTS': 'DERIV',
    'DERIVATIVE INVESTMENT': 'DERIV',
    'FIXED INCOME INVESTMENTS': 'FI',
    'ALTERNATIVE INVESTMENTS': 'AI',
    'PORTFOLIO MANAGEMENT': 'PM',
}

def _de_triple(s):
    """Remove triple-encoded chars (e.g. 'AAA' → 'A')."""
    result, i = [], 0
    while i < len(s):
        c = s[i]
        if i + 2 < len(s) and s[i+1] == c and s[i+2] == c and c != ' ':
            result.append(c); i += 3
        else:
            result.append(c); i += 1
    return ''.join(result)

def _canon_topic(raw):
    clean = re.sub(r'\s+', ' ', _de_triple(raw)).strip().upper()
    return _TOPIC_ALIASES.get(clean, clean)

def _split_by_topic(pages_text):
    """
    Given a list of page texts, return dict {topic_key: full_section_text}.
    Topic changes detected by ALL-CAPS header lines.
    Uses line-level attribution and prevents backward topic jumps
    (e.g. page 177 of Extra_QB has 'CORPORATE FINANCE' then 'ECONOMICS' as a
    PDF footer artifact — the second ECON is ignored because ECON already seen).
    """
    current_topic = None
    seen_topics = set()
    sections = {}
    for page_text in pages_text:
        for line in page_text.split('\n'):
            stripped = line.strip()
            if (stripped and stripped == stripped.upper()
                    and len(stripped) > 6
                    and re.match(r'^[A-Z][A-Z\s&,\-]+$', stripped)):
                cand = _canon_topic(stripped)
                if cand in _TOPIC_ALIASES.values() and cand not in seen_topics:
                    current_topic = cand
                    seen_topics.add(cand)
                    continue
            if current_topic:
                sections.setdefault(current_topic, []).append(line)
    return {k: '\n'.join(v) for k, v in sections.items()}

def parse_extra_qb():
    """
    Returns list of {'stem': str, 'answer': str} for all Extra_QB questions.
    Handles per-topic numbering restart by matching (topic, num) pairs.
    """
    print("\n--- Extra_QB ---")
    pages = _pdf_text_pages(EXTRA_QB_PDF)
    if not pages:
        return []

    # Find the page where the answer section starts (first page with "1. Answer: X")
    ans_start_idx = None
    for idx, pg in enumerate(pages):
        if re.search(r'(?m)^1\.\s+Answer:\s+[ABC]', pg):
            ans_start_idx = idx
            break
    if ans_start_idx is None:
        print("  Could not find answer section page")
        return []

    q_pages_list = pages[:ans_start_idx]
    a_pages_list = pages[ans_start_idx:]

    # Split both sections by topic
    q_sections = _split_by_topic(q_pages_list)
    a_sections = _split_by_topic(a_pages_list)

    print(f"  Q topics: {sorted(q_sections)}")
    print(f"  A topics: {sorted(a_sections)}")

    results = []
    for topic in sorted(set(q_sections) & set(a_sections)):
        q_text = q_sections[topic]
        a_text = a_sections[topic]

        # Parse stems: "N. stem ... A. opt B. opt C. opt"
        q_blocks = re.split(r'\n(?=\d+\.[ \t])', q_text)
        stems = {}
        for block in q_blocks:
            m = re.match(r'^(\d+)\.\s+(.+)', block, re.DOTALL)
            if not m:
                continue
            num = int(m.group(1))
            stem = _stem_from_block(m.group(2).strip())
            if stem and len(stem) > 15:
                stems[num] = stem

        # Parse answers: "N. Answer: A" — apply de-triple first (CORP/AI sections
        # in Extra_QB use triple-encoded text: "111... AAAnnnssswwweeerrr::: CCC")
        a_text_decoded = _de_triple(a_text)
        answers = {}
        for m in re.finditer(r'(\d+)\.\s+Answer:\s+([ABC])', a_text_decoded):
            answers[int(m.group(1))] = m.group(2)

        paired = 0
        for num in sorted(set(stems) & set(answers)):
            results.append({'stem': stems[num], 'answer': answers[num], 'topic': topic, 'q_num': num})
            paired += 1
        print(f"  [{topic}] Q={len(stems)} A={len(answers)} paired={paired}")

    print(f"  Total paired: {len(results)}")
    return results

# ── Parse Kevin_Mock ───────────────────────────────────────────────────────────

def parse_kevin_session(q_path, a_path, label):
    """
    Parse one Kevin Mock session.
    Questions: "N. stem\nA. ...\nB. ...\nC. ..."
    Answers  : "N. A\nExplanation..."
    Returns {q_num: {'stem': str, 'answer': str}}
    """
    q_pages = _pdf_text_pages(q_path)
    a_pages = _pdf_text_pages(a_path)
    if not q_pages or not a_pages:
        return {}

    q_full = "\n".join(q_pages)
    a_full = "\n".join(a_pages)

    # Parse questions
    q_blocks = re.split(r'\n(?=\d+\.[ \t])', q_full)
    stems = {}
    for block in q_blocks:
        m = re.match(r'^(\d+)\.\s+(.+)', block, re.DOTALL)
        if not m:
            continue
        num = int(m.group(1))
        stem = _stem_from_block(m.group(2).strip())
        if stem and len(stem) > 15:
            stems[num] = stem

    # Parse answers: line starting with "N. A" or "N. B" or "N. C"
    answers = {}
    for m in re.finditer(r'(?m)^(\d+)\.\s+([ABC])\s*\n', a_full):
        answers[int(m.group(1))] = m.group(2)

    print(f"  {label}: Q={len(stems)}, A={len(answers)}, paired={len(set(stems)&set(answers))}")

    result = {}
    for num in sorted(set(stems) & set(answers)):
        result[num] = {'stem': stems[num], 'answer': answers[num]}
    return result

# ── Run audits ─────────────────────────────────────────────────────────────────

all_verified = []
mismatches   = []

def audit_source(pairs_list, d80, d60, source_label):
    """pairs_list: list of dicts with keys stem, answer, q_num (+ optional topic)."""
    matched = unmatched = 0
    for qa in pairs_list:
        stem   = qa['stem']
        letter = qa['answer']
        num    = qa.get('q_num', '?')
        row = find_row(stem, d80, d60)
        if row is None:
            unmatched += 1
            continue
        matched += 1
        stored = (row.get('correct_answer') or '').upper().strip()
        ok = (stored == letter)
        rec = {
            'id': row['id'],
            'q_text': stem[:80],
            'stored': stored,
            'pdf_answer': letter,
            'match': ok,
            'source': source_label,
            'q_num': num,
            'topic': qa.get('topic', ''),
        }
        all_verified.append(rec)
        if not ok:
            mismatches.append(rec)
            safe = stem[:60].encode('ascii', errors='replace').decode()
            print(f"    MISMATCH #{num} {row['id'][:8]} | stored={stored} pdf={letter} | {safe}")
    print(f"  matched={matched}, unmatched={unmatched}, mismatches so far={len(mismatches)}")

# Extra_QB
extra_pairs = parse_extra_qb()
print(f"\nAuditing Extra_QB ({len(extra_pairs)} pairs)...")
audit_source(extra_pairs, extra_d80, extra_d60, 'Extra_QB')

# Kevin_Mock — convert to list format
print("\n--- Kevin_Mock ---")
kevin_pairs_list = []
for sess, q_name, a_name in [
    (1, 'SESSION 1 MOCK-Q.pdf', 'SESSION 1 MOCK-A.pdf'),
    (2, 'SESSION 2 MOCK-Q.pdf', 'SESSION 2 MOCK-A.pdf'),
]:
    p = parse_kevin_session(
        KEVIN_ROOT / q_name,
        KEVIN_ROOT / a_name,
        f"S{sess}"
    )
    for num, qa in p.items():
        kevin_pairs_list.append({'stem': qa['stem'], 'answer': qa['answer'],
                                  'q_num': f"S{sess}Q{num}", 'topic': f"Session{sess}"})

print(f"\nAuditing Kevin_Mock ({len(kevin_pairs_list)} pairs)...")
audit_source(kevin_pairs_list, kevin_d80, kevin_d60, 'Kevin_Mock')

# ── Summary ────────────────────────────────────────────────────────────────────

print(f"\n{'='*60}")
print(f"Total Q verified  : {len(all_verified)}")
print(f"Correct (match)   : {sum(1 for r in all_verified if r['match'])}")
print(f"MISMATCHES to fix : {len(mismatches)}")

# Deduplicate by id
seen = set()
deduped = []
for r in mismatches:
    if r['id'] not in seen:
        seen.add(r['id'])
        deduped.append(r)
print(f"Unique IDs to fix : {len(deduped)}")

with open(RESULTS_OUT, 'w', encoding='utf-8') as f:
    json.dump(all_verified, f, indent=2, ensure_ascii=False)
with open(FIXES_OUT, 'w', encoding='utf-8') as f:
    json.dump(deduped, f, indent=2, ensure_ascii=False)

print(f"\nResults -> {RESULTS_OUT}")
print(f"Fixes   -> {FIXES_OUT}")

# ── Generate PS1 ──────────────────────────────────────────────────────────────

if deduped:
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
    for m in deduped:
        url  = f"{SUPABASE_URL}?id=eq.{m['id']}"
        desc = m['q_text'][:60].replace("'", "''").encode('ascii', errors='replace').decode()
        lines.append(f"# {m['source']} Q{m['q_num']} | stored={m['stored']} pdf={m['pdf_answer']} | {desc}")
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
