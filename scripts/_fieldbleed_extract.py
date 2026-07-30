# -*- coding: utf-8 -*-
"""Render source PDF pages for the Kaplan Ethics field-bleed sweep candidates
(stem lacks terminal punctuation -> signature of the session-48 field-shift bug)."""
import json, re
from pathlib import Path
import fitz  # PyMuPDF

report = json.loads(Path("scripts/_audit_match_report.json").read_text(encoding="utf-8"))
by_id = {r["id"]: r for r in report}
live = json.loads(Path("scripts/_kaplan_ethics_live.json").read_text(encoding="utf-8"))

def ends_dangling(t):
    t = (t or "").strip()
    return bool(t) and not re.search(r'[\.\?\!:\)”’"]$', t)

cands = [r for r in live if ends_dangling(r.get("question_en"))]
print(f"{len(cands)} field-bleed candidates")

out_dir = Path("scripts/_fieldbleed_png")
out_dir.mkdir(exist_ok=True)

items = []
fail = 0
for q in cands:
    qid = q["id"]
    m = by_id.get(qid)
    if not m or not m.get("pdf") or m.get("best_page") is None:
        fail += 1
        continue
    pdf_path = m["pdf"]
    page_idx = m["best_page"]
    png_path = out_dir / f"{qid}.png"
    ok = False
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
        pix.save(str(png_path))
        doc.close()
        ok = True
    except Exception as e:
        print(f"  [FAIL] {qid}: {e}")
        fail += 1
    items.append({
        "id": qid, "pdf": pdf_path, "page_1indexed": page_idx + 1,
        "png": str(png_path) if ok else None,
        "topic": q.get("topic"), "subtopic": q.get("subtopic"),
        "question_en": q.get("question_en"),
        "option_a": q.get("option_a"), "option_b": q.get("option_b"), "option_c": q.get("option_c"),
        "correct_answer": q.get("correct_answer"),
        "explanation_en": q.get("explanation_en"),
    })

Path("scripts/_fieldbleed_items.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Rendered {len(items)-fail}/{len(items)} pages, {fail} failures")
