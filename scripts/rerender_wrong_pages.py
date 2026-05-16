#!/usr/bin/env python3
"""Re-render wrong-page images by searching PDF text more carefully."""
import sys, json, fitz
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IMG_DIR = Path(__file__).parent / "_table_images"

# Each entry: (qid, pdf_path, search_terms_list)
# search_terms_list: try each term in order until a page is found
TARGETS = [
    (
        "9c51aa0b-2104-46cd-869f-7cfc2d0a2ede",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\4. Corporate Issuers\4.04 Working Capital and Liquidity - Answers.pdf",
        ["evaluating several companies", "best accounts receivable turnover"],
    ),
    (
        "974f206c-25b6-49f5-9a44-9923ad0a5abb",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\5. Financial Statement Analysis\5.11 Financial Analysis Techniques - Answers.pdf",
        ["uses LIFO to determine", "LIFO reserve", "current ratio most likely"],
    ),
    (
        "96b2e751-28aa-40c6-b8a1-83d2ce8bae66",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\6. Equity Investments\6.08 Equity Valuation Concepts And Basic Tools - Answers.pdf",
        ["EV/EBITDA ratio is 25.4", "market value of the company", "common equity"],
    ),
    (
        "1af08d3f-b8ac-4fa7-abf1-651a97c253dc",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\1. Quantitative Methods\1.04 Probability Trees and Conditional Expectations - Answers.pdf",
        ["CEO's compensation", "calculated probability of 0.38"],
    ),
    (
        "a86e4c7c-2cd9-4f38-9cbb-90390b4d7236",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\1. Quantitative Methods\1.10 Simple Linear Regression - Answers.pdf",
        ["crude oil prices", "gross margin", "prediction interval"],
    ),
    (
        "17e887d4-ee3a-4a24-a29a-e80296187806",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\4. Corporate Issuers\4.06 Capital Structure - Answers.pdf",
        ["issued £30 million", "CAPM approach", "weighted average cost of capital"],
    ),
    (
        "74e53ac8-ad99-495a-ae73-b07f8b8de771",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\5. Financial Statement Analysis\5.11 Financial Analysis Techniques - Answers.pdf",
        ["efficiency compares with the industry", "annual data for a company"],
    ),
    (
        "3dd022f4-ab26-4829-8c17-b0931836c404",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\6. Equity Investments\6.08 Equity Valuation Concepts And Basic Tools - Answers.pdf",
        ["50 million common and 160,000 preferred", "market price per common share"],
    ),
    (
        "cf241f9a-3699-4f31-8d1b-3deadbbbcf91",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\6. Equity Investments\6.08 Equity Valuation Concepts And Basic Tools - Answers.pdf",
        ["justified forward price-to-earnings", "long-term dividend growth rate"],
    ),
    (
        "387e313d-c128-4048-91c6-ae252df6ee2b",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\7. Fixed Income\7.06 Fixed-Income Bond Valuation Prices and Yields - Answers.pdf",
        ["exception to the maturity effect", "maturity effect"],
    ),
    (
        "770170b4-ce40-486c-8ae2-a0ad70aefeaa",
        r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs\7. Fixed Income\7.07 Yield and Yield Spread Measures for Fixed-Rate Bonds - Answers.pdf",
        ["trades at 78.3", "I-spread", "78.3"],
    ),
]

ZOOM = 2.5
MAT = fitz.Matrix(ZOOM, ZOOM)

for qid, pdf_path, terms in TARGETS:
    pdf = Path(pdf_path)
    if not pdf.exists():
        print(f"  {qid[:8]} PDF NOT FOUND: {pdf_path}")
        continue

    doc = fitz.open(str(pdf))
    found_page = None

    for term in terms:
        for pno in range(len(doc)):
            page = doc[pno]
            if page.search_for(term):
                found_page = pno
                break
        if found_page is not None:
            break

    if found_page is None:
        print(f"  {qid[:8]} NOT FOUND in PDF (tried: {terms})")
        doc.close()
        continue

    page = doc[found_page]
    pix = page.get_pixmap(matrix=MAT)
    out = IMG_DIR / f"{qid}.png"
    pix.save(str(out))
    doc.close()
    print(f"  {qid[:8]} -> page {found_page} -> {out.name}")

print("\nDone.")
