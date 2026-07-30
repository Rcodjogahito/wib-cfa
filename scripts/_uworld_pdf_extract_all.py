# -*- coding: utf-8 -*-
"""Deterministic full-content extractor for UWorld Answer PDFs, mirroring
_kaplan_pdf_extract_all.py's approach: read stem/options/explanation/table
straight from PDF text+layout, and the correct answer from the FontAwesome
checkmark glyph's position (nearest option line by line-center distance,
not a fixed-tolerance overlap -- see the Kaplan Mock Exam false-positive
this avoided)."""
import re, sys
from pathlib import Path
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHECK_GLYPH = "\uf00c"

def extract_pdf_questions(pdf_path):
    doc = fitz.open(pdf_path)
    all_lines = []
    page_tables = []

    for pno in range(len(doc)):
        page = doc[pno]
        try:
            tabs = page.find_tables()
            page_tables.append([t.bbox for t in tabs.tables])
        except Exception:
            page_tables.append([])
        d = page.get_text("dict")
        for block in d["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"])
                has_check = any(CHECK_GLYPH in s["text"] for s in line["spans"])
                stripped = text.strip()
                if not stripped and not has_check:
                    continue
                all_lines.append({"page": pno, "bbox": line["bbox"], "text": stripped, "has_check": has_check})
    doc.close()

    blocks, cur = [], []
    for l in all_lines:
        if re.match(r"^\d+\.\s+\S", l["text"]):
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
            if re.match(rf"^\xa0?{letter}\.$", s) or re.match(rf"^\xa0?{letter}\.\s+\S", s):
                return i
        return None

    def clean_marker(text, letter):
        m = re.match(rf"^\xa0?{letter}\.\s*(.*)$", text.strip())
        return m.group(1) if m else ""

    def join_range(content, start_idx, end_idx, letter):
        lines = [clean_marker(content[start_idx]["text"], letter)] + \
                [l["text"].strip() for l in content[start_idx + 1:end_idx]]
        return " ".join(t for t in lines if t)

    results = []
    for block in blocks:
        content = block
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

        stem = " ".join(l["text"].strip() for l in content[:ia] if l["text"].strip())
        stem = re.sub(r"^\d+\.\s*", "", stem)
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
                t = l["text"].strip()
                if t in ("Things to remember:", "LOS") or t.startswith("Copyright"):
                    break
                expl_lines.append(t)
            explanation = " ".join(t for t in expl_lines if t)

        option_positions = {"A": ia, "B": ib, "C": ic}
        if idd is not None:
            option_positions["D"] = idd
        centers = {}
        for letter, idx in option_positions.items():
            l = content[idx]
            centers[letter] = ((l["bbox"][1] + l["bbox"][3]) / 2, l["page"])

        correct_letter = None
        check_lines = [l for l in content[:iexpl if iexpl is not None else len(content)] if l["has_check"]]
        for chk in check_lines:
            same_page = [L for L in centers if centers[L][1] == chk["page"]]
            if not same_page:
                continue
            chk_center = (chk["bbox"][1] + chk["bbox"][3]) / 2
            nearest = min(same_page, key=lambda L: abs(centers[L][0] - chk_center))
            if abs(centers[nearest][0] - chk_center) <= 20:
                correct_letter = nearest

        end_idx = iexpl if iexpl is not None else len(content)
        has_table = False
        pages_spanned = sorted(set(l["page"] for l in content[:end_idx]))
        for pno in pages_spanned:
            lines_on_page = [l for l in content[:end_idx] if l["page"] == pno]
            if not lines_on_page:
                continue
            ys = [l["bbox"][1] for l in lines_on_page] + [l["bbox"][3] for l in lines_on_page]
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
            "correct_answer": correct_letter,
            "explanation": explanation, "has_table": has_table,
        })
    return results


if __name__ == "__main__":
    import json
    test_pdf = r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\10. Ethics\11.02 Code Of Ethics And Standards Of Professional Conduct - Answers.pdf"
    res = extract_pdf_questions(test_pdf)
    print(f"{len(res)} questions extracted")
    ok = [r for r in res if r["status"] == "ok"]
    fail = [r for r in res if r["status"] != "ok"]
    noans = [r for r in ok if r["correct_answer"] is None]
    print(f"ok={len(ok)} parse_fail={len(fail)} no_answer={len(noans)}")
    print(json.dumps(ok[0], indent=1, ensure_ascii=False))
    if fail:
        print("FIRST FAIL:", fail[0])
