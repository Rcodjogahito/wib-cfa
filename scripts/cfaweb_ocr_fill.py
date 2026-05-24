#!/usr/bin/env python3
"""
Fill empty CFA_WEB Vision cache files using free Windows OCR (winsdk).
No Anthropic API calls needed — 100% local, no cost beyond OS.

Prerequisites:
    pip install winsdk

Usage: python scripts/cfaweb_ocr_fill.py

Re-run whenever cache files are empty or need refresh.
Cache files are in _cache_cfaweb_qb/ and _cache_cfaweb_mocks/ (gitignored).
"""
import asyncio, sys, json, re, time, tempfile, os
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fitz
from winsdk.windows.media.ocr import OcrEngine
from winsdk.windows.globalization import Language
from winsdk.windows.storage import StorageFile
from winsdk.windows.graphics.imaging import BitmapDecoder, BitmapPixelFormat, BitmapAlphaMode

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_QB    = Path(r"D:\CLAUDE\Projet CFA\CFA L1\3. QB CFA WEB PAID-1000 MCQs")
BASE_MOCKS = Path(r"D:\CLAUDE\Projet CFA\CFA L1\9. CFA WEB MOCKS-900 MCQs")
CACHE_QB   = Path(__file__).parent / "_cache_cfaweb_qb"
CACHE_MOCKS= Path(__file__).parent / "_cache_cfaweb_mocks"

QB_FILES = [
    ("Fixed income, FSA.pdf",  "Fixed_income,_FSA.json"),
    ("Portfolio, Quants.pdf",  "Portfolio,_Quants.json"),
]
MOCK_FILES = [
    ("MOCK 2 SS1 ANS (1).pdf", "MOCK_2_SS1_ANS_1.json"),
    ("MOCK 2 SS2 ANS.pdf",     "MOCK_2_SS2_ANS.json"),
    ("MOCK 3 SS1 ANS.pdf",     "MOCK_3_SS1_ANS.json"),
    ("MOCK 6 SS1 ANS (2).pdf", "MOCK_6_SS1_ANS_2.json"),
    ("MOCK 6 SS2 ANS.pdf",     "MOCK_6_SS2_ANS.json"),
]

# "of N" total → topic per PDF
QB_TOTAL_TO_TOPIC = {
    "Fixed income, FSA.pdf": {
        106: "Fixed Income",
        130: "Financial Statement Analysis",
    },
    "Portfolio, Quants.pdf": {
        100: "Portfolio Management",
        90:  "Quantitative Methods",
    },
}

# ── OCR engine ─────────────────────────────────────────────────────────────────
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = OcrEngine.try_create_from_language(Language("en-US"))
    return _engine


async def ocr_page_async(pdf_path: str, page_idx: int, zoom: float = 2.0) -> str:
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    tmp = tempfile.mktemp(suffix=".png")
    pix.save(tmp)
    doc.close()

    engine = get_engine()
    file = await StorageFile.get_file_from_path_async(tmp)
    stream = await file.open_read_async()
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async(
        BitmapPixelFormat.BGRA8, BitmapAlphaMode.PREMULTIPLIED
    )
    result = await engine.recognize_async(bitmap)
    os.remove(tmp)
    return result.text or ""


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# ── Topic normalisation ────────────────────────────────────────────────────────
TOPIC_MAP = {
    "fixed income":                     "Fixed Income",
    "financial statement analysis":     "Financial Statement Analysis",
    "financial reporting and analysis": "Financial Statement Analysis",
    "fsa":                              "Financial Statement Analysis",
    "portfolio management":             "Portfolio Management",
    "portfolio":                        "Portfolio Management",
    "quantitative methods":             "Quantitative Methods",
    "quantitative":                     "Quantitative Methods",
    "quant":                            "Quantitative Methods",
    "alternative investments":          "Alternative Investments",
    "corporate issuers":                "Corporate Issuers",
    "corporate finance":                "Corporate Issuers",
    "derivatives":                      "Derivatives",
    "economics":                        "Economics",
    "equity investments":               "Equity Investments",
    "equity":                           "Equity Investments",
    "ethics":                           "Ethics & Professional Standards",
    "ethics & professional standards":  "Ethics & Professional Standards",
    "ethics and professional standards":"Ethics & Professional Standards",
}

