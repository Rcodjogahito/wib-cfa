#!/usr/bin/env python3
"""
CFA_WEB NLP audit — full 1122 questions.
Uses DB explanation_en to verify correct_answer with improved P2+negation detection.
Covers the 369 questions not in Vision caches + double-checks all 1122.

Run: python scripts/cfaweb_nlp_audit.py [--dry-run]
"""
import sys, json, re, argparse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUMP_FILE  = r"C:\Users\codjo\AppData\Local\Temp\wib_dump_fresh.json"
OUT_FIXES  = r"C:\Users\codjo\AppData\Local\Temp\cfaweb_nlp_fixes.json"
OUT_PS1    = r"C:\Users\codjo\AppData\Local\Temp\apply_cfaweb_nlp_fixes.ps1"
OUT_REPORT = r"C:\Users\codjo\AppData\Local\Temp\cfaweb_nlp_report.json"

API_KEY    = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ"
    ".epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8"
)
SUPABASE_URL = "https://qlcakqtrambahrofnhho.supabase.co/rest/v1/questions"

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

# ── Text normalization ────────────────────────────────────────────────────────
def _norm(t: str) -> str:
    if not t: return ""
    t = t.lower().strip()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

# ── Negation-aware P1 detection ───────────────────────────────────────────────
# Patterns: "answer is A", "correct answer is B", "A is correct", "B. Correct"
_P1_PATTERNS = [
    r"\bcorrect (?:answer|choice|option|response) is ([abc])\b",
    r"\banswer(?:ed)? is ([abc])\b",
    r"\b([abc]) is (?:the )?correct\b",
    r"\b([abc])\. correct because",
    r"\b([abc]) is (?:the )?best answer\b",
    r"\b([abc]) (?:is most likely|most likely is)\b",
    r"\bselect ([abc])\b",
    r"\bchoose ([abc])\b",
]
def p1_detect(explanation: str) -> str | None:
    if not explanation: return None
    low = explanation.lower()
    for pat in _P1_PATTERNS:
        m = re.search(pat, low)
        if m:
            return m.group(1).upper()
    return None

# ── Negation patterns ─────────────────────────────────────────────────────────
# If explanation says "A is incorrect/wrong" → A is NOT the answer
_NEG_PATTERNS = [
    r"\b([abc]) is (?:not correct|incorrect|wrong|not the correct|not the best)\b",
    r"\b([abc]) is (?:not|never)\b",
    r"\bnot ([abc])\b",
    r"\bincorrect(?:ly)?[,\s]+(?:because )?([abc])\b",
    r"\b([abc])(?:'s| is) (?:a wrong|wrong)\b",
]
def _neg_detected(explanation: str) -> set:
    """Return set of letters that are negatively mentioned (likely wrong answers)."""
    if not explanation: return set()
    low = explanation.lower()
    neg = set()
    for pat in _NEG_PATTERNS:
        for m in re.finditer(pat, low):
            neg.add(m.group(1).upper())
    return neg

# ── Improved P2 with negation guard ──────────────────────────────────────────
def p2_detect(explanation: str, opt_a: str, opt_b: str, opt_c: str) -> str | None:
    """
    Detect which option is supported by explanation.
    Improved over session 40:
    - Uses first 5 sentences (was 1-3)
    - Excludes negatively mentioned letters
    - Scores: 50-char match=3, 30-char match=2, 20-char match=1
    - Returns single winner only if gap > 1 point vs second best
    """
    if not explanation: return None

    sentences = re.split(r'(?<=[.!?])\s+', explanation.strip())
    expl_full = explanation.lower()
    expl_short = " ".join(sentences[:5]).lower()

    neg = _neg_detected(explanation)
    scores: dict[str, int] = {}

    for letter, opt in [("A", opt_a), ("B", opt_b), ("C", opt_c)]:
        if letter in neg:
            continue
        if not opt or len(opt.strip()) < 5:
            continue
        clean = _norm(opt)
        if not clean or len(clean) < 5:
            continue

        key50 = clean[:50].rstrip()
        key30 = clean[:30].rstrip()
        key20 = clean[:20].rstrip()

        score = 0
        # First sentence (strongest signal)
        first = sentences[0].lower() if sentences else ""
        if len(key50) >= 10 and key50 in first:
            score += 4
        elif len(key30) >= 8 and key30 in first:
            score += 3
        elif len(key20) >= 6 and key20 in first:
            score += 2

        # Full short context
        if len(key50) >= 10 and key50 in expl_short:
            score += 2
        elif len(key30) >= 8 and key30 in expl_short:
            score += 1

        # Full explanation (weaker signal)
        if len(key50) >= 10 and key50 in expl_full:
            score += 1

        if score > 0:
            scores[letter] = score

    if not scores:
        return None
    if len(scores) == 1:
        return list(scores.keys())[0]
    # Multiple hits: require clear winner (gap >= 2)
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    best_letter, best_score = sorted_scores[0]
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0
    if best_score - second_score >= 2:
        return best_letter
    return None

