# -*- coding: utf-8 -*-
"""Audit all CFA_WEB questions against existing Vision-OCR caches (QB + Mocks).

v2 fix: the original _cfaweb_audit.py only understood the QB cache format
(list of pages with page_type='questions'/'answers' + items[]). The 12 Mock
cache files use a flatter, already-merged format (list of per-question dicts
with qnum/stem/A/B/C/correct/expl directly, plus some non-question page
markers with only page_type/page_idx) - these were silently read as 0 entries,
which is most of the reason only 160/1122 CFA_WEB questions got audited.
"""
import json, re, difflib
from pathlib import Path
from collections import Counter

WORD_RE = re.compile(r"[a-z0-9]{3,}")
def sig_words(text):
    return Counter(WORD_RE.findall((text or "").lower()))

def load_qb_dir(d):
    entries = []
    for jf in sorted(Path(d).glob("*.json")):
        pages = json.loads(jf.read_text(encoding="utf-8"))
        q_by_n, a_by_n = {}, {}
        for pg in pages:
            if pg.get("page_type") == "questions":
                for item in pg.get("items", []):
                    n = item.get("n")
                    if n is not None:
                        q_by_n[n] = item
            elif pg.get("page_type") == "answers":
                for item in pg.get("items", []):
                    n = item.get("n")
                    if n is not None:
                        a_by_n[n] = item
        for n, qitem in q_by_n.items():
            aitem = a_by_n.get(n, {})
            entries.append({
                "file": jf.name, "n": n,
                "stem": qitem.get("stem", ""),
                "A": qitem.get("A", ""), "B": qitem.get("B", ""), "C": qitem.get("C", ""),
                "correct": aitem.get("correct"), "expl": aitem.get("expl", ""),
                "stem_words": sig_words(qitem.get("stem", "")),
            })
    return entries

def load_mock_dir(d):
    entries = []
    for jf in sorted(Path(d).glob("*.json")):
        items = json.loads(jf.read_text(encoding="utf-8"))
        for item in items:
            if "stem" not in item:
                continue  # non-question page marker
            entries.append({
                "file": jf.name, "n": item.get("qnum"),
                "stem": item.get("stem", ""),
                "A": item.get("A", ""), "B": item.get("B", ""), "C": item.get("C", ""),
                "correct": item.get("correct"), "expl": item.get("expl", ""),
                "stem_words": sig_words(item.get("stem", "")),
            })
    return entries

def _ratio(a, b):
    return difflib.SequenceMatcher(None, (a or "").lower().strip(), (b or "").lower().strip()).ratio()

def best_match(q, cache_entries):
    qw = sig_words(q.get("question_en", ""))
    if not qw or sum(qw.values()) < 4:
        return None, 0.0
    best, best_score = None, 0.0
    for e in cache_entries:
        ew = e["stem_words"]
        if not ew:
            continue
        overlap = sum(min(qw[w], ew.get(w, 0)) for w in qw)
        total = sum(qw.values())
        score = overlap / total if total else 0.0
        if score > best_score:
            best_score, best = score, e
    if best is None:
        return None, 0.0
    opt_ratios = [
        _ratio(q.get("option_a"), best.get("A")),
        _ratio(q.get("option_b"), best.get("B")),
        _ratio(q.get("option_c"), best.get("C")),
    ]
    if min(opt_ratios) < 0.8:
        return None, 0.0
    return best, best_score

def main():
    data = json.loads(Path("scripts/_full_dump_audit.json").read_text(encoding="utf-8"))
    cfaweb = [q for q in data if q.get("source") == "CFA_WEB"]
    print(f"CFA_WEB questions: {len(cfaweb)}")

    all_entries = []
    all_entries.extend(load_qb_dir("scripts/_cache_cfaweb_qb"))
    all_entries.extend(load_mock_dir("scripts/_cache_cfaweb_mocks"))
    print(f"Cache entries loaded: {len(all_entries)}")

    results = []
    for i, q in enumerate(cfaweb):
        match, score = best_match(q, all_entries)
        r = {"id": q["id"], "topic": q.get("topic"), "score": round(score, 3)}
        if match and score >= 0.5:
            r["status"] = "matched"
            r["cache_file"] = match["file"]
            r["cache_n"] = match["n"]
            r["cache_correct"] = match["correct"]
            r["db_correct"] = q.get("correct_answer")
            r["db_stem"] = q.get("question_en")
            r["cache_stem"] = match["stem"]
            r["db_expl"] = q.get("explanation_en")
            r["cache_expl"] = match["expl"]
            r["mismatch"] = (match["correct"] is not None and match["correct"] != q.get("correct_answer"))
        else:
            r["status"] = "no_match"
        results.append(r)
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(cfaweb)}...", end="\r", flush=True)

    print()
    Path("scripts/_cfaweb_audit_v2_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter as C
    print("Status:", dict(C(r["status"] for r in results)))
    matched = [r for r in results if r["status"] == "matched"]
    mismatches = [r for r in matched if r.get("mismatch")]
    print(f"Matched: {len(matched)}, correct_answer mismatches: {len(mismatches)}")
    for m in mismatches[:40]:
        print(" -", m["id"], m["topic"], "db=", m["db_correct"], "cache=", m["cache_correct"], "score=", m["score"])

if __name__ == "__main__":
    main()
