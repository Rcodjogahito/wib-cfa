#!/usr/bin/env python3
"""
Kaplan Ligature Audit — Re-audit the ~796 Kaplan questions
where _detect_v2_kaplan previously returned None due to
fl-ligature broken option texts (len < 8 threshold).

After applying fix_ligature_artifacts() to stored DB options,
re-run NLP on stored explanations and compare to stored answers.
"""
import json, re, sys

DUMP      = r"C:\Users\codjo\AppData\Local\Temp\wib_dump_fresh.json"
RESULTS_OUT = r"C:\Users\codjo\AppData\Local\Temp\kaplan_liga_audit_results.json"
FIXES_OUT   = r"C:\Users\codjo\AppData\Local\Temp\kaplan_liga_fixes.json"
PS1_OUT     = r"C:\Users\codjo\AppData\Local\Temp\apply_kaplan_liga_fixes.ps1"

SUPABASE_URL = "https://qlcakqtrambahrofnhho.supabase.co/rest/v1/questions"
API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ"
    ".epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8"
)

# ── Ligature fix table (from src/styles.py) ────────────────────────────────────
_LIGA_FIXES = {
    'Deation': 'Deflation',       'deation': 'deflation',
    'Ination': 'Inflation',       'ination': 'inflation',
    'Stagation': 'Stagflation',   'stagation': 'stagflation',
    'Reation': 'Reflation',       'reation': 'reflation',
    'Disination': 'Disinflation', 'disination': 'disinflation',
    'Hyperination': 'Hyperinflation', 'hyperination': 'hyperinflation',
    'cash ow': 'cash flow',       'Cash ow': 'Cash flow',
    'cashow': 'cashflow',         'Cashow': 'Cashflow',
    'outow': 'outflow',           'Outow': 'Outflow',
    'inow': 'inflow',             'Inow': 'Inflow',
    'overow': 'overflow',         'Overow': 'Overflow',
    'underow': 'underflow',       'Underow': 'Underflow',
    'workow': 'workflow',         'Workow': 'Workflow',
    'oating-rate': 'floating-rate', 'Oating-rate': 'Floating-rate',
    'oating rate': 'floating rate', 'Oating rate': 'Floating rate',
    'oating exchange': 'floating exchange', 'Oating exchange': 'Floating exchange',
    'oor': 'floor',               'Oor': 'Floor',
    'uctuat': 'fluctuat',         'Uctuat': 'Fluctuat',
    'uctuati': 'fluctuati',
}

def fix_ligature_artifacts(text):
    if not text:
        return text
    for broken, correct in _LIGA_FIXES.items():
        if broken in text:
            text = text.replace(broken, correct)
    return text

# ── NLP helpers (from scripts/audit_fix_options_answers.py) ───────────────────
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
    if not explanation or len(explanation.strip()) < 15:
        return None
    expl = explanation.strip()
    opts = {"A": (opt_a or "").strip(), "B": (opt_b or "").strip(), "C": (opt_c or "").strip()}
    # Pass 1: explicit letter mention
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

# ── Main ───────────────────────────────────────────────────────────────────────
print("Loading dump...")
with open(DUMP, encoding="utf-8") as f:
    dump = json.load(f)

kaplan = [r for r in dump if r.get("source") == "Kaplan"]
print(f"Kaplan questions: {len(kaplan)}")

results   = []
mismatches = []
liga_count = 0

for row in kaplan:
    qid    = row["id"]
    q_text = row.get("question_en") or ""
    opt_a_raw = row.get("option_a") or ""
    opt_b_raw = row.get("option_b") or ""
    opt_c_raw = row.get("option_c") or ""
    expl   = row.get("explanation_en") or ""
    stored = (row.get("correct_answer") or "").upper().strip()

    # Apply ligature fix to stored options
    opt_a_fixed = fix_ligature_artifacts(opt_a_raw)
    opt_b_fixed = fix_ligature_artifacts(opt_b_raw)
    opt_c_fixed = fix_ligature_artifacts(opt_c_raw)

    has_ligature = (opt_a_fixed != opt_a_raw or
                    opt_b_fixed != opt_b_raw or
                    opt_c_fixed != opt_c_raw)
    if has_ligature:
        liga_count += 1

    # Run NLP with FIXED options against stored explanation
    detected = _detect_v2_kaplan(q_text, opt_a_fixed, opt_b_fixed, opt_c_fixed, expl)

    r = {
        "id": qid,
        "q_text": q_text[:80],
        "stored": stored,
        "detected": detected,
        "has_ligature": has_ligature,
        "opt_a_raw": opt_a_raw,   "opt_a_fixed": opt_a_fixed,
        "opt_b_raw": opt_b_raw,   "opt_b_fixed": opt_b_fixed,
        "opt_c_raw": opt_c_raw,   "opt_c_fixed": opt_c_fixed,
        "expl_preview": expl[:120],
        "subtopic": (row.get("subtopic") or "")[:60],
    }
    results.append(r)

    # Flag: ligature artifact present, NLP detected an answer, and it differs from stored
    if has_ligature and detected is not None and detected != stored:
        mismatches.append(r)
        print(f"MISMATCH {qid[:8]} | stored={stored} detected={detected} | {q_text[:60]}")

print(f"\n{'='*60}")
print(f"Total Kaplan          : {len(kaplan)}")
print(f"Has ligature artifacts: {liga_count}")
print(f"NLP detected (total)  : {sum(1 for r in results if r['detected'])}")
print(f"MISMATCHES to fix     : {len(mismatches)}")

with open(RESULTS_OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
with open(FIXES_OUT, "w", encoding="utf-8") as f:
    json.dump(mismatches, f, indent=2, ensure_ascii=False)
print(f"\nResults → {RESULTS_OUT}")
print(f"Fixes   → {FIXES_OUT}")

# Generate PowerShell PS1
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
        url  = f"{SUPABASE_URL}?id=eq.{m['id']}"
        desc = m['q_text'][:60].replace("'", "''")
        lines.append(f"# stored={m['stored']} detected={m['detected']} | {desc}")
        lines.append(f'$body = \'{{"correct_answer":"{m["detected"]}"}}\' ')
        lines.append('try {')
        lines.append(f'    Invoke-WebRequest -Uri "{url}" -Method PATCH -Headers $headers -Body $body -SkipCertificateCheck -UseBasicParsing | Out-Null')
        lines.append(f'    $ok++; Write-Host "OK  {m["id"][:8]}  {m["stored"]}->{m["detected"]}"')
        lines.append('} catch {')
        lines.append(f'    $err++; Write-Host "ERR {m["id"][:8]}: $_"')
        lines.append('}')
        lines.append('')
    lines.append('Write-Host ""')
    lines.append('Write-Host "Done: $ok OK, $err errors"')

    with open(PS1_OUT, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
    print(f"PS1     → {PS1_OUT}")
    print(f"\nTo apply: pwsh -File \"{PS1_OUT}\"")
else:
    print("No mismatches — no PS1 generated.")
