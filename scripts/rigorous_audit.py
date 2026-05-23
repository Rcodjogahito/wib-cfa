#!/usr/bin/env python3
"""
Rigorous answer-consistency audit.
For every question: compare stored correct_answer vs explanation text.
Outputs full detail for ALL cases with a signal (P1, P2, P3).
"""
import sys, re, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUMP = r"C:\Users\codjo\AppData\Local\Temp\wib_dump2.json"

with open(DUMP, encoding="utf-8-sig") as f:
    questions = json.load(f)

print(f"Loaded {len(questions)} questions\n")

# ── NLP engine (identical to data_quality.py) ─────────────────────────────────

_STOPS = {'the','a','an','and','or','but','is','are','was','were','be','been','being',
'have','has','had','do','does','did','to','of','in','for','on','with','as','at','by',
'from','that','this','which','who','it','its','will','would','could','should','may',
'might','can','not','no','more','than','less','most','least','such','also','both','all',
'any','each','if','when','then','they','their','them','there','these','those','we','our',
'you','your','he','she','his','her','what','how','why','about','into','through','after',
'before','between','same','other','however','therefore','because','since','while',
'although','only','typically','generally','usually','often','always','never','sometimes',
'relatively','compared','similar','different','another','include','includes','included',
'using','used','use','known','based'}

def _stem(w):
    for s in ('ations','ation','tions','tion','ments','ment','ness','ing','ings','ed','ers','er','es','s'):
        if len(w) > len(s)+4 and w.endswith(s): return w[:-len(s)]
    return w

def _tok(t):
    return [_stem(w) for w in re.findall(r'[a-z]+',t.lower()) if w not in _STOPS and len(w)>3]

def _fuzzy(a,ws):
    if len(a)<5: return a in ws
    for ew in ws:
        if ew.startswith(a) or a.startswith(ew): return True
        if len(a)>=6 and len(ew)>=6 and sum(x==y for x,y in zip(a,ew))/max(len(a),len(ew))>=0.85: return True
    return False

def detect(q,oa,ob,oc,expl):
    if not expl or len(expl.strip())<15: return None,0,0.0
    e=expl.strip()
    opts={"A":(oa or "").strip(),"B":(ob or "").strip(),"C":(oc or "").strip()}
    # P1
    for L in ("A","B","C"):
        if re.search(rf'\b(correct\s+answer\s+is\s+{L}|answer\s+is\s+{L}|{L}\s+is\s+(the\s+)?(correct|right|best|answer)|(choose|select)\s+{L}\b|(answer|option|choice)\s*:\s*{L}\b|{L}\s+is\s+correct)\b',e,re.I):
            return L,1,1.0
    # P2
    fs=(re.split(r'(?<=[.!?])\s+',e) or [""])[0].lower()
    for L in ("A","B","C"):
        oc2=opts[L].lower().rstrip(".").strip()
        if oc2 and len(oc2)>8 and oc2 in fs: return L,2,0.9
    # P3
    focus=" ".join(re.split(r'(?<=[.!?])\s+',e)[:3])
    es=set(_tok(focus)); er=re.findall(r'[a-z]+',focus.lower())
    scores={}
    for L in ("A","B","C"):
        ost=list(_tok(opts[L]))
        scores[L]=sum(1 for ow in ost if ow in es or _fuzzy(ow,er))/len(ost) if ost else 0.0
    mx=max(scores.values())
    if mx>=0.5:
        winners=[l for l,s in scores.items() if s==mx]
        if len(winners)==1: return winners[0],3,mx
        am={l:sum(1 for ow in _tok(opts[l]) if ow in es or _fuzzy(ow,er)) for l in winners}
        best=max(am,key=am.get)
        if am[best]>min(am.values()): return best,3,mx
    return None,0,0.0

# ── Run audit ─────────────────────────────────────────────────────────────────

p1,p2,p3,ok,nosig=[],[],[],0,0
for row in questions:
    expl=(row.get("explanation_en") or "").strip()
    if len(expl)<15: nosig+=1; continue
    det,pn,conf=detect(row.get("question_en",""),row.get("option_a",""),
                       row.get("option_b",""),row.get("option_c",""),expl)
    if det is None: nosig+=1; continue
    stored=(row.get("correct_answer") or "").strip().upper()
    if det==stored: ok+=1; continue
    item={"id":row["id"],"source":row.get("source",""),"subtopic":row.get("subtopic",""),
          "stored":stored,"detected":det,"conf":conf,"pass":pn,
          "question":row.get("question_en",""),
          "option_a":row.get("option_a",""),"option_b":row.get("option_b",""),
          "option_c":row.get("option_c",""),"explanation":expl}
    if pn==1: p1.append(item)
    elif pn==2: p2.append(item)
    elif pn==3: p3.append(item)

