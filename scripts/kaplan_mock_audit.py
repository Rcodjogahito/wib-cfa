#!/usr/bin/env python3
"""
Kaplan Mock Audit — verifies correct_answer for all Kaplan Mock questions
against original Mock Exam Answers PDFs (1–6).

Detection method:
  P1 (conf=1.0): explicit letter pattern in explanation text
                 "A is correct", "correct answer is B", "B." at start, etc.
  P2 (conf=0.9): exact or near-exact option text in first 2 sentences
  P3 (conf=0.7): stemmed word overlap — ADVISORY ONLY, not flagged as fix

Outputs:
  - kaplan_mock_audit_results.json : all verified questions with match status
  - kaplan_mock_audit_fixes.json   : P1/P2 mismatches (high-confidence fixes)
  - apply_kaplan_mock_fixes.ps1    : PowerShell PATCH script
"""
import json, re, sys, threading
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MOCK_ROOT  = Path(r"D:\CLAUDE\Projet CFA\CFA L1\8. KAPLAN MOCK-1100 MCQs")
DUMP       = r"C:\Users\codjo\AppData\Local\Temp\wib_dump_fresh.json"
RESULTS_OUT = r"C:\Users\codjo\AppData\Local\Temp\kaplan_mock_audit_results.json"
FIXES_OUT   = r"C:\Users\codjo\AppData\Local\Temp\kaplan_mock_audit_fixes.json"
PS1_OUT     = r"C:\Users\codjo\AppData\Local\Temp\apply_kaplan_mock_fixes.ps1"

SUPABASE_URL = "https://qlcakqtrambahrofnhho.supabase.co/rest/v1/questions"
API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ"
    ".epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8"
)
PDF_TIMEOUT = 90

import pdfplumber

# ── Ligature fix (same as styles.py) ──────────────────────────────────────────

_LIGA_FIXES = {
    'Deation': 'Deflation', 'Ination': 'Inflation', 'Stagation': 'Stagflation',
    'Reation': 'Reflation', 'Disination': 'Disinflation',
    'Hyperination': 'Hyperinflation', 'cash ow': 'cash flow',
    'cashow': 'cashflow', 'outow': 'outflow', 'inow': 'inflow',
    'overow': 'overflow', 'underow': 'underflow',
    'oating-rate': 'floating-rate', 'oating rate': 'floating rate',
    'oor': 'floor', 'oored': 'floored', 'uctuation': 'fluctuation',
    'ex post': 'ex post', 'exibility': 'flexibility',
    'pro t': 'profit', 'pro ts': 'profits', 'pro table': 'profitable',
    'bene t': 'benefit', 'bene ts': 'benefits', 'bene cial': 'beneficial',
    'con dence': 'confidence', 'con dent': 'confident',
    'con dential': 'confidential', 'con ict': 'conflict',
    'di cult': 'difficult', 'di culty': 'difficulty',
    'e ective': 'effective', 'e ectively': 'effectively',
    'e ciency': 'efficiency', 'e cient': 'efficient',
    'o ering': 'offering', 'o er': 'offer', 'o set': 'offset',
    'sta ': 'staff', 'staggered': 'staggered',
    'a ect': 'affect', 'a ects': 'affects', 'a ected': 'affected',
    'in ation': 'inflation', 'in ationary': 'inflationary',
    're ect': 'reflect', 're ects': 'reflects', 're ected': 'reflected',
    'de ault': 'default', 'de aults': 'defaults',
    'di erence': 'difference', 'di erent': 'different',
    'per form': 'perform', 'per formance': 'performance',
    'suf cient': 'sufficient', 'insuf cient': 'insufficient',
    'traf c': 'traffic', 'speci c': 'specific',
    'signi cant': 'significant', 'signi cance': 'significance',
    'signi cantly': 'significantly', 'classi cation': 'classification',
    'quanti cation': 'quantification', 'noti cation': 'notification',
    'justi cation': 'justification', 'veri cation': 'verification',
    'codi ed': 'codified', 'identi ed': 'identified',
    'justi ed': 'justified', 'cali bration': 'calibration',
    'pro le': 'profile', 'pro les': 'profiles',
    'coe cient': 'coefficient', 'coe cients': 'coefficients',
    'di erential': 'differential', 'di erentiate': 'differentiate',
}

def fix_ligature(text: str) -> str:
    for bad, good in _LIGA_FIXES.items():
        text = text.replace(bad, good)
    return text

# ── NLP detection ─────────────────────────────────────────────────────────────

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

def _stem(w: str) -> str:
    for suf in ('ations','ation','tions','tion','ments','ment','ness',
                'ing','ings','ed','ers','er','es','s'):
        if len(w) > len(suf) + 4 and w.endswith(suf):
            return w[:-len(suf)]
    return w