def _norm_topic(raw: str) -> str:
    if not raw:
        return ""
    s = re.sub(r"\s*[-–]\s*(?:answers?|questions?)\s*$", "", raw, flags=re.IGNORECASE).strip()
    sl = s.lower()
    for k, v in TOPIC_MAP.items():
        if k in sl:
            return v
    return raw.strip()


def _extract_topic(text: str) -> str:
    m = re.search(r"([A-Za-z][A-Za-z ,&]+?)\s*:?\s*Practice Pack", text, re.IGNORECASE)
    if m:
        return _norm_topic(m.group(1).strip())
    return ""


def _extract_section_total(text: str) -> int | None:
    m = re.search(r"(?:Question|Answer)\s+\d+\s+(?:of|Of)\s+(\d+)", text)
    return int(m.group(1)) if m else None


# ── Option split helpers ───────────────────────────────────────────────────────
def _split_options(block: str):
    a_patterns = [
        r"(?<=[?:!])\s*A[.)]\s+",
        r"(?<=[?:!])\s*A\s+",
        r"\s+A[.]\s+(?=[A-Za-z\d(])",
    ]
    b_patterns = [r"\s+B[.]\s+", r"\s+B\s+(?=[A-Z\d(])"]
    c_patterns = [r"\s+C[.]\s+", r"\s+C\s+(?=[A-Z\d(])"]

    a_match = None
    for pat in a_patterns:
        for m in re.finditer(pat, block):
            a_match = m
            break
        if a_match:
            break

    if not a_match:
        return _clean(block), "", "", ""

    stem = _clean(block[:a_match.start()])
    after_a = block[a_match.end():]

    b_match = None
    for pat in b_patterns:
        m = re.search(pat, after_a)
        if m:
            b_match = m
            break

    if not b_match:
        return stem, _clean(after_a), "", ""

    a_text = _clean(after_a[:b_match.start()])
    after_b = after_a[b_match.end():]

    c_match = None
    for pat in c_patterns:
        m = re.search(pat, after_b)
        if m:
            c_match = m
            break

    if not c_match:
        return stem, a_text, _clean(after_b), ""

    b_text = _clean(after_b[:c_match.start()])
    c_text = _clean(after_b[c_match.end():])
    return stem, a_text, b_text, c_text


# ── Correct answer extraction ──────────────────────────────────────────────────
def _find_correct_in_solution(sol_text: str) -> tuple:
    expl = ""

    for pat in [r"\b([ABC])[.)]\s+Correct\b", r"\b([ABC])\s+Correct\b"]:
        m = re.search(pat, sol_text, re.IGNORECASE)
        if m:
            correct = m.group(1).upper()
            e_m = re.search(r"[ABC][.)]\s+Correct[.:\s]+([^.]{10,100}\.)", sol_text, re.IGNORECASE)
            if e_m:
                expl = _clean(e_m.group(1))
            return correct, expl

    option_status = {}
    for lbl in ("A", "B", "C"):
        if re.search(rf"\b{lbl}[.)]\s+Correct\b", sol_text, re.IGNORECASE):
            option_status[lbl] = "correct"
        elif re.search(rf"\b{lbl}[.)]\s+Incorrect\b", sol_text, re.IGNORECASE):
            option_status[lbl] = "incorrect"

    correct_labels   = [k for k, v in option_status.items() if v == "correct"]
    incorrect_labels = [k for k, v in option_status.items() if v == "incorrect"]

    if len(correct_labels) == 1:
        return correct_labels[0], expl

    if len(incorrect_labels) == 2:
        remaining = [x for x in ("A", "B", "C") if x not in incorrect_labels]
        if len(remaining) == 1:
            return remaining[0], expl

    for m_corr in re.finditer(r"\bCorrect\b", sol_text, re.IGNORECASE):
        pre = sol_text[:m_corr.start()]
        m_lbl = re.search(r"\b([ABCabc])[.)]\s*$", pre.rstrip())
        if m_lbl:
            return m_lbl.group(1).upper(), expl
        all_lbls = re.findall(r"\b([ABCabc])[.)]\s", pre)
        if all_lbls:
            return all_lbls[-1].upper(), expl

    return None, ""


