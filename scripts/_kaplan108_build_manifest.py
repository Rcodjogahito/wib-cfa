import json
from pathlib import Path
import fitz

match = json.loads(Path("scripts/_audit_match_report.json").read_text(encoding="utf-8"))
match_by_id = {x["id"]: x for x in match}
dump_by_id = {d["id"]: d for d in json.loads(Path("scripts/_full_dump_fresh_20260730.json").read_text(encoding="utf-8"))}

comp = json.loads(Path("scripts/_kaplan_compound_report.json").read_text(encoding="utf-8"))
td = json.loads(Path("scripts/_kaplan_textdiff_report.json").read_text(encoding="utf-8"))
full = json.loads(Path("scripts/_kaplan_full_diff_report.json").read_text(encoding="utf-8"))

comp_res = {x["id"]: "compound_residual" for x in comp if x["recon_status"] == "residual"}
td_res = {x["id"]: "textdiff_residual" for x in td if x["recon_status"] == "residual"}
tf_res = {x["id"]: "table_format_flag" for x in full if x["status"] == "table_format_flag"}

all_reasons = {}
for d in (comp_res, td_res, tf_res):
    for k, v in d.items():
        all_reasons.setdefault(k, []).append(v)

print("total unique:", len(all_reasons))

out_dir = Path("scripts/_kaplan108_png")
out_dir.mkdir(exist_ok=True)

items = []
fail = 0
for qid, reasons in all_reasons.items():
    row = dump_by_id.get(qid)
    m = match_by_id.get(qid)
    if not row or not m:
        fail += 1
        continue
    pdf_path = m["pdf"]
    page_idx = m["best_page"]
    png_path = out_dir / f"{qid}.png"
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
        pix.save(str(png_path))
        doc.close()
    except Exception as e:
        print("FAIL render", qid, e)
        fail += 1
        continue
    items.append({
        "id": qid, "reasons": reasons, "pdf": pdf_path, "page_idx": page_idx,
        "png": str(png_path), "topic": row.get("topic"), "subtopic": row.get("subtopic"),
        "question_en": row.get("question_en"), "option_a": row.get("option_a"),
        "option_b": row.get("option_b"), "option_c": row.get("option_c"),
        "correct_answer": row.get("correct_answer"), "explanation_en": row.get("explanation_en"),
    })

print(f"rendered {len(items)}, failed {fail}")
Path("scripts/_kaplan108_manifest.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
