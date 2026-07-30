import json
from pathlib import Path
import fitz

PDF_MAP = {
    "AI,_Corporate,_Deriv,_Eco.json": r"D:\CLAUDE\Projet CFA\CFA L1\3. QB CFA WEB PAID-1000 MCQs\AI, Corporate, Deriv, Eco.pdf",
    "Equity,_Ethics.json": r"D:\CLAUDE\Projet CFA\CFA L1\3. QB CFA WEB PAID-1000 MCQs\Equity, Ethics.pdf",
    "Portfolio,_Quants.json": r"D:\CLAUDE\Projet CFA\CFA L1\3. QB CFA WEB PAID-1000 MCQs\Portfolio, Quants.pdf",
    "Fixed_income,_FSA.json": r"D:\CLAUDE\Projet CFA\CFA L1\3. QB CFA WEB PAID-1000 MCQs\Fixed income, FSA.pdf",
}

out_dir = Path("scripts/_cfaweb_other_png")
out_dir.mkdir(exist_ok=True)

manifest = []
for cache_name, pdf_path in PDF_MAP.items():
    cache = json.loads(Path(f"scripts/_cache_cfaweb_qb/{cache_name}").read_text(encoding="utf-8"))
    other_pages = [x["page_idx"] for x in cache if x.get("page_type") == "other"]
    print(cache_name, "other pages:", len(other_pages))
    doc = fitz.open(pdf_path)
    for pidx in other_pages:
        png_path = out_dir / f"{cache_name.replace('.json','')}_p{pidx}.png"
        if not png_path.exists():
            page = doc[pidx]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
            pix.save(str(png_path))
        manifest.append({"cache_name": cache_name, "pdf": pdf_path, "page_idx": pidx, "png": str(png_path)})
    doc.close()

Path("scripts/_cfaweb_other_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print("total other pages across all 4 QB files:", len(manifest))
