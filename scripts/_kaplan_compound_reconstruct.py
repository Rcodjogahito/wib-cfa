# -*- coding: utf-8 -*-
"""For the 239 Kaplan 'compound' diffs (text AND correct_answer both differ
from the resolved PDF question) - re-run the match to fetch the FULL
extracted PDF fields (stem/options/correct_answer/explanation), then verify
via word-bag equality (delig-tolerant) before proposing a patch, exactly the
same discipline used for the Kaplan Ethics field-bleed sweep earlier this
session.
"""
import json, re, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, "scripts")
from _kaplan_pdf_extract_all import extract_pdf_questions
from _kaplan_full_diff import resolve_pdf, sig_words, overlap_score

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_LIG_RE = re.compile(r"ffi|ffl|ff|fi|fl")
_WORD_RE_LOOSE = re.compile(r"[a-z0-9]+")
def sig_words_delig(t):
    return Counter(_LIG_RE.sub("", w) for w in _WORD_RE_LOOSE.findall((t or "").lower()) if len(_LIG_RE.sub("", w)) >= 2)

def main():
    diffs = json.loads(Path("scripts/_kaplan_full_diff_report.json").read_text(encoding="utf-8"))
    live_by_id = {r["id"]: r for r in json.loads(Path("scripts/_kaplan_live_full.json").read_text(encoding="utf-8"))}

    ans = [x for x in diffs if x["status"] == "answer_diff"]
    compound = [x for x in ans if not (x["a_cmp"] in ("exact", "delig_ok")
                                        and x["b_cmp"] in ("exact", "delig_ok")
                                        and x["c_cmp"] in ("exact", "delig_ok"))]
    print(f"{len(compound)} compound candidates")

    pdf_cache = {}
    results = []
    for x in compound:
        row = live_by_id.get(x["id"])
        if not row:
            continue
        pdf_path = resolve_pdf(x["subtopic"])
        if not pdf_path:
            results.append({**x, "recon_status": "no_pdf"})
            continue
        key = str(pdf_path)
        if key not in pdf_cache:
            try:
                pdf_cache[key] = [q for q in extract_pdf_questions(key) if q["status"] == "ok"]
            except Exception as e:
                pdf_cache[key] = []
                print(f"[WARN] {pdf_path}: {e}")
        extracted = pdf_cache[key]

        db_combined = " ".join([row.get("question_en") or "", row.get("option_a") or "",
                                 row.get("option_b") or "", row.get("option_c") or ""])
        qw = sig_words(db_combined)
        best, best_score = None, 0.0
        for e in extracted:
            pw = sig_words(" ".join([e["stem"], e["option_a"], e["option_b"], e["option_c"]]))
            s = overlap_score(qw, pw)
            if s > best_score:
                best_score, best = s, e

        if best is None:
            results.append({**x, "recon_status": "no_match"})
            continue

        recon_combined = " ".join([best["stem"], best["option_a"], best["option_b"], best["option_c"]])
        exact = sig_words(recon_combined) == qw
        delig_ok = (not exact) and (sig_words_delig(recon_combined) == sig_words_delig(db_combined))

        results.append({
            **x,
            "recon_status": "clean" if (exact or delig_ok) else "residual",
            "recon_score": round(best_score, 3),
            "new_question_en": best["stem"], "new_option_a": best["option_a"],
            "new_option_b": best["option_b"], "new_option_c": best["option_c"],
            "new_correct_answer": best["correct_answer"],
        })

    Path("scripts/_kaplan_compound_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter as C
    print("Status:", dict(C(r.get("recon_status") for r in results)))

if __name__ == "__main__":
    main()
