#!/usr/bin/env python3
"""
Fast scanner: identify which UWorld Answers PDFs hang in pdfplumber.
Uses subprocess per PDF with 8-second timeout.
Outputs: OK or HANG for each PDF stem.
"""
import sys, subprocess, warnings, logging
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)

from pathlib import Path

UWORLD_ROOT = Path(r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs")
EXTRACT_SCRIPT = Path(__file__).parent / "_pdf_extract.py"
PYTHON = sys.executable
TIMEOUT = 8  # seconds per PDF

hanging = []
ok = []

folders = {
    "1. Quantitative Methods", "2. Economics", "3. Portfolio Management",
    "4. Corporate Issuers", "5. Financial Statement Analysis", "6. Equity Investments",
    "7. Fixed Income", "8. Derivatives", "9. Alternative Investments", "10. Ethics",
}

for folder_name in sorted(folders):
    folder = UWORLD_ROOT / folder_name
    if not folder.exists():
        print(f"[SKIP] {folder_name} not found", flush=True)
        continue
    ans_pdfs = sorted(folder.glob("*- Answers.pdf"))
    print(f"\n{folder_name}: {len(ans_pdfs)} PDFs", flush=True)
    for ans_pdf in ans_pdfs:
        stem = ans_pdf.stem.replace(" - Answers", "")
        proc = subprocess.Popen(
            [PYTHON, str(EXTRACT_SCRIPT), str(ans_pdf)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            stdout, _ = proc.communicate(timeout=TIMEOUT)
            chars = len(stdout)
            print(f"  OK  {stem}: {chars} chars", flush=True)
            ok.append(stem)
        except subprocess.TimeoutExpired:
            proc.kill()
            print(f"  HANG {stem}", flush=True)
            hanging.append(stem)

print("\n" + "="*60)
print(f"OK: {len(ok)} | HANG: {len(hanging)}")
print("\nHANGING PDFs (add to _UWORLD_PDF_SKIP):")
for h in hanging:
    print(f'    "{h}",')
