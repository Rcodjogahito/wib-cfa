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
    """Each QB PDF contains several independent practice-pack sections
    (eg. Alternative Investments, Corporate Issuers, Derivatives, Economics)
    that each restart question numbering at 1 -- a naive single dict keyed
    only by "n" silently collides across sections (last one wins), dropping
    most matches. Segment into sections first: walk pages in page_idx order,
    and start a new section whenever a "questions" page's items restart at
    a number well below the max seen so far in the current section.
    """
    entries = []
    for jf in sorted(Path(d).glob("*.json")):
        pages = sorted(json.loads(jf.read_text(encoding="utf-8")), key=lambda p: p.get("page_idx", 0))
        sections = []  # list of (q_by_n, a_by_n)
        cur_q, cur_a, max_n_seen = {}, {}, 0
        for pg in pages:
            if pg.get("page_type") == "questions":
                ns = [item.get("n") for item in pg.get("items", []) if item.get("n") is not None]
                if ns and cur_q and min(ns) <= max_n_seen - 3:
                    sections.append((cur_q, cur_a))
                    cur_q, cur_a, max_n_seen = {}, {}, 0
                for item in pg.get("items", []):
                    n = item.get("n")
                    if n is not None:
                        cur_q[n] = item
                        max_n_seen = max(max_n_seen, n)
            elif pg.get("page_type") == "answers":
                for item in pg.get("items", []):
                    n = item.get("n")
                    if n is not None:
                        cur_a[n] = item
        if cur_q or cur_a:
            sections.append((cur_q, cur_a))

        for q_by_n, a_by_n in sections:
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
    # Some genuine source stems are very short (eg. "Accrued interest:") and
    # were unmatchable on stem words alone even though the full question+
    # options text is highly distinctive. Score on stem+options combined,
    # falling back gracefully -- this recovers short-stem items without
    # weakening the option-agreement check below.
    qw = sig_words(" ".join([
        q.get("question_en") or "", q.get("option_a") or "",
        q.get("option_b") or "", q.get("option_c") or "",
    ]))
    if not qw or sum(qw.values()) < 3:
        return None, 0.0
    total = sum(qw.values())
    scored = []
    for e in cache_entries:
        ew = sig_words(" ".join([e.get("stem") or "", e.get("A") or "", e.get("B") or "", e.get("C") or ""]))
        if not ew:
            continue
        overlap = sum(min(qw[w], ew.get(w, 0)) for w in qw)
        score = overlap / total if total else 0.0
        if score > 0:
            scored.append((score, e))
    if not scored:
        return None, 0.0
    scored.sort(key=lambda x: -x[0])
    top_score = scored[0][0]

    def opt_ok(e):
        opt_ratios = [
            _ratio(q.get("option_a"), e.get("A")),
            _ratio(q.get("option_b"), e.get("B")),
            _ratio(q.get("option_c"), e.get("C")),
        ]
        return min(opt_ratios) >= 0.8

    # Short/generic stems can tie or nearly-tie across several cache entries
    # (eg. "A limit order is an example of a(n):") -- trying only the single
    # top-scored candidate meant a genuinely correct match could be missed
    # if IT happened to have garbled options while a slightly-lower-scored
    # sibling entry (or even a same-score one later in iteration order) had
    # clean options. Check every candidate within 90% of the top score.
    for score, e in scored:
        if score < top_score * 0.9:
            break
        if opt_ok(e):
            return e, score

    # None of the near-top candidates have clean options. Some cache entries
    # have their 3 options garbled/merged into one field by an imperfect
    # Vision transcription. A near-perfect STEM match (>=0.85) is still
    # strong evidence of the right question even when option-level
    # comparison can't be trusted -- surface it with a low-confidence flag
    # instead of silently discarding an otherwise-correct match.
    if top_score >= 0.85:
        return scored[0][1], -top_score  # negative sentinel = low-confidence stem-only match
    return None, 0.0

def main():
    data = json.loads(Path("scripts/_full_dump_fresh_20260731b.json").read_text(encoding="utf-8"))
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
        if match and score < 0:
            r["status"] = "low_confidence_match"
            r["cache_file"] = match["file"]
            r["cache_n"] = match["n"]
            r["cache_correct"] = match["correct"]
            r["db_correct"] = q.get("correct_answer")
            r["db_stem"] = q.get("question_en")
            r["cache_stem"] = match["stem"]
            r["db_expl"] = q.get("explanation_en")
            r["cache_expl"] = match["expl"]
            r["cache_A"], r["cache_B"], r["cache_C"] = match.get("A"), match.get("B"), match.get("C")
            r["mismatch"] = (match["correct"] is not None and match["correct"] != q.get("correct_answer"))
        elif match and score >= 0.5:
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