# ── QB question page ───────────────────────────────────────────────────────────
def parse_qb_question_page(text: str, page_idx: int, total_topic_map: dict = None) -> dict:
    topic = _extract_topic(text)
    if not topic and total_topic_map:
        total = _extract_section_total(text)
        if total:
            topic = total_topic_map.get(total, "")

    parts = re.split(r"Question\s+(\d+)\s+(?:of|Of)\s+\d+\s*(?:Question\s+)?", text)
    items = []
    i = 1
    while i + 1 < len(parts):
        try:
            n = int(parts[i])
        except (ValueError, TypeError):
            i += 2
            continue
        stem, a, b, c = _split_options(parts[i + 1])
        if stem:
            items.append({"n": n, "stem": stem, "A": a, "B": b, "C": c})
        i += 2

    if not items:
        return {"page_type": "other", "page_idx": page_idx}
    return {"page_type": "questions", "topic": topic or None, "items": items, "page_idx": page_idx}


# ── QB answer page ─────────────────────────────────────────────────────────────
def parse_qb_answer_page(text: str, page_idx: int, total_topic_map: dict = None) -> dict:
    topic = _extract_topic(text)
    if not topic and total_topic_map:
        total = _extract_section_total(text)
        if total:
            topic = total_topic_map.get(total, "")

    parts = re.split(r"Answer\s+(\d+)\s+(?:of|Of)\s+\d+\s*(?:Answer\s+)?", text)
    items = []
    i = 1
    while i + 1 < len(parts):
        try:
            n = int(parts[i])
        except (ValueError, TypeError):
            i += 2
            continue
        block = parts[i + 1]
        sol_idx = re.search(r"\bSolution\b", block, re.IGNORECASE)
        sol_text = block[sol_idx.end():] if sol_idx else block
        correct, expl = _find_correct_in_solution(sol_text)
        if correct:
            items.append({"n": n, "correct": correct, "expl": expl})
        i += 2

    if not items:
        return {"page_type": "other", "page_idx": page_idx}
    return {"page_type": "answers", "topic": topic or None, "items": items, "page_idx": page_idx}


def parse_qb_page(text: str, page_idx: int, total_topic_map: dict = None) -> dict:
    has_answer   = bool(re.search(r"Answer\s+\d+\s+(?:of|Of)\s+\d+", text, re.IGNORECASE))
    has_question = bool(re.search(r"Question\s+\d+\s+(?:of|Of)\s+\d+", text, re.IGNORECASE))

    if has_answer and has_question:
        m_a = re.search(r"Answer\s+\d+", text, re.IGNORECASE)
        m_q = re.search(r"Question\s+\d+", text, re.IGNORECASE)
        if m_a and m_q:
            if m_a.start() <= m_q.start():
                return parse_qb_answer_page(text, page_idx, total_topic_map)
            return parse_qb_question_page(text, page_idx, total_topic_map)
    if has_answer:
        return parse_qb_answer_page(text, page_idx, total_topic_map)
    if has_question:
        return parse_qb_question_page(text, page_idx, total_topic_map)
    return {"page_type": "other", "page_idx": page_idx}


