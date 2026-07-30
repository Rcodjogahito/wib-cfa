# -*- coding: utf-8 -*-
"""Exhaustive Kevin_Mock audit: match every live DB Kevin_Mock question
against its deterministically-extracted PDF ground truth and diff."""
import json, re, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, "scripts")
from _kevinmock_pdf_extract_all import extract_questions, extract_answers

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\CLAUDE\Projet CFA\CFA L1\11. KEVIN SIR_s MOCK")
SESSIONS = [
    (ROOT / "SESSION 1 MOCK-Q.pdf", ROOT / "SESSION 1 MOCK-A.pdf"),
    (ROOT / "SESSION 2 MOCK-Q.pdf", ROOT / "SESSION 2 MOCK-A.pdf"),
]

WORD_RE = re.compile(r"[a-z0-9]{3,}")

def sig_words(t):
    return Counter(WORD_RE.findall((t or "").lower()))

def overlap_score(qw, pw):
    total = sum(qw.values())
    if not total:
        return 0.0
    overlap = sum(min(qw[w], pw.get(w, 0)) for w in qw)
    return overlap / total

def main():
    match_report = json.loads(Path("scripts/_audit_match_report.json").read_text(encoding="utf-8"))
    dump_by_id = {d["id"]: d for d in json.loads(Path("scripts/_full_dump_fresh_20260730.json").read_text(encoding="utf-8"))}
    km_rows = [r for r in match_report if r["source"] == "Kevin_Mock"]
    print(f"{len(km_rows)} live Kevin_Mock questions")

    all_extracted = []
    for q_pdf, a_pdf in SESSIONS:
        qs = extract_questions(str(q_pdf))
        ans = extract_answers(str(a_pdf))
        for num in sorted(set(qs) & set(ans)):
            all_extracted.append({**qs[num], **ans[num], "session_pdf": str(q_pdf), "num": num})
    print(f"{len(all_extracted)} extracted question+answer pairs")

    report = []
    for r in km_rows:
        row = dump_by_id.get(r["id"])
        if not row:
            continue
        db_combined = " ".join([row.get("question_en") or "", row.get("option_a") or "",
                                 row.get("option_b") or "", row.get("option_c") or ""])
        qw = sig_words(db_combined)
        best, best_score = None, 0.0
        for e in all_extracted:
            pw = sig_words(" ".join([e["stem"], e["option_a"], e["option_b"], e["option_c"]]))
            s = overlap_score(qw, pw)
            if s > best_score:
                best_score, best = s, e

        if best is None or best_score < 0.5:
            report.append({"id": r["id"], "status": "no_match", "score": round(best_score, 3)})
            continue

        def eq(a, b):
            a, b = (a or "").strip(), (b or "").strip()
            return "exact" if a == b else "diff"

        stem_cmp = eq(row.get("question_en"), best["stem"])
        a_cmp = eq(row.get("option_a"), best["option_a"])
        b_cmp = eq(row.get("option_b"), best["option_b"])
        c_cmp = eq(row.get("option_c"), best["option_c"])
        ans_cmp = "exact" if (row.get("correct_answer") == best["correct_answer"]) else "diff"
        expl_cmp = eq(row.get("explanation_en"), best.get("explanation"))

        any_text_diff = any(c == "diff" for c in (stem_cmp, a_cmp, b_cmp, c_cmp, expl_cmp))
        status = "ok"
        if ans_cmp == "diff":
            status = "answer_diff"
        elif any_text_diff:
            status = "text_diff"

        report.append({
            "id": r["id"], "status": status, "score": round(best_score, 3),
            "stem_cmp": stem_cmp, "a_cmp": a_cmp, "b_cmp": b_cmp, "c_cmp": c_cmp,
            "ans_cmp": ans_cmp, "expl_cmp": expl_cmp,
            "db_correct": row.get("correct_answer"), "pdf_correct": best["correct_answer"],
            "new_question_en": best["stem"], "new_option_a": best["option_a"],
            "new_option_b": best["option_b"], "new_option_c": best["option_c"],
            "new_explanation_en": best.get("explanation"),
        })

    Path("scripts/_kevinmock_full_diff_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Status counts:", dict(Counter(r["status"] for r in report)))

if __name__ == "__main__":
    main()