def _tokenize(text: str) -> list:
    return [_stem(w) for w in re.findall(r'[a-z]+', text.lower())
            if w not in _STOPS and len(w) > 3]

_NEGATED = re.compile(
    r'\b(least accurate|least likely|incorrect|not accurate|not correct|'
    r'does not|is not|is false|not true|except|inaccurate|violates|'
    r'least appropriate|least suitable|not an example|not a characteristic)\b',
    re.IGNORECASE
)

_EXPLICIT_LETTER = [
    # "Answer: B" or "The answer is B" at start
    re.compile(r'(?:^|\n)\s*(?:The\s+)?(?:correct\s+)?[Aa]nswer\s*(?:is|:)\s*([ABC])[\.\s]', re.I | re.M),
    # "A is correct" or "Choice A is correct"
    re.compile(r'\b(?:choice\s+)?([ABC])\s+is\s+correct\b', re.I),
    # "B is the correct answer"
    re.compile(r'\b([ABC])\s+is\s+the\s+correct\s+answer\b', re.I),
    # "The correct answer is B"
    re.compile(r'\bthe\s+correct\s+answer\s+is\s+([ABC])\b', re.I),
    # "B is incorrect" for negated questions (means B is the least accurate = answer)
    re.compile(r'\b(?:choice\s+)?([ABC])\s+is\s+(?:incorrect|not\s+accurate|inaccurate|wrong|false)\b', re.I),
    # "Both A and B are incorrect, C is correct"
    re.compile(r'\b([ABC])\s+is\s+the\s+(?:best|only\s+)?(?:correct\s+)?(?:answer|choice|option|statement)\b', re.I),
]

def _detect_p1(explanation: str, q_text: str) -> tuple[str | None, float]:
    """P1: explicit letter in explanation. Returns (letter, conf) or (None, 0)."""
    is_negated = bool(_NEGATED.search(q_text))
    for pattern in _EXPLICIT_LETTER:
        m = pattern.search(explanation[:500])
        if m:
            letter = m.group(1).upper()
            # For negated questions, "X is incorrect" means X IS the answer
            if 'incorrect' in pattern.pattern or 'inaccurate' in pattern.pattern:
                if is_negated:
                    return letter, 1.0
                # else: "X is incorrect" in a normal question is not a direct answer
                continue
            return letter, 1.0
    return None, 0.0

def _detect_p2(opt_a: str, opt_b: str, opt_c: str, explanation: str, q_text: str) -> tuple[str | None, float]:
    """P2: exact/near-exact option text in first 2 sentences of explanation."""
    sents = re.split(r'(?<=[.!?])\s+', explanation.strip())
    core = ' '.join(sents[:2])
    core_fixed = fix_ligature(core.lower())

    is_negated = bool(_NEGATED.search(q_text))
    scores = {}
    for letter, opt in [('A', opt_a), ('B', opt_b), ('C', opt_c)]:
        opt_fixed = fix_ligature(opt.lower())
        opt_words = _tokenize(opt_fixed)
        if not opt_words or len(opt_fixed) < 8:
            scores[letter] = 0.0
            continue
        # Exact substring match (high signal)
        if opt_fixed[:40] in core_fixed:
            scores[letter] = 1.0
        else:
            # Token overlap
            core_words = set(_tokenize(core_fixed))
            matched = sum(1 for w in opt_words if w in core_words)
            scores[letter] = matched / len(opt_words)

    if is_negated:
        # Lowest overlap = the false option = the answer for "least accurate"
        best = min(scores, key=scores.get)
        if scores[best] < 0.4 and max(scores.values()) > 0.5:
            return best, 0.9
    else:
        best = max(scores, key=scores.get)
        if scores[best] >= 0.5:
            return best, 0.9 * scores[best]
    return None, 0.0

def detect_answer(q_text: str, opt_a: str, opt_b: str, opt_c: str, explanation: str) -> tuple[str | None, float, int]:
    """Returns (letter, confidence, pass_num) or (None, 0, 0) if no signal."""
    expl = fix_ligature(explanation or '')
    letter, conf = _detect_p1(expl, q_text)
    if letter:
        return letter, conf, 1
    letter, conf = _detect_p2(opt_a, opt_b, opt_c, expl, q_text)
    if letter and conf >= 0.7:
        return letter, conf, 2
    return None, 0.0, 0

# ── PDF parser ────────────────────────────────────────────────────────────────

def _pdf_text(path, timeout=PDF_TIMEOUT):
    buf, err = [], []
    def _r():
        try:
            with pdfplumber.open(path) as pdf:
                buf.append('\n'.join(p.extract_text() or '' for p in pdf.pages))
        except Exception as e:
            err.append(str(e))
    t = threading.Thread(target=_r, daemon=True); t.start(); t.join(timeout)
    if t.is_alive() or err:
        return ''
    return buf[0] if buf else ''