# ── Mock page ──────────────────────────────────────────────────────────────────
def parse_mock_page(text: str, page_idx: int) -> dict:
    if not re.search(r"Question\s+\d+", text, re.IGNORECASE):
        return {"page_type": "other", "page_idx": page_idx}

    sol_split = re.split(r"\bSolution\b", text, maxsplit=1, flags=re.IGNORECASE)
    if len(sol_split) < 2:
        return {"page_type": "other", "page_idx": page_idx}

    q_part, sol_part = sol_split
    m = re.search(r"Question\s+(\d+)", q_part, re.IGNORECASE)
    qnum = int(m.group(1)) if m else None

    q_marker = re.search(r"\bQ\.\s+", q_part, re.IGNORECASE)
    if q_marker:
        stem_block = q_part[q_marker.end():]
    else:
        stem_block = re.sub(r"Question\s+\d+\s+(?:of|Of)\s+\d+\s*", "", q_part, flags=re.IGNORECASE)

    stem, a_opt, b_opt, c_opt = _split_options(stem_block)
    correct, expl = _find_correct_in_solution(sol_part)

    if correct not in ("A", "B", "C"):
        return {"page_type": "other", "page_idx": page_idx}

    topic_keywords = [
        ("Ethics & Professional Standards", ["ethics", "professional standards", "gips", "standard", "code of ethics"]),
        ("Quantitative Methods", ["quantitative", "probability", "regression", "time value", "variance", "standard deviation", "hypothesis"]),
        ("Economics", ["economics", "gdp", "monetary policy", "fiscal", "aggregate demand", "elasticity", "inflation"]),
        ("Financial Statement Analysis", ["financial statement", "financial reporting", "income statement", "balance sheet", "cash flow", "deferred tax", "ifrs", "gaap", "eps"]),
        ("Corporate Issuers", ["corporate issuers", "corporate finance", "capital structure", "dividend", "working capital", "wacc", "leverage"]),
        ("Equity Investments", ["equity", "valuation", "price-to-earnings", "dcf", "residual income", "gordon growth"]),
        ("Fixed Income", ["fixed income", "bond", "yield", "duration", "convexity", "credit spread"]),
        ("Derivatives", ["derivative", "option", "futures", "forward", "swap", "hedge"]),
        ("Alternative Investments", ["alternative", "hedge fund", "private equity", "real estate", "commodities"]),
        ("Portfolio Management", ["portfolio", "risk", "return", "sharpe", "efficient frontier", "capm", "ips"]),
    ]
    topic = ""
    combined = (sol_part + text[-300:]).lower()
    for t_name, keywords in topic_keywords:
        if any(kw in combined for kw in keywords):
            topic = t_name
            break

    return {
        "qnum": qnum,
        "topic": topic or None,
        "stem": stem if stem else _clean(stem_block[:200]),
        "A": a_opt,
        "B": b_opt,
        "C": c_opt,
        "correct": correct,
        "expl": expl,
        "page_idx": page_idx,
    }


# ── Main extraction ────────────────────────────────────────────────────────────
async def process_pdf(pdf_path: Path, cache_path: Path, is_mock: bool):
    pdf_name = pdf_path.name
    total_topic_map = QB_TOTAL_TO_TOPIC.get(pdf_name, {})
    print(f"\n{'Mock' if is_mock else 'QB'}: {pdf_name} ({cache_path.name})", flush=True)
    doc = fitz.open(str(pdf_path))
    n_pages = doc.page_count
    doc.close()
    print(f"  {n_pages} pages...", flush=True)

    results = []
    for i in range(n_pages):
        print(f"  Page {i+1}/{n_pages}", end="\r", flush=True)
        try:
            text = await ocr_page_async(str(pdf_path), i)
            entry = parse_mock_page(text, i) if is_mock else parse_qb_page(text, i, total_topic_map)
        except Exception as e:
            print(f"\n  [WARN] page {i+1}: {e}", flush=True)
            entry = {"page_type": "other", "page_idx": i}
        results.append(entry)

    if is_mock:
        valid = sum(1 for r in results if r.get("correct") in ("A","B","C"))
        print(f"\n  {valid}/{n_pages} valid Q+A", flush=True)
    else:
        q_items = sum(len(r.get("items") or []) for r in results if r.get("page_type") == "questions")
        a_items = sum(len(r.get("items") or []) for r in results if r.get("page_type") == "answers")
        print(f"\n  Q-items={q_items}, A-items={a_items}", flush=True)

    cache_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved -> {cache_path.name}", flush=True)
    return results


async def main():
    t0 = time.time()
    for pdf_name, cache_name in QB_FILES:
        pdf_path = BASE_QB / pdf_name
        cache_path = CACHE_QB / cache_name
        if pdf_path.exists():
            await process_pdf(pdf_path, cache_path, is_mock=False)
        else:
            print(f"[SKIP] {pdf_path}")

    for pdf_name, cache_name in MOCK_FILES:
        pdf_path = BASE_MOCKS / pdf_name
        cache_path = CACHE_MOCKS / cache_name
        if pdf_path.exists():
            await process_pdf(pdf_path, cache_path, is_mock=True)
        else:
            print(f"[SKIP] {pdf_path}")

    print(f"\nAll done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
