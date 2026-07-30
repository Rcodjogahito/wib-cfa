# -*- coding: utf-8 -*-
"""Exhaustive Kaplan audit: match every live DB Kaplan question (Reading QB +
Mock Exams) against its deterministically-extracted PDF ground truth
(_kaplan_pdf_extract_all.extract_pdf_questions) and diff stem / options /
correct_answer / explanation / table-formatting fidelity.
"""
import json, re, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, "scripts")
from _kaplan_pdf_extract_all import extract_pdf_questions

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KAPLAN_ANS_ROOT = Path(r"D:\CLAUDE\Projet CFA\CFA L1\2. QB KAPLAN-3000 MCQs\QSTN WITH ANS")
KAPLAN_MOCK_ROOT = Path(r"D:\CLAUDE\Projet CFA\CFA L1\8. KAPLAN MOCK-1100 MCQs")

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

_kaplan_reading_map = None
def build_reading_map():
    global _kaplan_reading_map
    if _kaplan_reading_map is not None:
        return _kaplan_reading_map
    mapping = {}
    for pdf in KAPLAN_ANS_ROOT.rglob("*- Answers.pdf"):
        m = re.match(r"(Reading \d+(?:\.\d+)?)", pdf.stem)
        if m:
            mapping[m.group(1)] = pdf
    _kaplan_reading_map = mapping
    return mapping

def resolve_pdf(subtopic):
    if subtopic.startswith("Mock Exam"):
        num = re.search(r"\d+", subtopic)
        if num:
            p = KAPLAN_MOCK_ROOT / f"Mock Exam {num.group()} - Answers.pdf"
            if p.exists():
                return p
        return None
    mapping = build_reading_map()
    m = re.match(r"(Reading \d+(?:\.\d+)?)", subtopic)
    if m and m.group(1) in mapping:
        return mapping[m.group(1)]
    return None

def main():
    rows = json.loads(Path("scripts/_kaplan_live_full.json").read_text(encoding="utf-8"))
    print(f"{len(rows)} live Kaplan questions")

    by_subtopic = {}
    for r in rows:
        by_subtopic.setdefault(r["subtopic"], []).append(r)

    pdf_cache = {}
    report = []
    n_no_pdf = 0
    for i, (subtopic, db_rows) in enumerate(by_subtopic.items()):
        pdf_path = resolve_pdf(subtopic)
        if not pdf_path:
            for r in db_rows:
                report.append({"id": r["id"], "subtopic": subtopic, "status": "no_pdf"})
            n_no_pdf += len(db_rows)
            continue

        key = str(pdf_path)
        if key not in pdf_cache:
            try:
                pdf_cache[key] = extract_pdf_questions(key)
            except Exception as e:
                pdf_cache[key] = []
                print(f"[WARN] extract failed {pdf_path.name}: {e}")
        extracted = [q for q in pdf_cache[key] if q["status"] == "ok"]

        for r in db_rows:
            db_combined = " ".join([r.get("question_en") or "", r.get("option_a") or "",
                                     r.get("option_b") or "", r.get("option_c") or ""])
            qw = sig_words(db_combined)
            best, best_score = None, 0.0
            for e in extracted:
                pw = sig_words(" ".join([e["stem"], e["option_a"], e["option_b"], e["option_c"]]))
                s = overlap_score(qw, pw)
                if s > best_score:
                    best_score, best = s, e

            if best is None or best_score < 0.5:
                report.append({"id": r["id"], "subtopic": subtopic, "status": "no_match", "score": round(best_score, 3)})
                continue

            def eq(a, b):
                a, b = (a or "").strip(), (b or "").strip()
                if a == b:
                    return "exact"
                if sig_words_delig(a) == sig_words_delig(b):
                    return "delig_ok"
                return "diff"

            stem_cmp = eq(r.get("question_en"), best["stem"])
            a_cmp = eq(r.get("option_a"), best["option_a"])
            b_cmp = eq(r.get("option_b"), best["option_b"])
            c_cmp = eq(r.get("option_c"), best["option_c"])
            ans_cmp = "exact" if (r.get("correct_answer") == best["correct_answer"]) else "diff"
            ans_missing = best["correct_answer"] is None

            db_expl = r.get("explanation_en") or ""
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
                "id": r["id"], "subtopic": subtopic, "status": status,
                "score": round(best_score, 3),
                "stem_cmp": stem_cmp, "a_cmp": a_cmp, "b_cmp": b_cmp, "c_cmp": c_cmp,
                "ans_cmp": ans_cmp, "ans_missing_in_pdf": ans_missing, "expl_cmp": expl_cmp,
                "table_flag": bool(table_flag),
                "db_correct": r.get("correct_answer"), "pdf_correct": best["correct_answer"],
            })

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(by_subtopic)} subtopics...", end="\r", flush=True)

    print(f"\nno_pdf: {n_no_pdf}")
    Path("scripts/_kaplan_full_diff_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter as C
    print("Status counts:", dict(C(r["status"] for r in report)))

if __name__ == "__main__":
    main()