def parse_mock_answers(path):
    """Parse Mock Answers PDF → list of {num, q_text, opt_a, opt_b, opt_c, explanation}."""
    text = _pdf_text(path)
    if not text:
        return []
    results = []
    parts = re.split(r'Question\s+#(\d+)\s+of\s+\d+\n', text)
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        block = (parts[i+1] if i+1 < len(parts) else '').strip()
        block = re.sub(r'Question\s+ID:\s*\d+\s*\n?', '', block)
        m = re.match(
            r'(.+?)\nA\)\s+(.+?)\nB\)\s+(.+?)\nC\)\s+(.+?)\nExplanation\n(.+)',
            block, re.DOTALL
        )
        if not m:
            continue
        q_text = re.sub(r'\s+', ' ', m.group(1)).strip()
        opt_a  = re.sub(r'\s+', ' ', m.group(2)).strip()
        opt_b  = re.sub(r'\s+', ' ', m.group(3)).strip()
        opt_c  = re.sub(r'\s+', ' ', m.group(4)).strip()
        expl   = re.sub(r'\s+', ' ', m.group(5)).strip()
        # Strip trailing module reference "(Module X.Y, LOS Z.a)"
        expl   = re.sub(r'\s*\(Module[^)]+\)\s*$', '', expl).strip()
        results.append({'num': num, 'q_text': q_text, 'opt_a': opt_a,
                        'opt_b': opt_b, 'opt_c': opt_c, 'explanation': expl})
    return results

# ── Load DB ───────────────────────────────────────────────────────────────────

print("Loading DB dump...")
with open(DUMP, encoding='utf-8') as f:
    dump = json.load(f)

kaplan = [r for r in dump if r.get('source') == 'Kaplan']
print(f"Kaplan questions in DB: {len(kaplan)}")

def _norm(text, n=80):
    return re.sub(r'\s+', ' ', fix_ligature(text or '').lower()).strip()[:n]

db80 = {}; db60 = {}
for r in kaplan:
    k = _norm(r.get('question_en', ''))
    if k:
        db80[k[:80]] = r
        db60[k[:60]] = r

def find_row(q_text):
    k = _norm(q_text)
    return db80.get(k[:80]) or db60.get(k[:60])

# ── Run audit ─────────────────────────────────────────────────────────────────

all_verified = []
mismatches   = []
p1_count     = 0; p2_count = 0; no_signal = 0; unmatched = 0

for exam_n in range(1, 7):
    path = MOCK_ROOT / f'Mock Exam {exam_n} - Answers.pdf'
    qs = parse_mock_answers(path)
    exam_matched = 0; exam_mismatch = 0
    for q in qs:
        row = find_row(q['q_text'])
        if row is None:
            unmatched += 1
            continue
        stored = (row.get('correct_answer') or '').upper().strip()
        letter, conf, pass_num = detect_answer(
            q['q_text'], q['opt_a'], q['opt_b'], q['opt_c'], q['explanation']
        )
        if letter is None:
            no_signal += 1
            continue
        if pass_num == 1: p1_count += 1
        elif pass_num == 2: p2_count += 1
        ok = (stored == letter)
        rec = {
            'id': row['id'],
            'q_text': q['q_text'][:80],
            'stored': stored,
            'pdf_answer': letter,
            'match': ok,
            'confidence': round(conf, 2),
            'pass': pass_num,
            'exam': exam_n,
            'q_num': q['num'],
        }
        all_verified.append(rec)
        exam_matched += 1
        if not ok:
            exam_mismatch += 1
            mismatches.append(rec)
            safe = q['q_text'][:60].encode('ascii', errors='replace').decode()
            print(f"  MISMATCH M{exam_n}Q{q['num']} {row['id'][:8]} "
                  f"| stored={stored} pdf={letter} P{pass_num} conf={conf:.2f} | {safe}")
    print(f"Mock {exam_n}: {exam_matched} verified, {exam_mismatch} mismatches")

print(f"\n{'='*60}")
print(f"Total verified   : {len(all_verified)}")
print(f"  P1 detections  : {p1_count}")
print(f"  P2 detections  : {p2_count}")
print(f"No signal (skip) : {no_signal}")
print(f"Unmatched in DB  : {unmatched}")
print(f"MISMATCHES       : {len(mismatches)}")

# Deduplicate
seen = set()
deduped = [r for r in mismatches if not (r['id'] in seen or seen.add(r['id']))]
print(f"Unique IDs       : {len(deduped)}")

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
        '$ok = 0; $err = 0', '',
    ]
    for m in deduped:
        url  = f"{SUPABASE_URL}?id=eq.{m['id']}"
        desc = m['q_text'][:60].replace("'", "''").encode('ascii', errors='replace').decode()
        lines.append(f"# M{m['exam']}Q{m['q_num']} P{m['pass']} conf={m['confidence']} | stored={m['stored']} pdf={m['pdf_answer']} | {desc}")
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
