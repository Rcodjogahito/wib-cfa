#!/usr/bin/env python3
"""Analyze P3 advisory flags at confidence >= 0.65."""
import sys, re, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUMP = r"C:\Users\codjo\AppData\Local\Temp\wib_questions_dump.json"

with open(DUMP, encoding="utf-8-sig") as f:
    questions = json.load(f)

_STOPS = {'the','a','an','and','or','but','is','are','was','were','be','been','being',
'have','has','had','do','does','did','to','of','in','for','on','with','as',
'at','by','from','that','this','which','who','it','its','will','would',
'could','should','may','might','can','not','no','more','than','less','most',
'least','such','also','both','all','any','each','if','when','then','they',
'their','them','there','these','those','we','our','you','your','he','she',
'his','her','what','how','why','about','into','through','after','before',
'between','same','other','however','therefore','because','since','while',
'although','only','typically','generally','usually','often','always','never',
'sometimes','relatively','compared','similar','different','another',
'include','includes','included','using','used','use','known','based'}

def _stem(w):
    for suf in ('ations','ation','tions','tion','ments','ment','ness','ing','ings','ed','ers','er','es','s'):
        if len(w) > len(suf) + 4 and w.endswith(suf):
            return w[:-len(suf)]
    return w

def _tok(t):
    return [_stem(w) for w in re.findall(r'[a-z]+', t.lower()) if w not in _STOPS and len(w) > 3]

def _fuzzy(a, ws):
    if len(a) < 5: return a in ws
    for ew in ws:
        if ew.startswith(a) or a.startswith(ew): return True
        if len(a) >= 6 and len(ew) >= 6 and sum(x==y for x,y in zip(a,ew))/max(len(a),len(ew)) >= 0.85: return True
    return False

def detect(q, oa, ob, oc, expl):
    if not expl or len(expl.strip()) < 15: return None, 0, 0.0
    e = expl.strip()
    opts = {"A": (oa or "").strip(), "B": (ob or "").strip(), "C": (oc or "").strip()}
    for L in ("A","B","C"):
        if re.search(
            rf'\b(correct\s+answer\s+is\s+{L}|answer\s+is\s+{L}|'
            rf'{L}\s+is\s+(the\s+)?(correct|right|best|answer)|'
            rf'(choose|select)\s+{L}\b|(answer|option|choice)\s*:\s*{L}\b|{L}\s+is\s+correct)\b',
            e, re.I):
            return L, 1, 1.0
    fs = (re.split(r'(?<=[.!?])\s+', e) or [""])[0].lower()
    for L in ("A","B","C"):
        oc2 = opts[L].lower().rstrip(".").strip()
        if oc2 and len(oc2) > 8 and oc2 in fs:
            return L, 2, 0.9
    focus = " ".join(re.split(r'(?<=[.!?])\s+', e)[:3])
    es = set(_tok(focus)); er = re.findall(r'[a-z]+', focus.lower())
    scores = {}
    for L in ("A","B","C"):
        ost = list(_tok(opts[L]))
        scores[L] = sum(1 for ow in ost if ow in es or _fuzzy(ow, er)) / len(ost) if ost else 0.0
    mx = max(scores.values())
    if mx >= 0.5:
        winners = [l for l,s in scores.items() if s == mx]
        if len(winners) == 1: return winners[0], 3, mx
        am = {l: sum(1 for ow in _tok(opts[l]) if ow in es or _fuzzy(ow,er)) for l in winners}
        best = max(am, key=am.get)
        if am[best] > min(am.values()): return best, 3, mx
    return None, 0, 0.0

# Collect all P3 flags
all_p3 = []
for row in questions:
    expl = (row.get("explanation_en") or "").strip()
    if len(expl) < 15: continue
    det, pn, conf = detect(
        row.get("question_en",""), row.get("option_a",""),
        row.get("option_b",""), row.get("option_c",""), expl)
    if det is None: continue
    stored = (row.get("correct_answer") or "").strip().upper()
    if det != stored and pn == 3:
        all_p3.append({
            "conf": conf, "id": row["id"], "source": row.get("source",""),
            "stored": stored, "detected": det,
            "question": row.get("question_en",""),
            "option_a": row.get("option_a",""),
            "option_b": row.get("option_b",""),
            "option_c": row.get("option_c",""),
            "explanation": expl,
        })

all_p3.sort(key=lambda x: -x["conf"])

by_src = {}
for item in all_p3:
    by_src.setdefault(item["source"], 0); by_src[item["source"]] += 1

print(f"Total P3 flags: {len(all_p3)}")
print(f"By source: {by_src}")

thresholds = [0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50]
for t in thresholds:
    n = sum(1 for x in all_p3 if x["conf"] >= t)
    print(f"  conf >= {t:.2f}: {n}")

# Print top 40 for manual review
print(f"\n{'='*70}")
print("TOP P3 FLAGS (highest confidence) — MANUAL REVIEW")
print(f"{'='*70}\n")
for i, item in enumerate(all_p3[:40]):
    print(f"[{i+1:3d}] conf={item['conf']:.2f} src={item['source']:12s} stored={item['stored']} -> detected={item['detected']}")
    print(f"       Q: {item['question'][:110]}...")
    print(f"       A. {item['option_a'][:80]}")
    print(f"       B. {item['option_b'][:80]}")
    print(f"       C. {item['option_c'][:80]}")
    print(f"       Expl: {item['explanation'][:200]}...")
    print()

# Save full list for potential apply
out = r"C:\Users\codjo\AppData\Local\Temp\wib_p3_flags.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(all_p3, f, ensure_ascii=False, indent=2)
print(f"\nFull P3 list saved to: {out}")
