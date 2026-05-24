#!/usr/bin/env python3
"""
Re-extract missing CFA_WEB caches via Claude Vision.
Run AFTER setting ANTHROPIC_API_KEY environment variable.

Missing caches (empty/invalid):
  QB:    Fixed income, FSA.pdf
         Portfolio, Quants.pdf
  Mocks: MOCK 2 SS1 ANS (1).pdf, MOCK 2 SS2 ANS.pdf
         MOCK 3 SS1 ANS.pdf
         MOCK 6 SS1 ANS (2).pdf, MOCK 6 SS2 ANS.pdf

Usage:
  set ANTHROPIC_API_KEY=sk-ant-...
  python scripts/cfaweb_reextract_missing.py

Then re-run: python scripts/cfaweb_full_audit.py
"""
import sys, json, time, base64, re, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import fitz
import anthropic

BASE_QB    = Path(r"D:\CLAUDE\Projet CFA\CFA L1\3. QB CFA WEB PAID-1000 MCQs")
BASE_MOCKS = Path(r"D:\CLAUDE\Projet CFA\CFA L1\9. CFA WEB MOCKS-900 MCQs")
CACHE_QB   = Path(__file__).parent / "_cache_cfaweb_qb"
CACHE_MOCKS= Path(__file__).parent / "_cache_cfaweb_mocks"

_RETRY_DELAYS = [30, 60, 120, 180]

QB_PROMPT = """You are extracting CFA Level 1 exam content from a scanned PDF page.
RETURN ONLY VALID JSON — no markdown, no explanation.

QUESTION PAGE (shows questions A/B/C, no answers marked):
{"page_type":"questions","topic":"<section header or null>","items":[{"n":<int>,"stem":"<question text>","A":"<option A>","B":"<option B>","C":"<option C>"}]}

ANSWER PAGE (shows Answer N of M, Answer: X, or Correct bolded next to letter):
{"page_type":"answers","topic":"<section header or null>","items":[{"n":<int>,"correct":"<A/B/C>","expl":"<one sentence why>"}]}

OTHER (cover, blank, TOC, transition page):
{"page_type":"other"}

RULES:
- Use the LOCAL n from "Question N of M" or "Answer N of M"
- Include ALL questions/answers on the page in items[]
- correct must be exactly "A", "B", or "C"
- "Correct" printed in bold/highlighted next to a letter = that letter is correct
- "Answer: C" or "C is correct" = use that letter
- For answer pages, focus ONLY on detecting the correct letter; expl is one short sentence
"""

MOCK_PROMPT = """You are extracting a CFA Level 1 mock exam question from a scanned answer-key page.
Each page shows ONE question: stem, options A/B/C, and the solution section marking the correct answer.
RETURN ONLY VALID JSON — no markdown:
{"qnum":<int or null>,"topic":"<CFA topic or null>","stem":"<full question text>","A":"<option A text>","B":"<option B text>","C":"<option C text>","correct":"<A/B/C>","expl":"<one sentence explaining why correct>"}
If blank, cover, or no complete Q with answer: {"page_type":"other"}
CRITICAL: correct = the ONE letter explicitly labelled 'Correct' or 'A. Correct because...' in the Solution section.
"""

def _page_to_png(page, zoom=2.5) -> bytes:
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")

def _call_vision(client, img_bytes: bytes, prompt: str, attempt=0) -> dict:
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                    "data": base64.b64encode(img_bytes).decode()}},
                {"type": "text", "text": prompt},
            ]}],
        )
        text = r.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except Exception as e:
        err = str(e)
        if ("429" in err or "rate_limit" in err) and attempt < len(_RETRY_DELAYS):
            w = _RETRY_DELAYS[attempt]
            print(f"    [RATE LIMIT] waiting {w}s ...")
            time.sleep(w)
            return _call_vision(client, img_bytes, prompt, attempt + 1)
        if attempt < 2:
            time.sleep(5)
            return _call_vision(client, img_bytes, prompt, attempt + 1)
        print(f"    [WARN] Vision failed: {e}")
        return {"page_type": "other"}

def extract_pdf(pdf_path: Path, cache_path: Path, client, prompt: str) -> list:
    print(f"  [{pdf_path.stat().st_size//1024}KB] {pdf_path.name}")
    doc = fitz.open(str(pdf_path))
    results = []
    for i, page in enumerate(doc):
        print(f"    page {i+1}/{len(doc)}", end="\r")
        img = _page_to_png(page)
        result = _call_vision(client, img, prompt)
        result["page_idx"] = i
        results.append(result)
        time.sleep(2.0)
    doc.close()
    # Save cache
    cache_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    q_count = sum(len(p.get("items", [])) for p in results if p.get("page_type") == "answers")
    mock_count = sum(1 for p in results if "correct" in p)
    print(f"\n    -> {len(results)} pages, answers={q_count or mock_count}")
    return results

def main():
    ak = os.environ.get("ANTHROPIC_API_KEY", "")
    if not ak:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        print("Run: set ANTHROPIC_API_KEY=sk-ant-api03-...")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=ak)
    print("Vision client ready.\n")

    # ── QB missing ────────────────────────────────────────────────────────────
    QB_MISSING = [
        ("Fixed income, FSA.pdf",  "Fixed_income,_FSA.json"),
        ("Portfolio, Quants.pdf",  "Portfolio,_Quants.json"),
    ]
    print("=== QB PDFs (missing) ===")
    for pdf_name, cache_name in QB_MISSING:
        pdf_path   = BASE_QB / pdf_name
        cache_path = CACHE_QB / cache_name
        if not pdf_path.exists():
            print(f"  [SKIP] not found: {pdf_name}")
            continue
        if cache_path.exists():
            cache_path.unlink()
            print(f"  Deleted stale cache: {cache_name}")
        extract_pdf(pdf_path, cache_path, client, QB_PROMPT)

    # ── Mock ANS missing ──────────────────────────────────────────────────────
    MOCK_MISSING = [
        ("MOCK 2 SS1 ANS (1).pdf", "MOCK_2_SS1_ANS_1.json"),
        ("MOCK 2 SS2 ANS.pdf",     "MOCK_2_SS2_ANS.json"),
        ("MOCK 3 SS1 ANS.pdf",     "MOCK_3_SS1_ANS.json"),
        ("MOCK 6 SS1 ANS (2).pdf", "MOCK_6_SS1_ANS_2.json"),
        ("MOCK 6 SS2 ANS.pdf",     "MOCK_6_SS2_ANS.json"),
    ]
    print("\n=== Mock ANS PDFs (missing) ===")
    for pdf_name, cache_name in MOCK_MISSING:
        pdf_path   = BASE_MOCKS / pdf_name
        cache_path = CACHE_MOCKS / cache_name
        if not pdf_path.exists():
            print(f"  [SKIP] not found: {pdf_name}")
            continue
        if cache_path.exists():
            cache_path.unlink()
            print(f"  Deleted stale cache: {cache_name}")
        extract_pdf(pdf_path, cache_path, client, MOCK_PROMPT)

    print("\nRe-extraction complete.")
    print("Now run: python scripts/cfaweb_full_audit.py")

if __name__ == "__main__":
    main()
