#!/usr/bin/env python3
"""
Systematic P3 classification using two independent signals:

Signal 1 — Negation test:
  The explanation contains "incorrect / not correct / wrong / false" in close proximity
  to the STORED answer's option text → stored is explicitly contradicted.

Signal 2 — Affirmation test:
  The explanation contains "correct / right / true / indeed" near the DETECTED answer's
  option text → detected is explicitly supported.

Signal 3 — Logical contradiction test:
  The stored answer's key claim is logically inverted in the explanation
  (e.g., stored says "increases" but explanation says "decreases").

A flag is classified as LIKELY REAL ERROR when it passes Signal 1 OR (Signal 2 AND Signal 3).
All others are LIKELY FALSE POSITIVE.
"""
import sys, re, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open(r"C:\Users\codjo\AppData\Local\Temp\wib_audit2.json", encoding="utf-8") as f:
    audit = json.load(f)

p3_high = audit["p3_high"]  # conf >= 0.80
p3_all  = audit["p3_all"]

def _words(t, n=5):
    return [w.lower() for w in re.findall(r'[a-z]+', t or "") if len(w) > 3]

NEG_WORDS = ['incorrect', 'inaccurate', 'not correct', 'not true', 'not accurate',
             'is wrong', 'are wrong', 'is false', 'are false', 'does not', 'is not',
             'are not', 'will not', 'would not', 'cannot', 'not the case',
             'not appropriate', 'not applicable', 'not a', 'not an',
             'mistaken', 'erroneous']

AFF_WORDS = ['correct', 'accurate', 'true', 'right', 'appropriate', 'indeed',
             'properly', 'correctly', 'is the', 'are the']

def proximity_score(text, opt_text, keywords, window=80):
    """Count how many times keywords appear within `window` chars of opt_text words."""
    text_l = text.lower()
    opt_core = opt_text.lower().strip().rstrip(".")[:40]  # first 40 chars of option
    # Find all positions of the option text
    positions = []
    pos = 0
    while True:
        idx = text_l.find(opt_core[:20], pos)
        if idx == -1: break
        positions.append(idx)
        pos = idx + 1
    if not positions:
        # Try word-by-word
        opt_words = _words(opt_core)[:3]
        for w in opt_words:
            for m in re.finditer(re.escape(w), text_l):
                positions.append(m.start())
    score = 0
    for pos in positions:
        window_text = text_l[max(0, pos-window):pos+window]
        for kw in keywords:
            if kw in window_text:
                score += 1
                break
    return score

def inversion_check(stored_opt, explanation):
    """Check if explanation inverts a key claim in stored option."""
    inversions = [
        (r'\bincreas', r'\bdecreas'), (r'\bdecreas', r'\bincreas'),
        (r'\bhigher\b', r'\blower\b'),  (r'\blower\b', r'\bhigher\b'),
        (r'\bmore\b', r'\bless\b'),     (r'\bless\b', r'\bmore\b'),
        (r'\bpositive\b', r'\bnegative\b'), (r'\bnegative\b', r'\bpositive\b'),
        (r'\bgreater\b', r'\bless(er)?\b'), (r'\bless(er)?\b', r'\bgreater\b'),
        (r'\brise\b', r'\bfall\b'),     (r'\bfall\b', r'\brise\b'),
        (r'\bbefore\b', r'\bafter\b'),  (r'\bafter\b', r'\bbefore\b'),
        (r'\bunlimited\b', r'\blimited\b'), (r'\blimited\b', r'\bunlimited\b'),
        (r'\bactive\b', r'\bpassive\b'), (r'\bpassive\b', r'\bactive\b'),
        (r'\bdirect\b', r'\bindirect\b'), (r'\bindirect\b', r'\bdirect\b'),
        (r'\blinear\b', r'\bnonlinear\b'), (r'\bnonlinear\b', r'\blinear\b'),
        (r'\bsystematic\b', r'\bunsystematic\b'),
        (r'\brealistic\b', r'\bunrealistic\b'),
        (r'\bpublic\b', r'\bprivate\b'), (r'\bprivate\b', r'\bpublic\b'),
        (r'\bweak.form\b', r'\bsemi.strong\b'),
        (r'\bovervalued\b', r'\bundervalued\b'),
        (r'\bovervalued\b', r'\bfairly valued\b'),
        (r'\bundervalued\b', r'\bovervalued\b'),
        (r'\bstronger\b', r'\bweaker\b'), (r'\bweaker\b', r'\bstronger\b'),
    ]
    so = stored_opt.lower()
    el = explanation.lower()[:600]
    for (a_pat, b_pat) in inversions:
        if re.search(a_pat, so) and re.search(b_pat, el):
            return True
    return False

