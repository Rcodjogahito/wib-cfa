# -*- coding: utf-8 -*-
"""Deterministic extractor for Kevin Sir's Mock Exam PDFs. Unlike Kaplan/UWorld,
there's no visual checkmark -- the answer key PDF ("...-A.pdf") prints the
correct letter as plain text right after the question number (e.g. "6.  A"),
followed by the explanation prose, until the next "N.  LETTER" line. The
question stems/options live in a SEPARATE PDF ("...-Q.pdf"), keyed by the
same question number, with options as "A. text" / "B. text" / "C. text" lines.
"""
import re, sys
from pathlib import Path
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QSTART_RE = re.compile(r"^(\d+)\.\s+(.*)$")
ANS_START_RE = re.compile(r"^(\d+)\.\s+([A-C])\s*$")


def _lines(pdf_path):
    doc = fitz.open(pdf_path)
    out = []
    for pno in range(len(doc)):
        page = doc[pno]
        d = page.get_text("dict")
        for block in d["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).strip()
                if text:
                    out.append(text)
    doc.close()
    return out


def extract_questions(q_pdf_path):
    lines = _lines(q_pdf_path)
    # drop running header/footer lines
    lines = [l for l in lines if not re.match(r"^\d+\s*\|\s*P\s*a\s*g\s*e", l)
             and "MOCK EXAM" not in l and "SESSION" not in l]

    blocks, cur, cur_num = [], [], None
    for l in lines:
        m = QSTART_RE.match(l)
        if m and (cur_num is None or int(m.group(1)) == cur_num + 1):
            if cur:
                blocks.append((cur_num, cur))
            cur_num = int(m.group(1))
            cur = [m.group(2)]
        else:
            cur.append(l)
    if cur:
        blocks.append((cur_num, cur))

    results = {}
    for num, content in blocks:
        ia = ib = ic = None
        for i, l in enumerate(content):
            if ia is None and re.match(r"^A\.\s+\S", l):
                ia = i
            elif ib is None and re.match(r"^B\.\s+\S", l):
                ib = i
            elif ic is None and re.match(r"^C\.\s+\S", l):
                ic = i
        if ia is None or ib is None or ic is None or not (ia < ib < ic):
            continue
        stem = " ".join(content[:ia]).strip()
        def clean(t, letter):
            return re.sub(rf"^{letter}\.\s*", "", t)
        option_a = " ".join([clean(content[ia], "A")] + content[ia + 1:ib]).strip()
        option_b = " ".join([clean(content[ib], "B")] + content[ib + 1:ic]).strip()
        option_c = " ".join([clean(content[ic], "C")] + content[ic + 1:]).strip()
        results[num] = {"stem": stem, "option_a": option_a, "option_b": option_b, "option_c": option_c}
    return results


def extract_answers(a_pdf_path):
    lines = _lines(a_pdf_path)
    lines = [l for l in lines if not re.match(r"^\d+\s*\|\s*P\s*a\s*g\s*e", l)
             and "MOCK EXAM" not in l and "SESSION" not in l]

    blocks, cur, cur_num, cur_letter = [], [], None, None
    for l in lines:
        m = ANS_START_RE.match(l)
        if m and (cur_num is None or int(m.group(1)) == cur_num + 1):
            if cur_num is not None:
                blocks.append((cur_num, cur_letter, cur))
            cur_num, cur_letter = int(m.group(1)), m.group(2)
            cur = []
        else:
            cur.append(l)
    if cur_num is not None:
        blocks.append((cur_num, cur_letter, cur))

    results = {}
    for num, letter, expl_lines in blocks:
        results[num] = {"correct_answer": letter, "explanation": " ".join(expl_lines).strip()}
    return results


if __name__ == "__main__":
    import json
    q_path = r"D:\CLAUDE\Projet CFA\CFA L1\11. KEVIN SIR_s MOCK\SESSION 1 MOCK-Q.pdf"
    a_path = r"D:\CLAUDE\Projet CFA\CFA L1\11. KEVIN SIR_s MOCK\SESSION 1 MOCK-A.pdf"
    qs = extract_questions(q_path)
    ans = extract_answers(a_path)
    print(f"{len(qs)} questions extracted, {len(ans)} answers extracted")
    missing_q = set(ans) - set(qs)
    missing_a = set(qs) - set(ans)
    print("nums with answer but no question:", sorted(missing_q)[:10])
    print("nums with question but no answer:", sorted(missing_a)[:10])
    print(json.dumps({**qs[6], **ans[6]}, indent=1, ensure_ascii=False))
