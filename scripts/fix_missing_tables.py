#!/usr/bin/env python3
"""
Fix incomplete UWorld questions where tables are embedded PDF images.

Pipeline per question:
  1. Locate the source PDF via subtopic → topic folder mapping
  2. Find the page containing the question (text match)
  3. Render the embedded image region with pymupdf
  4. Extract as markdown via Claude Vision
  5. Reconstruct question_en with table inserted
  6. PATCH Supabase

Run: python scripts/fix_missing_tables.py [--dry-run]
"""

import base64
import io
import json
import re
import sys
import time

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path
from typing import Optional

import fitz  # pymupdf
import pdfplumber

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Config ────────────────────────────────────────────────────────────────────

UWORLD_ROOT = Path(r"D:\CLAUDE\Projet CFA\CFA L1\6. TOUGH QB UWORLD-2000 MCQs")
SECRETS_PATH = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
DRY_RUN = "--dry-run" in sys.argv

# Subtopic prefix → UWorld topic folder name
SUBTOPIC_PREFIX_MAP = {
    "1.": "1. Quantitative Methods",
    "2.": "2. Economics",
    "3.": "3. Portfolio Management",
    "4.": "4. Corporate Issuers",
    "5.": "5. Financial Statement Analysis",
    "6.": "6. Equity Investments",
    "7.": "7. Fixed Income",
    "8.": "8. Derivatives",
    "9.": "9. Alternative Investments",
    "10.": "3. Portfolio Management",   # 10.xx subtopics live in Portfolio Mgmt folder
    "11.": "10. Ethics",                # Ethics subtopics use 11.xx prefix
}

# Rate-limit: max Vision API calls per minute (pro plan)
VISION_CALLS_PER_MIN = 8
CALL_INTERVAL = 60.0 / VISION_CALLS_PER_MIN  # seconds between calls


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_secrets(path: Path) -> dict:
    result: dict = {}
    section = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                result[section] = {}
            elif "=" in line and section:
                k, _, v = line.partition("=")
                result[section][k.strip()] = v.strip().strip('"').strip("'")
    return result


def get_supabase():
    secrets = load_secrets(SECRETS_PATH)
    from supabase import create_client
    return create_client(
        secrets["supabase"]["SUPABASE_URL"],
        secrets["supabase"]["SUPABASE_SERVICE_KEY"],
    )


def get_anthropic_client():
    """Return Anthropic client using Claude Code's OAuth token."""
    import anthropic
    creds_path = Path.home() / ".claude" / ".credentials.json"
    with open(creds_path) as f:
        creds = json.load(f)
    token = creds["claudeAiOauth"]["accessToken"]
    return anthropic.Anthropic(auth_token=token)


# ── DB query: fetch incomplete questions ──────────────────────────────────────