p3.sort(key=lambda x:-x["conf"])

total=len(questions)
print(f"{'='*65}")
print(f"AUDIT RESULTS — {total} questions")
print(f"{'='*65}")
print(f"  P1 explicit-letter (conf=1.0): {len(p1):5d}  ← definitive mismatches")
print(f"  P2 option-text match (conf≥0.9):{len(p2):4d}  ← high-confidence mismatches")
print(f"  P3 overlap advisory:           {len(p3):5d}  (conf 0.5-1.0, see breakdown)")
print(f"  Consistent (OK):               {ok:5d}")
print(f"  No signal (short expl):        {nosig:5d}")
print(f"  Total:                         {total:5d}")

# P3 breakdown by confidence
buckets=[(1.0,1.01),(0.9,1.0),(0.8,0.9),(0.7,0.8),(0.6,0.7),(0.5,0.6)]
print(f"\n  P3 by confidence:")
for lo,hi in buckets:
    n=sum(1 for x in p3 if lo<=x["conf"]<hi)
    print(f"    conf={lo:.1f}-{hi:.2f}: {n}")

# P3 by source
p3_src={}
for x in p3: p3_src.setdefault(x["source"],0); p3_src[x["source"]]+=1
print(f"\n  P3 by source: {p3_src}")

# ── P1 detail (should be 0) ───────────────────────────────────────────────────
if p1:
    print(f"\n{'='*65}")
    print(f"P1 MISMATCHES — {len(p1)} (DEFINITIVE — must fix)")
    print(f"{'='*65}")
    for i,x in enumerate(p1):
        print(f"\n[P1-{i+1}] {x['source']} | stored={x['stored']} → detected={x['detected']}")
        print(f"  Q:  {x['question']}")
        print(f"  A.  {x['option_a']}")
        print(f"  B.  {x['option_b']}")
        print(f"  C.  {x['option_c']}")
        print(f"  Expl: {x['explanation'][:300]}")

# ── P2 detail ────────────────────────────────────────────────────────────────
if p2:
    print(f"\n{'='*65}")
    print(f"P2 MISMATCHES — {len(p2)} (HIGH CONFIDENCE — must fix)")
    print(f"{'='*65}")
    for i,x in enumerate(p2):
        print(f"\n[P2-{i+1}] {x['source']} | stored={x['stored']} → detected={x['detected']}")
        print(f"  Q:  {x['question']}")
        print(f"  A.  {x['option_a']}")
        print(f"  B.  {x['option_b']}")
        print(f"  C.  {x['option_c']}")
        print(f"  Expl: {x['explanation'][:300]}")

# ── P3 full detail conf >= 0.80 ───────────────────────────────────────────────
p3_high=[x for x in p3 if x["conf"]>=0.80]
print(f"\n{'='*65}")
print(f"P3 FLAGS conf≥0.80 — {len(p3_high)} questions (advisory; ~90% false-positive)")
print(f"For each: read explanation to judge if it explicitly disproves stored answer")
print(f"{'='*65}")
for i,x in enumerate(p3_high):
    opt_stored = x[f"option_{x['stored'].lower()}"]
    opt_det    = x[f"option_{x['detected'].lower()}"]
    print(f"\n[P3-{i+1:03d}] conf={x['conf']:.2f} | {x['source']} | stored={x['stored']} ({opt_stored[:60]}) → {x['detected']} ({opt_det[:60]})")
    print(f"  Q:    {x['question'][:150]}")
    print(f"  Expl: {x['explanation'][:250]}")

# Save P1+P2 as JSON for potential patching
out={"p1":p1,"p2":p2,"p3_high":p3_high,"p3_all":p3}
with open(r"C:\Users\codjo\AppData\Local\Temp\wib_audit2.json","w",encoding="utf-8") as f:
    json.dump(out,f,ensure_ascii=False,indent=2)
print(f"\n\nFull results saved to C:\\Users\\codjo\\AppData\\Local\\Temp\\wib_audit2.json")
