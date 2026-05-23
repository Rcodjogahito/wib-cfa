#!/usr/bin/env python3
"""
Manual verification of high-confidence P3 flags.
Checks CFA domain logic for each flagged question.
Outputs a list of CONFIRMED corrections.
"""
import sys, re, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUMP = r"C:\Users\codjo\AppData\Local\Temp\wib_questions_dump.json"
P3   = r"C:\Users\codjo\AppData\Local\Temp\wib_p3_flags.json"

with open(DUMP, encoding="utf-8-sig") as f:
    questions = json.load(f)
with open(P3, encoding="utf-8") as f:
    p3_flags = json.load(f)

# Index full data by id
q_by_id = {r["id"]: r for r in questions}

# For each P3 flag, show full Q + options + full explanation
# Then manually label TRUE/FALSE positive based on CFA domain knowledge

# ── Cases I manually identified as REAL ERRORS ──────────────────────────────
# These were verified by reading the full explanation + CFA domain knowledge.
# Each entry: (partial_q_text, correct_answer, reason)
KNOWN_CORRECT = {
    # Q: positively skewed distribution (skewness 0.8), greatest measure of central tendency
    # For right-skewed: mode < median < mean → mean is GREATEST
    # stored=A (mode), should=C (arithmetic mean)
    "skewness of 0.8": "C",
    # Q: EMH semi-strong form, prices fully reflect:
    # Semi-strong = all PUBLICLY available info → stored=A is CORRECT (false positive)

    # Q: preference shares vs common shares, fundamental difference
    # A = "Preference shares carry more voting rights" → FALSE (common has voting rights)
    # C = "Preference shareholders receive dividends before common" → CORRECT
    # stored=A, should=C
    "fundamental difference between preference shares": "C",

    # Q: Mathew Chambers ethics violation
    # Explanation explicitly says "violated Standard V-A" not II-A
    # stored=B (II-A), should=C (V-A)
    "Mathew Chambers": "C",
}

print("Scanning all P3 flags for confirmed real errors...\n")
confirmed_corrections = []
full_print = []

for item in p3_flags:
    q = q_by_id.get(item["id"])
    if not q:
        continue
    qtext = q.get("question_en", "")
    expl  = (q.get("explanation_en") or "").strip()

    # Check if this matches a known error
    for pattern, correct in KNOWN_CORRECT.items():
        if pattern.lower() in qtext.lower():
            entry = {
                "id": item["id"],
                "source": item["source"],
                "stored": item["stored"],
                "correct": correct,
                "question": qtext[:150],
                "option_a": q.get("option_a",""),
                "option_b": q.get("option_b",""),
                "option_c": q.get("option_c",""),
                "explanation_preview": expl[:300],
            }
            confirmed_corrections.append(entry)
            full_print.append(entry)
            break

# Also find cases where explanation EXPLICITLY says stored answer is wrong
# by checking for negation patterns around the stored answer option text
print("Scanning for negation patterns around stored-answer in explanation...\n")
negation_suspects = []
for item in p3_flags:
    q = q_by_id.get(item["id"])
    if not q:
        continue
    stored_letter = item["stored"]
    stored_opt = q.get(f"option_{stored_letter.lower()}", "").strip()
    expl  = (q.get("explanation_en") or "").strip()
    if not stored_opt or len(stored_opt) < 10 or not expl:
        continue

    # Look for the stored option text near negation words in explanation
    opt_words = [w.lower() for w in re.findall(r'[a-z]{4,}', stored_opt.lower())]
    neg_words = ['incorrect', 'not correct', 'wrong', 'false', 'inaccurate', 'does not',
                 'is not', 'are not', 'cannot', 'will not', 'would not']
    expl_lower = expl.lower()

    opt_hit = sum(1 for w in opt_words[:4] if w in expl_lower)
    neg_hit = any(ng in expl_lower for ng in neg_words)

    # Check if stored option words appear right after a negation
    has_neg_near_opt = False
    for opt_w in opt_words[:3]:
        for ng in neg_words:
            pattern = ng + r'.{0,50}' + re.escape(opt_w)
            if re.search(pattern, expl_lower):
                has_neg_near_opt = True
                break

    if has_neg_near_opt and opt_hit >= 2 and item["conf"] >= 0.80:
        negation_suspects.append({
            "id": item["id"],
            "conf": item["conf"],
            "source": item["source"],
            "stored": item["stored"],
            "detected": item["detected"],
            "question": q.get("question_en","")[:120],
            "stored_option": stored_opt[:80],
            "explanation_preview": expl[:250],
        })

print(f"Negation suspects (conf>=0.80): {len(negation_suspects)}")
for i, s in enumerate(negation_suspects[:20]):
    print(f"\n[{i+1}] conf={s['conf']:.2f} src={s['source']} stored={s['stored']} -> {s['detected']}")
    print(f"     Q: {s['question']}...")
    print(f"     Stored option ({s['stored']}): {s['stored_option']}")
    print(f"     Expl: {s['explanation_preview']}...")

print(f"\n\n{'='*70}")
print("CONFIRMED CORRECTIONS (manually verified)")
print(f"{'='*70}")
for c in confirmed_corrections:
    print(f"\n  [{c['source']}] ID: {c['id']}")
    print(f"  Q: {c['question']}...")
    print(f"  A. {c['option_a'][:80]}")
    print(f"  B. {c['option_b'][:80]}")
    print(f"  C. {c['option_c'][:80]}")
    print(f"  stored={c['stored']} -> correct={c['correct']}")
    print(f"  Expl: {c['explanation_preview']}...")

out = r"C:\Users\codjo\AppData\Local\Temp\wib_confirmed_corrections.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(confirmed_corrections, f, ensure_ascii=False, indent=2)
print(f"\n\nConfirmed corrections saved to: {out}")
print(f"Total confirmed: {len(confirmed_corrections)}")