# ── Keyword-based explicit signal ────────────────────────────────────────────
def _explicit_signal(explanation: str, opt_a: str, opt_b: str, opt_c: str) -> str | None:
    """
    Look for explicit framing: "A is correct because", "only A", etc.
    Higher confidence than P2.
    """
    if not explanation: return None
    low = explanation.lower()
    for letter, opt in [("A", opt_a), ("B", opt_b), ("C", opt_c)]:
        if not opt: continue
        l = letter.lower()
        # "A is correct", "option A is correct", "A. correct"
        if re.search(rf'\b{l}(?:\)|\b)[^\w]{{0,10}}(?:is )?correct', low):
            return letter
        # "only A" with negation guard
        if re.search(rf'\bonly {l}\b', low) or re.search(rf'\b{l} only\b', low):
            neg = _neg_detected(explanation)
            if letter not in neg:
                return letter
    return None

# ── Main audit ────────────────────────────────────────────────────────────────
print("Loading DB dump...")
with open(DUMP_FILE, encoding="utf-8") as f:
    dump = json.load(f)

cfa_rows = [r for r in dump if r.get("source") == "CFA_WEB"]
print(f"CFA_WEB questions: {len(cfa_rows)}")

fixes   = []
ok      = 0
no_sig  = 0
p1_hits = 0
p2_hits = 0
ex_hits = 0
false_pos_blocked = 0

report  = []

for row in cfa_rows:
    uid       = row["id"]
    stored    = (row.get("correct_answer") or "").upper().strip()
    expl      = row.get("explanation_en") or ""
    opt_a     = row.get("option_a") or ""
    opt_b     = row.get("option_b") or ""
    opt_c     = row.get("option_c") or ""
    q_text    = (row.get("question_en") or "")[:80]

    if stored not in ("A", "B", "C"):
        no_sig += 1
        continue

    # --- P1: explicit letter in explanation
    p1 = p1_detect(expl)
    # --- Explicit signal
    ex = _explicit_signal(expl, opt_a, opt_b, opt_c)
    # --- P2: option text in explanation
    p2 = p2_detect(expl, opt_a, opt_b, opt_c)

    # Determine detected answer (priority: P1 > explicit > P2)
    detected = None
    method   = None
    if p1 and p1 != stored:
        detected, method = p1, "P1"
    elif ex and ex != stored:
        detected, method = ex, "EXPLICIT"
    elif p2 and p2 != stored:
        detected, method = p2, "P2"

    if detected is None:
        # Confirmed correct or no signal
        if p1 == stored or ex == stored or p2 == stored:
            ok += 1
        else:
            no_sig += 1
        report.append({"id": uid, "stored": stored, "signal": p1 or ex or p2 or None, "result": "ok_or_nosig"})
        continue

    # Extra guard: require that the detected answer is positively mentioned
    # and the stored answer is either absent or negatively mentioned
    neg = _neg_detected(expl)
    stored_opt = {"A": opt_a, "B": opt_b, "C": opt_c}[stored]
    detected_opt = {"A": opt_a, "B": opt_b, "C": opt_c}[detected]

    # Reject if explanation also positively mentions stored answer (ambiguous)
    if method == "P2":
        # Verify: detected option text appears in explanation; stored option does NOT appear prominently
        detected_norm = _norm(detected_opt)
        stored_norm   = _norm(stored_opt)
        # If stored option text appears in first 2 sentences → too ambiguous
        first2 = " ".join(re.split(r'(?<=[.!?])\s+', expl.strip())[:2]).lower()
        if len(stored_norm) >= 15 and stored_norm[:30] in first2:
            false_pos_blocked += 1
            report.append({"id": uid, "stored": stored, "signal": detected, "result": "blocked_ambiguous"})
            continue

    if method == "P1":   p1_hits += 1
    elif method == "P2": p2_hits += 1
    else:                ex_hits += 1

    entry = {
        "id":       uid,
        "q_text":  q_text,
        "stored":   stored,
        "detected": detected,
        "method":   method,
        "expl_db":  expl[:200],
    }
    fixes.append(entry)
    report.append({"id": uid, "stored": stored, "signal": detected, "result": "mismatch", "method": method})

print(f"\nResults:")
print(f"  Confirmed correct (P1/P2/EX matches stored): {ok}")
print(f"  No signal (explanation ambiguous/short):     {no_sig}")
print(f"  Blocked as ambiguous:                        {false_pos_blocked}")
print(f"  Genuine mismatches: {len(fixes)}")
print(f"    P1 (explicit letter): {p1_hits}")
print(f"    Explicit framing:     {ex_hits}")
print(f"    P2 (option text):     {p2_hits}")

if fixes:
    print(f"\n=== {len(fixes)} mismatches ===")
    for f in fixes:
        print(f"  {f['id'][:8]}  {f['stored']}->{f['detected']}  [{f['method']}]")
        print(f"    Q: {f['q_text']}")
        print(f"    Expl: {f['expl_db'][:120]}")

with open(OUT_REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
with open(OUT_FIXES, "w", encoding="utf-8") as f:
    json.dump(fixes, f, indent=2, ensure_ascii=False)

if not fixes:
    print("\nNo mismatches — CFA_WEB answers fully consistent with explanations.")
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
    lines.append(f"# [{fix['method']}] {fix['stored']}->{fix['detected']}  {desc}")
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
print(f"\nPS1 -> {OUT_PS1}")
