# -*- coding: utf-8 -*-
"""Retry the 28 field-bleed residuals that failed on their session-47
best_page: search every page of the resolved PDF (not just the single best
page) for the true matching block, in case the original page pick was wrong
(near-duplicate question elsewhere in the same reading)."""
import json, re, sys
from pathlib import Path
from collections import Counter
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORD_RE = re.compile(r"[a-z0-9]{3,}")
_LIG_RE = re.compile(r"ffi|ffl|ff|fi|fl")
_WORD_RE_LOOSE = re.compile(r"[a-z0-9]+")

def _delig(w):
    return _LIG_RE.sub("", w)

def sig_words(t):
    return Counter(WORD_RE.findall((t or "").lower()))

def sig_words_delig(t):
    return Counter(_delig(w) for w in _WORD_RE_LOOSE.findall((t or "").lower()) if len(_delig(w)) >= 2)

def split_blocks(lines):
    blocks, cur = [], []
    for l in lines:
        if re.match(r"^Question #\d+ of \d+", l.strip()):
            if cur:
                blocks.append(cur)
            cur = [l]
        else:
            cur.append(l)
    if cur:
        blocks.append(cur)
    return blocks

def parse_block(block_lines):
    text_lines = [l for l in block_lines
                  if not re.match(r"^Question #\d+ of \d+", l.strip())
                  and not re.match(r"^Question ID:", l.strip())]

    def marker_idx(lines, letter):
        for i, l in enumerate(lines):
            s = l.strip()
            if s == f"{letter})" or re.match(rf"^{letter}\)\s+\S", s):
                return i
        return None

    ia, ib, ic = marker_idx(text_lines, "A"), marker_idx(text_lines, "B"), marker_idx(text_lines, "C")
    if ia is None or ib is None or ic is None or not (ia < ib < ic):
        return None

    iexpl = None
    for i in range(ic, len(text_lines)):
        if text_lines[i].strip() == "Explanation":
            iexpl = i
            break

    def clean_marker(line, letter):
        m = re.match(rf"^{letter}\)\s*(.*)$", line.strip())
        return m.group(1) if m else ""

    stem = " ".join(l.strip() for l in text_lines[:ia] if l.strip())
    a_lines = [clean_marker(text_lines[ia], "A")] + [l.strip() for l in text_lines[ia+1:ib]]
    b_lines = [clean_marker(text_lines[ib], "B")] + [l.strip() for l in text_lines[ib+1:ic]]
    c_end = iexpl if iexpl is not None else len(text_lines)
    c_lines = [clean_marker(text_lines[ic], "C")] + [l.strip() for l in text_lines[ic+1:c_end]]

    return {
        "stem": stem,
        "option_a": " ".join(l for l in a_lines if l),
        "option_b": " ".join(l for l in b_lines if l),
        "option_c": " ".join(l for l in c_lines if l),
    }

def main():
    items = json.loads(Path("scripts/_fieldbleed_reconstruct_report.json").read_text(encoding="utf-8"))
    residuals = [x for x in items if x["recon_status"] == "word_bag_mismatch"]
    print(f"{len(residuals)} residuals to retry across the full PDF")

    results = []
    for q in residuals:
        db_combined = " ".join([q.get("question_en") or "", q.get("option_a") or "",
                                 q.get("option_b") or "", q.get("option_c") or ""])
        db_words = sig_words(db_combined)

        try:
            doc = fitz.open(q["pdf"])
        except Exception as e:
            results.append({**q, "retry_status": f"pdf_error:{e}"})
            continue

        best_parsed, best_score, best_page = None, 0.0, None
        for pidx in range(len(doc)):
            text = doc[pidx].get_text("text")
            for b in split_blocks(text.split("\n")):
                parsed = parse_block(b)
                if not parsed:
                    continue
                combined = " ".join([parsed["stem"], parsed["option_a"], parsed["option_b"], parsed["option_c"]])
                pw = sig_words(combined)
                total = sum(db_words.values())
                overlap = sum(min(db_words[w], pw.get(w, 0)) for w in db_words)
                score = overlap / total if total else 0.0
                if score > best_score:
                    best_score, best_parsed, best_page = score, parsed, pidx + 1
        doc.close()

        if best_parsed is None:
            results.append({**q, "retry_status": "no_block_found", "retry_score": 0.0})
            continue

        recon_combined = " ".join([best_parsed["stem"], best_parsed["option_a"],
                                    best_parsed["option_b"], best_parsed["option_c"]])
        exact = sig_words(recon_combined) == db_words
        delig_ok = (not exact) and (sig_words_delig(recon_combined) == sig_words_delig(db_combined))

        results.append({
            **q,
            "retry_status": "clean_shift" if exact else ("clean_shift_delig" if delig_ok else "still_mismatch"),
            "retry_score": round(best_score, 3),
            "retry_page_1indexed": best_page,
            "retry_question_en": best_parsed["stem"],
            "retry_option_a": best_parsed["option_a"],
            "retry_option_b": best_parsed["option_b"],
            "retry_option_c": best_parsed["option_c"],
        })

    Path("scripts/_fieldbleed_retry_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter as C
    print("Retry status:", dict(C(r["retry_status"] for r in results)))

if __name__ == "__main__":
    main()
