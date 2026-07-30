# -*- coding: utf-8 -*-
"""Exhaustive UWorld audit: match every live DB UWorld question against its
deterministically-extracted PDF ground truth (_uworld_pdf_extract_all) and
diff stem/options/correct_answer/explanation/table-formatting fidelity.
Mirrors _kaplan_full_diff.py.
"""
import json, re, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, "scripts")
from _uworld_pdf_extract_all import extract_pdf_questions

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORD_RE = re.compile(r"[a-z0-9]{3,}")
_LIG_RE = re.compile(r"ffi|ffl|ff|fi|fl")
_WORD_RE_LOOSE = re.compile(r"[a-z0-9]+")

def sig_words(t):
    return Counter(WORD_RE.findall((t or "").lower()))

def sig_words_delig(t):
    return Counter(_LIG_RE.sub("", w) for w in _WORD_RE_LOOSE.findall((t or "").lower()) if len(_LIG_RE.sub("", w)) >= 2)

def overlap_score(qw, pw):
    total = sum(qw.values())
    if not total:
        return 0.0
    overlap = sum(min(qw[w], pw.get(w, 0)) for w in qw)
    return overlap / total

def main():
    match_report = json.loads(Path("scripts/_audit_match_report.json").read_text(encoding="utf-8"))
    dump = json.loads(Path("scripts/_full_dump_fresh_20260730.json").read_text(encoding="utf-8"))
    dump_by_id = {d["id"]: d for d in dump}

    uworld_rows = [r for r in match_report if r["source"] == "UWorld"]
    print(f"{len(uworld_rows)} live UWorld questions (matched)")

    by_pdf = {}
    for r in uworld_rows:
        by_pdf.setdefault(r["pdf"], []).append(r)

    pdf_cache = {}
    report = []
    n_no_pdf = 0
    for i, (pdf_path, db_rows) in enumerate(by_pdf.items()):
        if pdf_path not in pdf_cache:
            try:
                pdf_cache[pdf_path] = extract_pdf_questions(pdf_path)
            except Exception as e:
                pdf_cache[pdf_path] = []
                print(f"[WARN] extract failed {Path(pdf_path).name}: {e}")
        extracted = [q for q in pdf_cache[pdf_path] if q["status"] == "ok"]
        if not extracted:
            for r in db_rows:
                report.append({"id": r["id"], "pdf": pdf_path, "status": "no_pdf"})
            n_no_pdf += len(db_rows)
            continue

        for r in db_rows:
            row = dump_by_id.get(r["id"])
            if not row:
                continue
            db_combined = " ".join([row.get("question_en") or "", row.get("option_a") or "",
                                     row.get("option_b") or "", row.get("option_c") or ""])
            qw = sig_words(db_combined)
            best, best_score = None, 0.0
            for e in extracted:
                pw = sig_words(" ".join([e["stem"], e["option_a"], e["option_b"], e["option_c"]]))
                s = overlap_score(qw, pw)
                if s > best_score:
                    best_score, best = s, e

            if best is None or best_score < 0.5:
                report.append({"id": r["id"], "pdf": pdf_path, "status": "no_match", "score": round(best_score, 3)})
                continue

            def eq(a, b):
                a, b = (a or "").strip(), (b or "").strip()
                if a == b:
                    return "exact"
                if sig_words_delig(a) == sig_words_delig(b):
                    return "delig_ok"
                return "diff"

            stem_cmp = eq(row.get("question_en"), best["stem"])
            a_cmp = eq(row.get("option_a"), best["option_a"])
            b_cmp = eq(row.get("option_b"), best["option_b"])
            c_cmp = eq(row.get("option_c"), best["option_c"])
            ans_cmp = "exact" if (row.get("correct_answer") == best["correct_answer"]) else "diff"
            ans_missing = best["correct_answer"] is None

            db_expl = row.get("explanation_en") or ""
            pdf_expl = best.get("explanation") or ""
            expl_cmp = eq(db_expl, pdf_expl) if pdf_expl else "pdf_expl_missing"

            table_flag = best.get("has_table") and "|" not in db_combined and "|" not in db_expl

            any_text_diff = any(c == "diff" for c in (stem_cmp, a_cmp, b_cmp, c_cmp, expl_cmp))
            status = "ok"
            if ans_cmp == "diff" and not ans_missing:
                status = "answer_diff"
            elif any_text_diff:
                status = "text_diff"
            elif table_flag:
                status = "table_format_flag"

            report.append({
                "id": r["id"], "pdf": pdf_path, "status": status,
                "score": round(best_score, 3),
                "stem_cmp": stem_cmp, "a_cmp": a_cmp, "b_cmp": b_cmp, "c_cmp": c_cmp,
                "ans_cmp": ans_cmp, "ans_missing_in_pdf": ans_missing, "expl_cmp": expl_cmp,
                "table_flag": bool(table_flag),
                "db_correct": row.get("correct_answer"), "pdf_correct": best["correct_answer"],
            })

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(by_pdf)} pdfs...", flush=True)

    print(f"no_pdf: {n_no_pdf}")
    Path("scripts/_uworld_full_diff_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter as C
    print("Status counts:", dict(C(r["status"] for r in report)))

if __name__ == "__main__":
    main()
