# -*- coding: utf-8 -*-
"""Independent corroboration layer for the Kaplan answer_diff candidates
found by _kaplan_full_diff.py: before trusting the PDF icon-color detection
at this scale, cross-check it against the DB's OWN explanation_en (a
completely separate signal, not derived from the same extraction pass) --
same P1/P2-style method used successfully across every prior Kaplan audit
session (44b-44i etc.), applied here as a second opinion rather than a
blind trust in either signal alone.
"""
import json, re, sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORD_RE = re.compile(r"[a-z0-9]{4,}")
STOP = set("""this that with from have been were will would could should
which than into onto upon your their them they these those
about above after again against because before being below between both down
during each further here how much most other over same some such then there
under until where while""".split())

def sig_words(t):
    return Counter(w for w in WORD_RE.findall((t or "").lower()) if w not in STOP)

def option_support_score(explanation, option_text):
    ew = sig_words(explanation)
    ow = sig_words(option_text)
    if not ow or not ew:
        return 0.0
    overlap = sum(min(ow[w], ew.get(w, 0)) for w in ow)
    return overlap / sum(ow.values())

def main():
    diffs = json.loads(Path("scripts/_kaplan_full_diff_report.json").read_text(encoding="utf-8"))
    live_by_id = {r["id"]: r for r in json.loads(Path("scripts/_kaplan_live_full.json").read_text(encoding="utf-8"))}

    ans = [x for x in diffs if x["status"] == "answer_diff"]
    print(f"{len(ans)} answer_diff candidates to corroborate")

    results = []
    for x in ans:
        row = live_by_id.get(x["id"])
        if not row:
            continue
        expl = row.get("explanation_en") or ""
        opts = {"A": row.get("option_a"), "B": row.get("option_b"), "C": row.get("option_c")}
        db_letter, pdf_letter = x["db_correct"], x["pdf_correct"]
        db_score = option_support_score(expl, opts.get(db_letter))
        pdf_score = option_support_score(expl, opts.get(pdf_letter)) if pdf_letter else 0.0

        if pdf_score > db_score + 0.1:
            verdict = "corroborated_pdf"
        elif db_score > pdf_score + 0.1:
            verdict = "corroborated_db"
        else:
            verdict = "ambiguous"

        results.append({
            **x, "db_score": round(db_score, 3), "pdf_score": round(pdf_score, 3), "verdict": verdict,
        })

    Path("scripts/_kaplan_answer_corroborate_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter as C
    print("Verdicts:", dict(C(r["verdict"] for r in results)))

if __name__ == "__main__":
    main()