TRULY_MISSING_RE = re.compile(
    r"the following\s+(?:data|exhibit|table|figure|chart|financial statements?|financial information|information)\s*:\s*"
    r"(?:Based|If|Assuming|Which|The company|The analyst|An analyst|Using|From|According|Given that|Determine|Calculate)",
    re.IGNORECASE,
)
NAME_ONLY_RE = re.compile(
    r"^(?:Company|Portfolio|Fund|Firm|Manager|Account)\s+[A-Z]$",
    re.IGNORECASE,
)
COLON_SPLIT_RE = re.compile(
    r"(.*?the following\s+\w+\s*:)\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)


def fetch_incomplete(sb) -> list:
    page_size = 1000
    offset = 0
    results = []
    while True:
        rows = sb.table("questions").select(
            "id,topic,subtopic,source,question_en,option_a,option_b,option_c"
        ).range(offset, offset + page_size - 1).execute()
        if not rows.data:
            break
        for q in rows.data:
            if q.get("source") != "UWorld":
                continue
            text = q.get("question_en", "") or ""
            if "|" in text:
                continue
            opts = [(q.get(f"option_{k}") or "").strip() for k in ("a", "b", "c")]
            name_opts = all(NAME_ONLY_RE.match(o) for o in opts if o)
            if TRULY_MISSING_RE.search(text) or name_opts:
                results.append(q)
        offset += page_size
        if len(rows.data) < page_size:
            break
    return results


# ── PDF: locate source file ───────────────────────────────────────────────────

def find_pdf(subtopic: str) -> Optional[Path]:
    """Return the question PDF path for a given subtopic slug."""
    for prefix, folder_name in SUBTOPIC_PREFIX_MAP.items():
        if subtopic.startswith(prefix):
            pdf_path = UWORLD_ROOT / folder_name / "ONLY QSTN" / f"{subtopic}.pdf"
            if pdf_path.exists():
                return pdf_path
    return None


# ── PDF: find page index containing the question text ─────────────────────────

def find_question_page(pdf_path: Path, question_snippet: str) -> Optional[int]:
    """Return 0-based page index where the question starts.

    Finds the page that best matches the question using multiple text probes,
    preferring pages that contain both pre-colon AND post-colon text.
    """
    # Extract text probes
    m = re.search(r"the following\s+\w+", question_snippet, re.IGNORECASE)
    pre_text = question_snippet[:m.start()].strip()[-70:] if m else question_snippet[:70].strip()
    m2 = re.search(
        r"the following\s+\w+\s*:\s*(.{15,})",
        question_snippet,
        re.IGNORECASE,
    )
    post_text = m2.group(1).strip()[:70] if m2 else ""

    pre_norm = re.sub(r"\s+", " ", pre_text).strip().lower()
    post_norm = re.sub(r"\s+", " ", post_text).strip().lower()

    # Extra probe: first 50 chars of full question (usually unique enough)
    prefix_norm = re.sub(r"\s+", " ", question_snippet[:50]).strip().lower()

    # Load all pages once
    try:
        page_texts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = re.sub(r"\s+", " ", page.extract_text() or "").lower()
                page_texts.append(t)
    except Exception as e:
        print(f"    [WARN] pdfplumber error on {pdf_path.name}: {e}")
        return None

    # Pass 1: page has BOTH pre and post text (most reliable)
    if len(pre_norm) >= 10 and len(post_norm) >= 10:
        for idx, t in enumerate(page_texts):
            if pre_norm in t and post_norm in t:
                return idx

    # Pass 2: page has the post text alone (post is usually more specific)
    if len(post_norm) >= 15:
        for idx, t in enumerate(page_texts):
            if post_norm in t:
                return idx

    # Pass 3: page has the first 50-char prefix of the question
    if len(prefix_norm) >= 20:
        for idx, t in enumerate(page_texts):
            if prefix_norm in t:
                return idx

    # Pass 4: page has the pre text alone (last resort, may give false positives)
    if len(pre_norm) >= 10:
        for idx, t in enumerate(page_texts):
            if pre_norm in t:
                return idx

    return None


# ── pymupdf: render image region from page ────────────────────────────────────

def render_table_region(pdf_path: Path, page_idx: int) -> Optional[bytes]:
    """
    Find embedded raster images on the page and render the bounding region as PNG.
    Falls back to rendering the full page if no specific rect found.
    Returns PNG bytes, or None if no image found.
    """
    try:
        doc = fitz.open(str(pdf_path))
        page = doc[page_idx]

        # Get all embedded images on this page
        img_list = page.get_images(full=True)
        if not img_list:
            doc.close()
            return None

        # Find bounding boxes of all images via image xrefs
        image_rects = []
        for img_info in img_list:
            xref = img_info[0]
            try:
                rects = page.get_image_rects(xref)
                image_rects.extend(rects)
            except Exception:
                pass

        mat = fitz.Matrix(2.5, 2.5)  # 2.5× zoom for clarity

        if not image_rects:
            # Fallback: render top portion of full page (tables usually in top 2/3)
            page_rect = page.rect
            clip = fitz.Rect(0, 0, page_rect.width, page_rect.height * 0.75)
            pix = page.get_pixmap(matrix=mat, clip=clip)
        else:
            # Union of all image rects with slight padding
            union = image_rects[0]
            for r in image_rects[1:]:
                union = union | r

            clip = fitz.Rect(
                max(0, union.x0 - 5),
                max(0, union.y0 - 5),
                union.x1 + 5,
                union.y1 + 5,
            )
            pix = page.get_pixmap(matrix=mat, clip=clip)

        png_bytes = pix.tobytes("png")
        doc.close()
        return png_bytes

    except Exception as e:
        print(f"    [WARN] pymupdf error on {pdf_path.name} p{page_idx}: {e}")
        return None


# ── Claude Vision: extract markdown table ─────────────────────────────────────

_last_call_time = 0.0


def extract_table_via_vision(client, png_bytes: bytes) -> Optional[str]:
    """Send PNG to Claude Vision and get back a markdown table."""
    global _last_call_time

    # Rate limiting
    elapsed = time.time() - _last_call_time
    if elapsed < CALL_INTERVAL:
        time.sleep(CALL_INTERVAL - elapsed)

    img_b64 = base64.standard_b64encode(png_bytes).decode("utf-8")

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "This image is a financial data table from a CFA Level 1 exam question. "
                                "Extract the complete table as a GitHub-flavored markdown table. "
                                "Include ALL rows and columns exactly as shown. "
                                "Return ONLY the markdown table, nothing else. "
                                "Use | separators and a header separator row (|---|---|...)."
                            ),
                        },
                    ],
                }],
            )
            _last_call_time = time.time()
            table_md = resp.content[0].text.strip()
            # Validate: must contain markdown table syntax
            if "|" in table_md and "---" in table_md:
                return table_md
            # If vision returned something without proper table syntax, try to fix
            print(f"    [WARN] Vision returned non-table content: {table_md[:80]}")
            return None

        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                wait = 30 * (attempt + 1)
                print(f"    [RATE LIMIT] Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    [ERROR] Vision API: {e}")
                return None

    return None


