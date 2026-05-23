#!/usr/bin/env python3
"""Full view of specific suspected questions for manual verification."""
import sys, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUMP = r"C:\Users\codjo\AppData\Local\Temp\wib_questions_dump.json"
P3   = r"C:\Users\codjo\AppData\Local\Temp\wib_p3_flags.json"

with open(DUMP, encoding="utf-8-sig") as f:
    questions = json.load(f)
with open(P3, encoding="utf-8") as f:
    p3_flags = json.load(f)

q_by_id = {r["id"]: r for r in questions}

# Specific keyword patterns to look up
SUSPECTS = [
    # (partial_q, reason_for_suspicion)
    ("When evaluating mutually exclusive projects, the IRR", "IRR reinvestment assumption"),
    ("semi-strong form of the efficient market hypothesis assumes", "Semi-strong EMH definition"),
    ("semi-strong-form efficient", "Semi-strong EMH implications"),
    ("capital market line are most likely constructed", "CML construction"),
    ("fundamental difference between preference shares", "Preference vs common shares"),
    ("unimodal distribution has a skewness", "Skewness + central tendency"),
    ("Mathew Chambers", "Ethics standard"),
    ("Which of the following best explains why recognition of investment management", "IM profession"),
    ("general and limited partnerships", "Partnership liability"),
    ("greenfield", "Greenfield vs brownfield"),
    ("market portfolio", "Market portfolio nonsystematic"),
    ("PSA", "PSA prepayment 200"),
    ("emotional bias", "Emotional bias response"),
    ("most appropriate action it can take is to", "Central bank money supply"),
]

print("FULL QUESTION DETAILS FOR REVIEW\n")
print("="*70)

for partial, reason in SUSPECTS:
    # Find in p3_flags first
    matched = [item for item in p3_flags if partial.lower() in item["question"].lower()]
    if not matched:
        # Try in all questions
        matched_q = [q for q in questions if partial.lower() in (q.get("question_en") or "").lower()]
        if matched_q:
            q = matched_q[0]
            stored = q.get("correct_answer","").upper()
            print(f"\n[OK - NO P3 FLAG] {reason}")
            print(f"Q: {q.get('question_en','')[:200]}")
            print(f"A. {q.get('option_a','')[:100]}")
            print(f"B. {q.get('option_b','')[:100]}")
            print(f"C. {q.get('option_c','')[:100]}")
            print(f"stored={stored}")
            print(f"Expl: {(q.get('explanation_en') or '')[:400]}")
            print("-"*50)
        continue
    for item in matched[:1]:
        q = q_by_id.get(item["id"], {})
        print(f"\n[P3 FLAG conf={item['conf']:.2f}] {reason} — stored={item['stored']} detected={item['detected']}")
        print(f"Q: {q.get('question_en','')}")
        print(f"A. {q.get('option_a','')}")
        print(f"B. {q.get('option_b','')}")
        print(f"C. {q.get('option_c','')}")
        print(f"Expl: {(q.get('explanation_en') or '')[:500]}")
        print("-"*50)
