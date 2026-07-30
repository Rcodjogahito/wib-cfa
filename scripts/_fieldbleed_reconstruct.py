# -*- coding: utf-8 -*-
"""Deterministic reconstruction of the Kaplan Ethics field-bleed bug.

The bug (confirmed in session 48 on a 173-item sample): DB's question_en /
option_a / option_b / option_c are built by grouping PDF text lines with each
field's boundary delayed by exactly one line -- field[i] ends up holding
[true_field[i] lines except its first] + [true_field[i+1]'s first line].
This is a pure reassignment of the SAME text (no loss), so it is fully
recoverable by re-parsing the source PDF page's literal "A)"/"B)"/"C)"
markers (which PyMuPDF's plain-text extraction preserves) rather than by
free-text reconstruction.

Approach per candidate:
1. Extract the resolved PDF page's raw text (line-preserving).
2. Split into individual question blocks on that page (a page holds several).
3. Within the matching block (fuzzy-matched against the DB's broken combined
   text), parse stem / A / B / C / explanation using the literal markers.
4. Sanity check: the reconstructed stem+A+B+C word-bag must equal the DB's
   broken combined word-bag (same words, just reshuffled) -- if it does not,
   this candidate isn't a clean shift (e.g. cross-contamination from a
   different question) and is left for manual/agent review instead of a
   blind patch.
5. correct_answer / explanation_en are left untouched (confirmed unaffected
   by this bug in every session-48 example).
"""
import json, re, sys
from pathlib import Path
from collections import Counter
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORD_RE = re.compile(r"[a-z0-9]{3,}")
_LIG_RE = re.compile(r"ffi|ffl|ff|fi|fl")
def _delig(w):
    """Normalize away fl/fi/ff-ligature glyphs pdfplumber silently dropped on
    import (documented session 44 for 'fl'; same mechanism also hits 'fi'/'ff'/
    'ffi'/'ffl', e.g. DB 'conict'==PDF 'conflict', DB 'le'==PDF 'file')."""
    return _LIG_RE.sub("", w)

def sig_words(t):
    return Counter(WORD_RE.findall((t or "").lower()))

_WORD_RE_LOOSE = re.compile(r"[a-z0-9]+")
def sig_words_delig(t):
    # loose (no min-length) tokenization before deligging: a ligature-dropped
    # DB word can itself be very short (e.g. "firm" -> "rm"), which the
    # {3,}-char WORD_RE would otherwise asymmetrically filter out only on
    # the DB side (the PDF side's un-dropped "firm" passes the filter fine,
    # then reduces to "rm" *after* delig) - use the same loose extraction on
    # both sides so the comparison is symmetric.
    return Counter(_delig(w) for w in _WORD_RE_LOOSE.findall((t or "").lower()) if len(_delig(w)) >= 2)

def get_page_lines(pdf_path, page_1indexed):
    doc = fitz.open(pdf_path)
    text = doc[page_1indexed - 1].get_text("text")
    doc.close()
    return [l for l in text.split("\n")]

def split_blocks(lines):
    """Split a page's lines into per-question blocks starting at 'Question #'."""
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
    """Parse one question block into stem/A/B/C/explanation text."""
    text_lines = block_lines[:]
    # drop 'Question #' and 'Question ID:' header lines
    text_lines = [l for l in text_lines
                  if not re.match(r"^Question #\d+ of \d+", l.strip())
                  and not re.match(r"^Question ID:", l.strip())]

    def marker_idx(lines, letter):
        for i, l in enumerate(lines):
            s = l.strip()
            if s == f"{letter})" or re.match(rf"^{letter}\)\s+\S", s):
                return i
        return None

    ia = marker_idx(text_lines, "A")
    ib = marker_idx(text_lines, "B")
    ic = marker_idx(text_lines, "C")
    if ia is None or ib is None or ic is None or not (ia < ib < ic):
        return None

    iexpl = None
    for i in range(ic, len(text_lines)):
        if text_lines[i].strip() == "Explanation":
            iexpl = i
            break

    def clean_marker(line, letter):
        s = line.strip()
        m = re.match(rf"^{letter}\)\s*(.*)$", s)
        return m.group(1) if m else ""

    stem = " ".join(l.strip() for l in text_lines[:ia] if l.strip())
    a_lines = [clean_marker(text_lines[ia], "A")] + [l.strip() for l in text_lines[ia+1:ib]]
    b_lines = [clean_marker(text_lines[ib], "B")] + [l.strip() for l in text_lines[ib+1:ic]]
    c_end = iexpl if iexpl is not None else len(text_lines)
    c_lines = [clean_marker(text_lines[ic], "C")] + [l.strip() for l in text_lines[ic+1:c_end]]

    option_a = " ".join(l for l in a_lines if l)
    option_b = " ".join(l for l in b_lines if l)
    option_c = " ".join(l for l in c_lines if l)
    return {"stem": stem, "option_a": option_a, "option_b": option_b, "option_c": option_c}

def main():
    items = json.loads(Path("scripts/_fieldbleed_items.json").read_text(encoding="utf-8"))
    results = []
    for q in items:
        db_combined = " ".join([q.get("question_en") or "", q.get("option_a") or "",
                                 q.get("option_b") or "", q.get("option_c") or ""])
        db_words = sig_words(db_combined)

        try:
            lines = get_page_lines(q["pdf"], q["page_1indexed"])
        except Exception as e:
            results.append({**q, "recon_status": f"pdf_error:{e}"})
            continue

        blocks = split_blocks(lines)
        best_parsed, best_score = None, 0.0
        for b in blocks:
            parsed = parse_block(b)
            if not parsed:
                continue
            combined = " ".join([parsed["stem"], parsed["option_a"], parsed["option_b"], parsed["option_c"]])
            pw = sig_words(combined)
            total = sum(db_words.values())
            overlap = sum(min(db_words[w], pw.get(w, 0)) for w in db_words)
            score = overlap / total if total else 0.0
            if score > best_score:
                best_score, best_parsed = score, parsed

        if best_parsed is None:
            results.append({**q, "recon_status": "no_block_parsed"})
            continue

        recon_combined = " ".join([best_parsed["stem"], best_parsed["option_a"],
                                    best_parsed["option_b"], best_parsed["option_c"]])
        recon_words = sig_words(recon_combined)
        exact_match = recon_words == db_words
        delig_match = (not exact_match) and (sig_words_delig(recon_combined) == sig_words_delig(db_combined))

        if exact_match:
            status = "clean_shift"
        elif delig_match:
            status = "clean_shift_delig"
        else:
            status = "word_bag_mismatch"
        results.append({
            **q,
            "recon_status": status,
            "recon_score": round(best_score, 3),
            "new_question_en": best_parsed["stem"],
            "new_option_a": best_parsed["option_a"],
            "new_option_b": best_parsed["option_b"],
            "new_option_c": best_parsed["option_c"],
        })

    Path("scripts/_fieldbleed_reconstruct_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter as C
    print("Status:", dict(C(r["recon_status"] for r in results)))

if __name__ == "__main__":
    main()
