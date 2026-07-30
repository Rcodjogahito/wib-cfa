# -*- coding: utf-8 -*-
"""Deterministic full-content extractor for Kaplan Answer PDFs (Reading QB +
Mock Exams): for every question block, recover the true stem / options /
correct_answer / explanation directly from the PDF's own text and vector
graphics -- no image reading, no LLM calls.

Key discovery (session 65): the green-check / red-X answer markers are real
vector-drawn rectangles (fitz page.get_drawings()) with a fixed fill color
per status, not just visual decoration -- so which option is "correct" can
be read straight from the PDF structure by matching each marker's y-position
against the nearest colored drawing on the same page.
"""
import re, sys
from pathlib import Path
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GREEN = (0.4863, 0.7255, 0.0)
RED = (0.8392, 0.0314, 0.2314)

def _close(c1, c2, tol=0.08):
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))

def _is_gray(fill):
    return abs(fill[0] - fill[1]) < 0.05 and abs(fill[1] - fill[2]) < 0.05

def extract_pdf_questions(pdf_path):
    doc = fitz.open(pdf_path)
    all_lines = []
    page_drawings = []
    page_tables = []

    for pno in range(len(doc)):
        page = doc[pno]
        drawings = page.get_drawings()
        colored = [d for d in drawings if d.get("fill") and not _is_gray(d["fill"])]
        page_drawings.append(colored)
        try:
            tabs = page.find_tables()
            page_tables.append([t.bbox for t in tabs.tables])
        except Exception:
            page_tables.append([])
        d = page.get_text("dict")
        for block in d["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).strip()
                if not text:
                    continue
                all_lines.append({"page": pno, "bbox": line["bbox"], "text": text})
    doc.close()

    blocks, cur = [], []
    for l in all_lines:
        if re.match(r"^Question #\d+ of \d+$", l["text"].strip()):
            if cur:
                blocks.append(cur)
            cur = [l]
        else:
            cur.append(l)
    if cur:
        blocks.append(cur)

    def marker_idx(content, letter):
        for i, l in enumerate(content):
            s = l["text"].strip()
            if s == f"{letter})" or re.match(rf"^{letter}\)\s+\S", s):
                return i
        return None

    def clean_marker(text, letter):
        m = re.match(rf"^{letter}\)\s*(.*)$", text.strip())
        return m.group(1) if m else ""

    def join_range(content, start_idx, end_idx, letter):
        lines = [clean_marker(content[start_idx]["text"], letter)] + \
                [l["text"].strip() for l in content[start_idx + 1:end_idx]]
        return " ".join(t for t in lines if t)

    results = []
    for block in blocks:
        content = [l for l in block
                   if not re.match(r"^Question #\d+ of \d+$", l["text"])
                   and not re.match(r"^Question ID:", l["text"])]
        if not content:
            continue

        ia, ib, ic = marker_idx(content, "A"), marker_idx(content, "B"), marker_idx(content, "C")
        idd = marker_idx(content, "D")
        if ia is None or ib is None or ic is None or not (ia < ib < ic):
            results.append({"status": "parse_fail", "raw_text": " ".join(l["text"] for l in block)[:200]})
            continue
        opt_end = idd if (idd is not None and idd > ic) else None

        iexpl = None
        search_start = opt_end if opt_end is not None else ic
        for i in range(search_start, len(content)):
            if content[i]["text"].strip() == "Explanation":
                iexpl = i
                break

        stem = " ".join(l["text"].strip() for l in content[:ia])
        option_a = join_range(content, ia, ib, "A")
        option_b = join_range(content, ib, ic, "B")
        c_end = opt_end if opt_end is not None else (iexpl if iexpl is not None else len(content))
        option_c = join_range(content, ic, c_end, "C")
        option_d = None
        if idd is not None:
            d_end = iexpl if iexpl is not None else len(content)
            option_d = join_range(content, idd, d_end, "D")

        explanation = None
        if iexpl is not None:
            expl_lines = []
            for l in content[iexpl + 1:]:
                if re.match(r"^\(Module|^\(Reading|^\(LOS", l["text"].strip()):
                    break
                expl_lines.append(l["text"].strip())
            explanation = " ".join(t for t in expl_lines if t)
            # Mock Exam PDFs sometimes append "(Module X.X, LOS X.y ...)" to
            # the END of the last explanation line instead of putting it on
            # its own line (Reading PDFs always use a separate line) -- strip
            # it wherever it lands so both layouts produce the same text.
            explanation = re.sub(r"\s*\((?:Module|Reading|LOS)[^)]*\)\s*$", "", explanation).strip()

        option_positions = {"A": ia, "B": ib, "C": ic}
        if idd is not None:
            option_positions["D"] = idd
        # nearest-neighbor match (by line-center distance) instead of a fixed
        # y-tolerance overlap check: tight line spacing in some PDFs (esp.
        # Mock Exams, where the checkmark sits right after the option text
        # rather than in a fixed right-margin column) let a tolerance-based
        # overlap match TWO adjacent option lines for the same icon, with
        # whichever letter was checked last silently winning -- found via a
        # confirmed real case (Mock Exam 4, geometric mean question) where a
        # green check on option B was wrongly attributed to option C.
        correct_letter = None
        marker_colors = {}
        centers = {}
        for letter, idx in option_positions.items():
            line = content[idx]
            y0, y1 = line["bbox"][1], line["bbox"][3]
            centers[letter] = ((y0 + y1) / 2, line["page"])
        for letter, idx in option_positions.items():
            line = content[idx]
            pno = line["page"]
            y0, y1 = line["bbox"][1], line["bbox"][3]
            best_d, best_color = None, None
            for d in page_drawings[pno]:
                r = d["rect"]
                icon_center = (r.y0 + r.y1) / 2
                # nearest option-line center to this icon must be THIS letter
                nearest_letter = min(centers, key=lambda L: abs(centers[L][0] - icon_center) if centers[L][1] == pno else 1e9)
                if nearest_letter != letter:
                    continue
                dist = abs(icon_center - (y0 + y1) / 2)
                if dist > 20:
                    continue
                if best_d is None or dist < best_d:
                    best_d = dist
                    if _close(d["fill"], GREEN):
                        best_color = "green"
                    elif _close(d["fill"], RED):
                        best_color = "red"
            if best_color:
                marker_colors[letter] = best_color
                if best_color == "green":
                    correct_letter = letter

        pages_spanned = sorted(set(l["page"] for l in content[:iexpl if iexpl else len(content)]))
        has_table = False
        for pno in pages_spanned:
            block_lines_on_page = [l for l in content if l["page"] == pno]
            if not block_lines_on_page:
                continue
            ys = [l["bbox"][1] for l in block_lines_on_page] + [l["bbox"][3] for l in block_lines_on_page]
            y_min, y_max = min(ys), max(ys)
            for tbbox in page_tables[pno]:
                if tbbox[1] < y_max + 5 and tbbox[3] > y_min - 5:
                    has_table = True
                    break
            if has_table:
                break

        results.append({
            "status": "ok",
            "stem": stem, "option_a": option_a, "option_b": option_b,
            "option_c": option_c, "option_d": option_d,
            "correct_answer": correct_letter, "marker_colors": marker_colors,
            "explanation": explanation, "has_table": has_table,
        })
    return results


if __name__ == "__main__":
    import json
    test_pdf = r"D:\CLAUDE\Projet CFA\CFA L1\2. QB KAPLAN-3000 MCQs\QSTN WITH ANS\Ethical and professional standard\Reading 91.8 Guidance for Standard VI - Answers.pdf"
    res = extract_pdf_questions(test_pdf)
    print(f"{len(res)} questions extracted")
    ok = [r for r in res if r["status"] == "ok"]
    fail = [r for r in res if r["status"] != "ok"]
    print(f"ok={len(ok)} parse_fail={len(fail)}")
    no_answer = [r for r in ok if r["correct_answer"] is None]
    print(f"no correct_answer detected: {len(no_answer)}")
    print(json.dumps(ok[0], indent=1, ensure_ascii=False))
    if fail:
        print("FIRST FAIL:", fail[0])