# ── Classify all P3 flags ──────────────────────────────────────────────────────
likely_real   = []
uncertain     = []
likely_false  = []

for x in p3_all:
    stored_opt   = x.get(f"option_{x['stored'].lower()}", "")
    detected_opt = x.get(f"option_{x['detected'].lower()}", "")
    expl = x.get("explanation", "")

    neg_score = proximity_score(expl, stored_opt, NEG_WORDS, window=100)
    aff_score = proximity_score(expl, detected_opt, AFF_WORDS, window=100)
    inv       = inversion_check(stored_opt, expl)

    x["neg_score"] = neg_score
    x["aff_score"] = aff_score
    x["inv"]       = inv

    if neg_score >= 2:
        x["verdict"] = "LIKELY_REAL"
        likely_real.append(x)
    elif neg_score >= 1 and (aff_score >= 1 or inv):
        x["verdict"] = "LIKELY_REAL"
        likely_real.append(x)
    elif inv and aff_score >= 1:
        x["verdict"] = "LIKELY_REAL"
        likely_real.append(x)
    elif neg_score == 1 or (inv and x["conf"] >= 0.85):
        x["verdict"] = "UNCERTAIN"
        uncertain.append(x)
    else:
        x["verdict"] = "LIKELY_FALSE_POSITIVE"
        likely_false.append(x)

likely_real.sort(key=lambda x: -(x["neg_score"] + x["aff_score"] + (1 if x["inv"] else 0) + x["conf"]))
uncertain.sort(key=lambda x: -x["conf"])

print(f"P3 flags total: {len(p3_all)}")
print(f"  LIKELY REAL ERROR:    {len(likely_real)}")
print(f"  UNCERTAIN:            {len(uncertain)}")
print(f"  LIKELY FALSE POSITIVE:{len(likely_false)}")

# ── Print LIKELY REAL with full detail ────────────────────────────────────────
print(f"\n{'='*70}")
print(f"LIKELY REAL ERRORS ({len(likely_real)}) — neg_score + signal analysis")
print(f"{'='*70}")
for i,x in enumerate(likely_real):
    stored_opt   = x.get(f"option_{x['stored'].lower()}", "")
    detected_opt = x.get(f"option_{x['detected'].lower()}", "")
    print(f"\n[R-{i+1:03d}] conf={x['conf']:.2f} neg={x['neg_score']} aff={x['aff_score']} inv={x['inv']} | {x['source']} | {(x.get('subtopic') or '')[:40]}")
    print(f"  stored={x['stored']}: {stored_opt}")
    print(f"  detect={x['detected']}: {detected_opt}")
    print(f"  Q:  {x['question'][:160]}")
    print(f"  Expl: {x['explanation'][:350]}")

# ── Print UNCERTAIN ────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"UNCERTAIN ({len(uncertain)}) — need manual review")
print(f"{'='*70}")
for i,x in enumerate(uncertain[:40]):
    stored_opt = x.get(f"option_{x['stored'].lower()}", "")
    print(f"\n[U-{i+1:03d}] conf={x['conf']:.2f} neg={x['neg_score']} inv={x['inv']} | {x['source']}")
    print(f"  stored={x['stored']}: {stored_opt[:80]}")
    print(f"  Q:  {x['question'][:140]}")
    print(f"  Expl: {x['explanation'][:250]}")

# Save
with open(r"C:\Users\codjo\AppData\Local\Temp\wib_classified.json","w",encoding="utf-8") as f:
    json.dump({"likely_real":likely_real,"uncertain":uncertain,"likely_false":likely_false},f,ensure_ascii=False,indent=2)
print(f"\n\nSaved to wib_classified.json")