# ── Reconstruct question_en with table inserted ────────────────────────────────

def reconstruct_question(question_en: str, table_md: str) -> str:
    """Insert markdown table into question_en at the right position."""
    m = COLON_SPLIT_RE.match(question_en)
    if not m:
        # Fallback: append table before the end
        return question_en + "\n\n" + table_md
    preamble = m.group(1).strip()
    postamble = m.group(2).strip()
    return f"{preamble}\n\n{table_md}\n\n{postamble}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    mode = "DRY RUN" if DRY_RUN else "LIVE UPDATE"
    print(f"=== fix_missing_tables.py — {mode} ===\n")

    sb = get_supabase()
    client = get_anthropic_client()

    incomplete = fetch_incomplete(sb)
    print(f"Found {len(incomplete)} incomplete UWorld questions.\n")

    fixed = 0
    skipped = 0
    errors = 0

    for i, q in enumerate(incomplete):
        qid = q["id"]
        subtopic = q.get("subtopic", "")
        topic = q["topic"]
        question_en = q["question_en"]

        print(f"[{i+1}/{len(incomplete)}] {topic} | {subtopic}")
        print(f"  Q: {question_en[:80]}...")

        # 1. Find PDF
        pdf_path = find_pdf(subtopic)
        if not pdf_path:
            print(f"  [SKIP] PDF not found for subtopic: {subtopic}")
            skipped += 1
            continue

        # 2. Find page
        page_idx = find_question_page(pdf_path, question_en)
        if page_idx is None:
            print(f"  [SKIP] Could not find question page in {pdf_path.name}")
            skipped += 1
            continue
        print(f"  Found on page {page_idx + 1} of {pdf_path.name}")

        # 3. Render table region
        png_bytes = render_table_region(pdf_path, page_idx)
        if not png_bytes:
            print(f"  [SKIP] No embedded image found on page {page_idx + 1}")
            skipped += 1
            continue
        print(f"  Rendered {len(png_bytes)//1024}KB image region")

        if DRY_RUN:
            print("  [DRY RUN] Would call Vision API + update Supabase")
            fixed += 1
            continue

        # 4. Extract table via Vision
        table_md = extract_table_via_vision(client, png_bytes)
        if not table_md:
            print(f"  [ERROR] Vision API returned no table")
            errors += 1
            continue
        print(f"  Extracted table ({table_md.count(chr(10))+1} rows)")

        # 5. Reconstruct question
        new_question_en = reconstruct_question(question_en, table_md)
        print(f"  New length: {len(question_en)} -> {len(new_question_en)} chars")

        # 6. Update Supabase
        try:
            sb.table("questions").update(
                {"question_en": new_question_en}
            ).eq("id", qid).execute()
            print(f"  [OK] Updated in Supabase")
            fixed += 1
        except Exception as e:
            print(f"  [ERROR] Supabase update: {e}")
            errors += 1

        print()

    print(f"\n{'='*50}")
    print(f"Fixed:   {fixed}")
    print(f"Skipped: {skipped}")
    print(f"Errors:  {errors}")


if __name__ == "__main__":
    main()
