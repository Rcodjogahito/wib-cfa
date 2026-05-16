#!/usr/bin/env python3
"""
Render pages containing missing-table questions to PNG for manual table extraction.

Usage: python scripts/render_table_pages.py
Output: scripts/_table_images/{qid}.png  (one per question, zoomed 2.5x)
Also writes: scripts/_table_images/index.json  (qid → {subtopic, question_en, pdf_path, page})
"""

import json
import re
import sys
import tomllib
from pathlib import Path

import fitz  # pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).parent.parent
UWORLD_BASE = Path(r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs")
OUT_DIR = Path(__file__).parent / "_table_images"
OUT_DIR.mkdir(exist_ok=True)

SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"
with open(SECRETS_PATH, "rb") as f:
    _s = tomllib.load(f)
from supabase import create_client
sb = create_client(_s["supabase"]["SUPABASE_URL"], _s["supabase"]["SUPABASE_SERVICE_KEY"])

MISSING_RE = re.compile(
    r"the following\s+[\w\s]{1,40}\s*:\s*"
    r"(?:Based|If|Assuming|Which|The company|The analyst|An analyst|Using|From|According|"
    r"Given|Determine|Calculate|What|Over the|The fund|A fund|The portfolio|An investor|"
    r"The investor|Select|Identify|Choose|Classify)",
    re.IGNORECASE,
)

FOLDER_MAP = {
    "1": "1. Quantitative Methods",
    "2": "2. Economics",
    "3": "3. Portfolio Management",
    "4": "4. Corporate Issuers",
    "5": "5. Financial Statement Analysis",
    "6": "6. Equity Investments",
    "7": "7. Fixed Income",
    "8": "8. Derivatives",
    "9": "9. Alternative Investments",
    "10": "10. Ethics",
}


def subtopic_to_pdf(subtopic: str) -> Path | None:
    m = re.match(r"^(\d+)\.", subtopic)
    if not m:
        return None
    folder_key = m.group(1)
    folder = FOLDER_MAP.get(folder_key)
    if not folder:
        return None
    pdf_name = subtopic + " - Answers.pdf"
    return UWORLD_BASE / folder / pdf_name


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def find_page(pdf: fitz.Document, question_en: str) -> int | None:
    # Use 45-char prefix of the question (before the colon where table is missing)
    m = MISSING_RE.search(question_en)
    if m:
        prefix = question_en[:m.start()].strip()
    else:
        prefix = question_en
    # Use first 50 chars
    search_text = _clean(prefix[:50])
    words = search_text.split()[:8]  # first 8 significant words

    for page_num in range(len(pdf)):
        page = pdf[page_num]
        page_text = _clean(page.get_text())
        matched = sum(1 for w in words if w in page_text)
        if matched >= min(6, len(words)):
            return page_num

    # Fallback: 4-word match
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        page_text = _clean(page.get_text())
        matched = sum(1 for w in words[:4] if w in page_text)
        if matched >= 3:
            return page_num

    return None


def render_page(pdf: fitz.Document, page_num: int, out_path: Path, zoom: float = 2.5):
    page = pdf[page_num]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    pix.save(str(out_path))


def main():
    # Fetch all UWorld questions with missing tables
    data = []
    off = 0
    while True:
        r = sb.table("questions").select(
            "id,topic,subtopic,question_en"
        ).eq("source", "UWorld").range(off, off + 999).execute()
        data.extend(r.data)
        if len(r.data) < 1000:
            break
        off += 1000

    missing = [
        q for q in data
        if MISSING_RE.search(q.get("question_en", "")) and "|" not in q.get("question_en", "")
    ]
    print(f"Questions with missing tables: {len(missing)}")

    index: dict[str, dict] = {}
    rendered = 0
    skipped = 0

    for q in missing:
        qid = q["id"]
        subtopic = q["subtopic"]
        question_en = q["question_en"]

        pdf_path = subtopic_to_pdf(subtopic)
        if not pdf_path or not pdf_path.exists():
            print(f"  SKIP (no PDF): {subtopic}")
            skipped += 1
            continue

        out_img = OUT_DIR / f"{qid}.png"

        try:
            doc = fitz.open(str(pdf_path))
            page_num = find_page(doc, question_en)
            if page_num is None:
                print(f"  SKIP (page not found): {subtopic} | {question_en[:60]}")
                skipped += 1
                doc.close()
                continue

            render_page(doc, page_num, out_img)
            doc.close()

            index[qid] = {
                "subtopic": subtopic,
                "topic": q["topic"],
                "question_en": question_en,
                "pdf_path": str(pdf_path),
                "page": page_num,
                "image": str(out_img),
            }
            rendered += 1
            print(f"  OK  page {page_num+1:3d}: {subtopic} | {question_en[:60]}")

        except Exception as e:
            print(f"  ERROR: {subtopic} — {e}")
            skipped += 1

    # Save index
    idx_path = OUT_DIR / "index.json"
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\nRendered: {rendered} | Skipped: {skipped}")
    print(f"Index: {idx_path}")


if __name__ == "__main__":
    main()
