# -*- coding: utf-8 -*-
"""Reconstruct UWorld 'text_diff' candidates (correct_answer already matches,
but stem/option/explanation text differs from the PDF) using the same
word-bag-verified extraction approach proven for Kaplan
(_kaplan_textdiff_reconstruct.py)."""
import json, re, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, "scripts")
from _uworld_pdf_extract_all import extract_pdf_questions
from _uworld_full_diff import sig_words, overlap_score

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_LIG_RE = re.compile(r"ffi|ffl|ff|fi|fl")
_WORD_RE_LOOSE = re.compile(r"[a-z0-9]+")
def sig_words_delig(t):
    return Counter(_LIG_RE.sub("", w) for w in _WORD_RE_LOOSE.findall((t or "").lower()) if len(_LIG_RE.sub("", w)) >= 2)

def main():
    diffs = json.loads(Path("scripts/_uworld_full_diff_report.json").read_text(encoding="utf-8"))
    dump_by_id = {d["id"]: d for d in json.loads(Path("scripts/_full_dump_fresh_20260730.json").read_text(encoding="utf-8"))}

    td = [x for x in diffs if x["status"] == "text_diff"]
    print(f"{len(td)} text_diff candidates")

    pdf_cache = {}
    results = []
    for i, x in enumerate(td):
        row = dump_by_id.get(x["id"])
        if not row:
            continue
        pdf_path = x["pdf"]
        if pdf_path not in pdf_cache:
            try:
                pdf_cache[pdf_path] = [q for q in extract_pdf_questions(pdf_path) if q["status"] == "ok"]
            except Exception as e:
                pdf_cache[pdf_path] = []
                print(f"[WARN] {pdf_path}: {e}")
        extracted = pdf_cache[pdf_path]

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
        qbank_clean = exact or delig_ok

        db_expl = row.get("explanation_en") or ""
        pdf_expl = best.get("explanation") or ""
        expl_exact = db_expl.strip() == pdf_expl.strip()
        expl_delig_ok = (not expl_exact) and (sig_words_delig(pdf_expl) == sig_words_delig(db_expl))
        expl_clean = expl_exact or expl_delig_ok
        expl_changed = bool(pdf_expl) and not expl_clean
        # safety filter proven necessary for Kaplan Mock Exams: reject an
        # explanation replacement that's suspiciously shorter than the
        # original (risk of a scrambled/incomplete PDF-text extraction
        # silently dropping the final computed value)
        expl_len_ok = (not expl_changed) or (len(pdf_expl.split()) >= 0.7 * max(1, len(db_expl.split())))

        results.append({
            **x,
            "recon_status": "clean" if qbank_clean else "residual",
            "recon_score": round(best_score, 3),
            "new_question_en": best["stem"], "new_option_a": best["option_a"],
            "new_option_b": best["option_b"], "new_option_c": best["option_c"],
            "new_correct_answer": best["correct_answer"],
            "new_explanation_en": pdf_expl if pdf_expl else None,
            "expl_changed": expl_changed,
            "expl_len_ok": expl_len_ok,
        })
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(td)}...", flush=True)

    Path("scripts/_uworld_textdiff_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter as C
    print("Status:", dict(C(r.get("recon_status") for r in results)))
    print("expl_changed among clean:", sum(1 for r in results if r.get("recon_status") == "clean" and r.get("expl_changed")))
    print("expl_changed but len filter rejects:", sum(1 for r in results if r.get("recon_status") == "clean" and r.get("expl_changed") and not r.get("expl_len_ok")))

if __name__ == "__main__":
    main()
