#!/usr/bin/env python3
"""
CFA_WEB full answer audit.
1. Re-extracts any empty/partial caches via Claude Vision.
2. Joins QB Q-pages + A-pages by (topic, n).
3. Mocks: already one record per Q with correct field.
4. Matches cached stems → DB questions by text similarity.
5. Outputs mismatches + PS1 to apply fixes.

Run: python scripts/cfaweb_full_audit.py [--dry-run] [--skip-vision]
"""
import sys, json, re, time, base64, argparse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
from difflib import SequenceMatcher

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_QB    = Path(r"D:\CLAUDE\Projet CFA\CFA L1\3. QB CFA WEB PAID-1000 MCQs")
BASE_MOCKS = Path(r"D:\CLAUDE\Projet CFA\CFA L1\9. CFA WEB MOCKS-900 MCQs")
CACHE_QB   = Path(__file__).parent / "_cache_cfaweb_qb"
CACHE_MOCKS= Path(__file__).parent / "_cache_cfaweb_mocks"
DUMP_FILE  = r"C:\Users\codjo\AppData\Local\Temp\wib_dump_fresh.json"
OUT_FIXES  = r"C:\Users\codjo\AppData\Local\Temp\cfaweb_audit_fixes.json"
OUT_PS1    = r"C:\Users\codjo\AppData\Local\Temp\apply_cfaweb_fixes.ps1"
OUT_FULL   = r"C:\Users\codjo\AppData\Local\Temp\cfaweb_audit_full.json"

API_KEY    = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ"
    ".epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8"
)
SUPABASE_URL = "https://qlcakqtrambahrofnhho.supabase.co/rest/v1/questions"

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--skip-vision", action="store_true", help="Skip Vision re-extraction (use existing caches only)")
args = parser.parse_args()

# ── Vision helpers ────────────────────────────────────────────────────────────
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

try:
    import anthropic as _anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

_RETRY_DELAYS = [30, 60, 120, 180]

def _page_to_png(page, zoom=2.5) -> bytes:
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")

QB_PROMPT = """You are extracting CFA Level 1 exam content from a scanned PDF page.
RETURN ONLY VALID JSON — no markdown, no explanation.

Determine the page type:

QUESTION PAGE (shows questions A/B/C, no answers marked):
{"page_type":"questions","topic":"<section header or null>","items":[{"n":<int>,"stem":"<question text>","A":"<option A>","B":"<option B>","C":"<option C>"}]}

ANSWER PAGE (shows Answer N of M, Answer: X, or Correct bolded):
{"page_type":"answers","topic":"<section header or null>","items":[{"n":<int>,"correct":"<A/B/C>","expl":"<one sentence>"}]}

OTHER (cover, blank, TOC):
{"page_type":"other"}

RULES:
- Use the LOCAL n from "Question N of M" or "Answer N of M"
- If multiple Q or A on same page, include ALL in items[]
- correct must be exactly "A", "B", or "C"
- "Correct" bolded next to a letter → that letter is correct
- "Answer: C" explicit → use that letter
"""

MOCK_PROMPT = """You are extracting a CFA Level 1 mock exam Q+A from a scanned answer-key page.
Each page shows ONE question: stem, options A/B/C, and solution with "Correct" next to the right letter.
RETURN ONLY VALID JSON — no markdown:
{"qnum":<int or null>,"topic":"<CFA topic or null>","stem":"<full question>","A":"<opt A>","B":"<opt B>","C":"<opt C>","correct":"<A/B/C>","expl":"<one sentence>"}
If blank/cover/no complete Q: {"page_type":"other"}
RULES: correct = the letter labelled 'Correct' in the Solution section.
"""

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

def _is_cache_valid(cache_path: Path) -> bool:
    """Return True if cache has at least one item with real content."""
    if not cache_path.exists():
        return False
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            return False
        # Check if any item has real content
        for item in data:
            if isinstance(item, dict):
                # QB: page_type == questions/answers with items
                if item.get("page_type") in ("questions", "answers") and item.get("items"):
                    return True
                # Mock: has correct field
                if "correct" in item:
                    return True
        return False
    except Exception:
        return False

def extract_qb_pdf(pdf_path: Path, cache_path: Path, client) -> list:
    """Extract QB PDF pages (Q and A pages separately)."""
    print(f"  Extracting QB: {pdf_path.name} ({pdf_path.stat().st_size // 1024}KB)...")
    doc = fitz.open(str(pdf_path))
    results = []
    for i, page in enumerate(doc):
        print(f"    page {i+1}/{len(doc)}", end="\r")
        img = _page_to_png(page)
        result = _call_vision(client, img, QB_PROMPT)
        result["page_idx"] = i
        results.append(result)
        time.sleep(2.0)
    doc.close()
    cache_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n    -> {len(results)} pages cached")
    return results

def extract_mock_pdf(pdf_path: Path, cache_path: Path, client) -> list:
    """Extract Mock ANS PDF pages (one Q per page)."""
    print(f"  Extracting Mock: {pdf_path.name} ({pdf_path.stat().st_size // 1024}KB)...")
    doc = fitz.open(str(pdf_path))
    results = []
    for i, page in enumerate(doc):
        print(f"    page {i+1}/{len(doc)}", end="\r")
        img = _page_to_png(page)
        result = _call_vision(client, img, MOCK_PROMPT)
        result["page_idx"] = i
        results.append(result)
        time.sleep(2.0)
    doc.close()
    cache_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n    -> {len(results)} pages cached")
    return results

# ── Topic normalization ───────────────────────────────────────────────────────
_TOPIC_STRIP = re.compile(
    r"\s*(practice pack|practi[a-z]+ pack|–\s*answers|-\s*answers|answers|questions|–\s*questions|-\s*questions|:\s*answers)\s*",
    re.IGNORECASE
)
TOPIC_MAP = {
    "alternative investments": "Alternative Investments",
    "alternative investment":  "Alternative Investments",
    "corporate issuers":       "Corporate Issuers",
    "corporate finance":       "Corporate Issuers",
    "corporate issuer":        "Corporate Issuers",
    "derivatives":             "Derivatives",
    "economics":               "Economics",
    "equity investments":      "Equity Investments",
    "equity":                  "Equity Investments",
    "ethics & professional standards": "Ethics & Professional Standards",
    "ethics and professional standards": "Ethics & Professional Standards",
    "ethical and professional standards": "Ethics & Professional Standards",
    "ethics":                  "Ethics & Professional Standards",
    "fixed income":            "Fixed Income",
    "financial statement analysis": "Financial Statement Analysis",
    "financial reporting and analysis": "Financial Statement Analysis",
    "fsa":                     "Financial Statement Analysis",
    "portfolio management":    "Portfolio Management",
    "portfolio":               "Portfolio Management",
    "quantitative methods":    "Quantitative Methods",
    "quantitative":            "Quantitative Methods",
    "quant":                   "Quantitative Methods",
}

def _norm_topic(raw: str) -> str:
    if not raw:
        return ""
    s = raw.lower().strip()
    s = _TOPIC_STRIP.sub("", s).strip()
    for k, v in TOPIC_MAP.items():
        if k in s:
            return v
    return raw.strip()

# ── Build unified Q+A list from QB cache ─────────────────────────────────────
def build_qb_qa(cache_data: list) -> list:
    """
    Joins question pages + answer pages by (normalized_topic, n).
    Returns list of {stem, A, B, C, correct, topic, expl}.
    """
    q_pages = [p for p in cache_data if p.get("page_type") == "questions"]
    a_pages = [p for p in cache_data if p.get("page_type") == "answers"]

    # Build Q map: (norm_topic, n) -> {stem, A, B, C}
    q_map = {}
    # Also track topic progression for pages with topic=None
    last_q_topic = ""
    for p in sorted(q_pages, key=lambda x: x.get("page_idx", 0)):
        t = _norm_topic(p.get("topic") or last_q_topic)
        if p.get("topic"):
            last_q_topic = p["topic"]
        for item in p.get("items") or []:
            n = item.get("n")
            if n is not None:
                key = (t, n)
                q_map[key] = {
                    "stem": (item.get("stem") or "").strip(),
                    "A":    (item.get("A") or "").strip(),
                    "B":    (item.get("B") or "").strip(),
                    "C":    (item.get("C") or "").strip(),
                    "topic": t,
                }

    # Build A map: (norm_topic, n) -> {correct, expl}
    a_map = {}
    last_a_topic = ""
    for p in sorted(a_pages, key=lambda x: x.get("page_idx", 0)):
        t = _norm_topic(p.get("topic") or last_a_topic)
        if p.get("topic"):
            last_a_topic = p["topic"]
        for item in p.get("items") or []:
            n = item.get("n")
            if n is not None:
                a_map[(t, n)] = {
                    "correct": (item.get("correct") or "").upper().strip(),
                    "expl":    item.get("expl", ""),
                }

    # Join
    result = []
    for key, qdata in q_map.items():
        adata = a_map.get(key)
        if not adata:
            # Try topic-agnostic lookup (n only, if topic mismatch)
            matches = [(k, v) for k, v in a_map.items() if k[1] == key[1]]
            if len(matches) == 1:
                adata = matches[0][1]
        if adata and adata.get("correct") in ("A", "B", "C"):
            result.append({**qdata, "correct": adata["correct"], "expl": adata.get("expl", "")})

    return result

def build_mock_qa(cache_data: list) -> list:
    """Mocks cache: each item is already {stem, A, B, C, correct, topic, qnum}."""
    result = []
    for item in cache_data:
        if isinstance(item, dict) and item.get("correct") in ("A", "B", "C"):
            result.append({
                "stem":    (item.get("stem") or "").strip(),
                "A":       (item.get("A") or "").strip(),
                "B":       (item.get("B") or "").strip(),
                "C":       (item.get("C") or "").strip(),
                "correct": item["correct"].upper().strip(),
                "topic":   _norm_topic(item.get("topic") or ""),
                "expl":    item.get("expl", ""),
                "qnum":    item.get("qnum"),
            })
    return result

# ── Text normalization for matching ──────────────────────────────────────────
def _norm_text(t: str) -> str:
    if not t:
        return ""
    t = t.lower().strip()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t

def _similarity(a: str, b: str) -> float:
    na, nb = _norm_text(a), _norm_text(b)
    if not na or not nb:
        return 0.0
    # Fast prefix check
    prefix_len = min(40, len(na), len(nb))
    if na[:prefix_len] == nb[:prefix_len]:
        return 1.0
    return SequenceMatcher(None, na[:120], nb[:120]).ratio()

def find_db_matches(stem: str, db_list: list, threshold=0.82) -> list:
    """Find all DB questions matching stem above threshold. Returns sorted list."""
    if not stem:
        return []
    norm_stem = _norm_text(stem)
    if len(norm_stem) < 20:
        return []  # Too short to be reliable
    prefix = norm_stem[:60]
    results = []
    for row in db_list:
        q = _norm_text(row.get("question_en") or "")
        if not q:
            continue
        # Fast prefix check
        if q[:60] == prefix:
            results.append((1.0, row))
            continue
        # Only compute SequenceMatcher if first 20 chars overlap somewhat
        if norm_stem[:20] not in q[:80] and q[:20] not in norm_stem[:80]:
            continue
        score = SequenceMatcher(None, norm_stem[:150], q[:150]).ratio()
        if score >= threshold:
            results.append((score, row))
    # Sort by score desc
    results.sort(key=lambda x: -x[0])
    return results

# ── P2 triple-confirmation ────────────────────────────────────────────────────
def _p2_detect(explanation: str, opt_a: str, opt_b: str, opt_c: str) -> str | None:
    """
    Detect which option letter is most supported by the explanation.
    Same P2 logic as Kaplan audit: check first 50 chars of each option in explanation.
    Returns 'A', 'B', 'C' or None.
    """
    if not explanation:
        return None
    expl_low = explanation.lower()
    # First 3 sentences of explanation
    sentences = re.split(r'(?<=[.!?])\s+', explanation.strip())
    expl_short = " ".join(sentences[:3]).lower()

    hits = {}
    for letter, opt in [("A", opt_a), ("B", opt_b), ("C", opt_c)]:
        if not opt or len(opt.strip()) < 6:
            continue
        clean = re.sub(r"[^a-z0-9 ]", " ", opt.lower().strip())
        clean = re.sub(r"\s+", " ", clean).strip()
        key50 = clean[:50].rstrip()
        key30 = clean[:30].rstrip()
        if key50 in expl_short or key50 in expl_low[:400]:
            hits[letter] = 2  # strong match
        elif key30 in expl_short or key30 in expl_low[:300]:
            hits[letter] = 1  # weaker match

    if len(hits) == 1:
        return list(hits.keys())[0]
    if len(hits) > 1:
        # Return the one with highest score
        best = max(hits, key=lambda k: hits[k])
        return best  # ambiguous but return best
    return None

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Load DB dump
    print("Loading DB dump...")
    with open(DUMP_FILE, encoding="utf-8") as f:
        dump = json.load(f)
    cfa_rows = [r for r in dump if r.get("source") == "CFA_WEB"]
    print(f"CFA_WEB in DB: {len(cfa_rows)}")

    # Initialize Vision client if needed
    client = None
    if not args.skip_vision:
        if HAS_FITZ and HAS_ANTHROPIC:
            import os
            ak = os.environ.get("ANTHROPIC_API_KEY", "")
            if ak:
                client = _anthropic.Anthropic(api_key=ak)
                print("Vision client initialized.")
            else:
                print("[WARN] ANTHROPIC_API_KEY not set — skipping Vision re-extraction.")
        else:
            print("[WARN] fitz or anthropic not available — skipping Vision re-extraction.")

    # ── QB PDFs ───────────────────────────────────────────────────────────────
    QB_PDFS = [
        ("AI, Corporate, Deriv, Eco.pdf",  "AI,_Corporate,_Deriv,_Eco.json"),
        ("Equity, Ethics.pdf",              "Equity,_Ethics.json"),
        ("Fixed income, FSA.pdf",           "Fixed_income,_FSA.json"),
        ("Portfolio, Quants.pdf",           "Portfolio,_Quants.json"),
    ]

    all_qa = []  # unified list across all sources

    print("\n=== QB PDFs ===")
    for pdf_name, cache_name in QB_PDFS:
        cache_path = CACHE_QB / cache_name
        if _is_cache_valid(cache_path):
            print(f"[cache OK] {pdf_name}")
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        elif client:
            pdf_path = BASE_QB / pdf_name
            if not pdf_path.exists():
                print(f"[SKIP] PDF not found: {pdf_name}")
                continue
            # Delete invalid cache and re-extract
            if cache_path.exists():
                cache_path.unlink()
            data = extract_qb_pdf(pdf_path, cache_path, client)
        else:
            print(f"[SKIP] No vision client and cache invalid: {pdf_name}")
            continue
        qa = build_qb_qa(data)
        print(f"  -> {len(qa)} Q+A pairs from {cache_name}")
        all_qa.extend(qa)

    # ── Mock PDFs ─────────────────────────────────────────────────────────────
    MOCK_ANS_PDFS = [
        ("MOCK 1 SS1 ANS.pdf",     "MOCK_1_SS1_ANS.json"),
        ("MOCK 1 SS2 ANS.pdf",     "MOCK_1_SS2_ANS.json"),
        ("MOCK 2 SS1 ANS (1).pdf", "MOCK_2_SS1_ANS_1.json"),
        ("MOCK 2 SS2 ANS.pdf",     "MOCK_2_SS2_ANS.json"),
        ("MOCK 3 SS1 ANS.pdf",     "MOCK_3_SS1_ANS.json"),
        ("MOCK 3 SS2 ANS.pdf",     "MOCK_3_SS2_ANS.json"),
        ("MOCK 4 SS1 ANS.pdf",     "MOCK_4_SS1_ANS.json"),
        ("MOCK 4 SS2 ANS.pdf",     "MOCK_4_SS2_ANS.json"),
        ("MOCK 5 SS1 ANS.pdf",     "MOCK_5_SS1_ANS.json"),
        ("MOCK 5 SS2 ANS.pdf",     "MOCK_5_SS2_ANS.json"),
        ("MOCK 6 SS1 ANS (2).pdf", "MOCK_6_SS1_ANS_2.json"),
        ("MOCK 6 SS2 ANS.pdf",     "MOCK_6_SS2_ANS.json"),
    ]

    print("\n=== Mock ANS PDFs ===")
    for pdf_name, cache_name in MOCK_ANS_PDFS:
        cache_path = CACHE_MOCKS / cache_name
        if _is_cache_valid(cache_path):
            print(f"[cache OK] {pdf_name}")
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        elif client:
            pdf_path = BASE_MOCKS / pdf_name
            if not pdf_path.exists():
                # Try alternate filenames
                alt = list(BASE_MOCKS.glob(f"*{pdf_name.split()[1]}*ANS*.pdf"))
                if alt:
                    pdf_path = alt[0]
                else:
                    print(f"[SKIP] PDF not found: {pdf_name}")
                    continue
            if cache_path.exists():
                cache_path.unlink()
            data = extract_mock_pdf(pdf_path, cache_path, client)
        else:
            print(f"[SKIP] No vision client and cache invalid: {pdf_name}")
            continue
        qa = build_mock_qa(data)
        print(f"  -> {len(qa)} Q+A pairs from {cache_name}")
        all_qa.extend(qa)

    print(f"\nTotal Q+A pairs from all sources: {len(all_qa)}")

    # ── Match to DB ───────────────────────────────────────────────────────────
    print("\n=== Matching to DB ===")

    # Step 1: Build per-DB-ID candidate map
    # For each DB question, collect all cache entries that match it
    # {db_id: [(sim, cache_ans, expl, cache_qa), ...]}
    id_candidates: dict = {}

    for qa in all_qa:
        db_matches = find_db_matches(qa["stem"], cfa_rows)
        if not db_matches:
            continue
        # Only use the best match IF it's clearly better than the second (ratio > 0.05)
        if len(db_matches) >= 2 and (db_matches[0][0] - db_matches[1][0]) < 0.05:
            # Ambiguous - two equally good matches, skip
            continue
        best_sim, best_row = db_matches[0]
        uid = best_row["id"]
        if uid not in id_candidates:
            id_candidates[uid] = []
        id_candidates[uid].append((best_sim, qa["correct"].upper().strip(), qa.get("expl",""), qa, best_row))

    print(f"Unique DB questions matched: {len(id_candidates)}")
    unmatched_count = len(all_qa) - sum(len(v) for v in id_candidates.values())

    matched, mismatches, ambiguous = [], [], []

    for uid, candidates in id_candidates.items():
        # Use the candidate with the highest similarity
        candidates.sort(key=lambda x: -x[0])
        best_sim, cache_ans, cache_expl, qa, row = candidates[0]

        # Check if multiple cache entries agree
        cache_answers = [c[1] for c in candidates]
        majority = max(set(cache_answers), key=cache_answers.count)
        agreement = cache_answers.count(majority) / len(cache_answers)

        db_ans = (row.get("correct_answer") or "").upper().strip()
        cache_ans_final = majority  # use majority vote

        if db_ans == cache_ans_final:
            matched.append({"id": uid, "stored": db_ans, "cached": cache_ans_final, "sim": best_sim})
            continue

        if cache_ans_final not in ("A", "B", "C"):
            continue

        # P2 triple-confirmation on DB explanation_en
        expl_en = row.get("explanation_en") or ""
        opt_a   = row.get("option_a") or ""
        opt_b   = row.get("option_b") or ""
        opt_c   = row.get("option_c") or ""
        p2_from_expl = _p2_detect(expl_en, opt_a, opt_b, opt_c)

        confidence = "HIGH" if agreement >= 0.8 else "MEDIUM" if agreement >= 0.5 else "LOW"

        result = {
            "id":          uid,
            "q_text":      (row.get("question_en") or "")[:80],
            "stored":      db_ans,
            "cached":      cache_ans_final,
            "cache_votes": f"{cache_answers.count(cache_ans_final)}/{len(cache_answers)}",
            "p2_expl":     p2_from_expl or "None",
            "agreement":   round(agreement, 2),
            "confidence":  confidence,
            "sim":         round(best_sim, 3),
            "expl_db":     expl_en[:150],
            "topic":       qa.get("topic", ""),
        }

        if p2_from_expl is None:
            # No P2 signal — use cache if agreement is high and sim is perfect
            if agreement >= 0.8 and best_sim >= 0.99:
                result["confidence"] = "MEDIUM-CACHE"
                mismatches.append(result)
            else:
                ambiguous.append(result)
        elif p2_from_expl == cache_ans_final:
            # P2 from explanation confirms cached answer → genuine mismatch
            result["confidence"] = "HIGH-CONFIRMED"
            mismatches.append(result)
        elif p2_from_expl == db_ans:
            # P2 confirms stored answer → false positive, skip
            matched.append(result)
        else:
            # P2 suggests a third answer → ambiguous
            ambiguous.append(result)

    print(f"Matched (correct or false positive confirmed): {len(matched)}")
    print(f"Genuine mismatches: {len(mismatches)}")
    print(f"  - HIGH-CONFIRMED (P2 supports cached): {sum(1 for m in mismatches if m.get('confidence')=='HIGH-CONFIRMED')}")
    print(f"  - MEDIUM-CACHE (no P2, high agreement): {sum(1 for m in mismatches if 'CACHE' in m.get('confidence',''))}")
    print(f"Ambiguous (skipped): {len(ambiguous)}")
    print(f"Unmatched cache entries: {unmatched_count}")

    # Save full audit
    with open(OUT_FULL, "w", encoding="utf-8") as f:
        json.dump({
            "total_qa": len(all_qa),
            "matched": len(matched),
            "mismatches": mismatches,
            "ambiguous": ambiguous,
            "unmatched": unmatched_count,
        }, f, indent=2, ensure_ascii=False)

    if not mismatches:
        print("\nNo confirmed mismatches — CFA_WEB answers look correct.")
        return

    print(f"\n=== {len(mismatches)} confirmed mismatches ===")
    for m in mismatches:
        print(f"  {m['id'][:8]}  stored={m['stored']}  cached={m['cached']}  conf={m['confidence']}  votes={m['cache_votes']}")
        print(f"    Q: {m['q_text']}")
        print(f"    P2_expl={m['p2_expl']}  DB_expl: {m['expl_db'][:100]}")

    # Save fixes
    with open(OUT_FIXES, "w", encoding="utf-8") as f:
        json.dump(mismatches, f, indent=2, ensure_ascii=False)
    print(f"\nFixes -> {OUT_FIXES}")

    if args.dry_run:
        print("[DRY RUN] PS1 not generated.")
        return

    # Generate PS1
    lines = [
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8",
        "$headers = @{",
        f'    "apikey"        = "{API_KEY}"',
        f'    "Authorization" = "Bearer {API_KEY}"',
        '    "Content-Type"  = "application/json"',
        '    "Prefer"        = "return=minimal"',
        "}",
        "$ok = 0; $err = 0",
        "",
    ]
    for m in mismatches:
        url  = f"{SUPABASE_URL}?id=eq.{m['id']}"
        desc = m["q_text"][:60].replace("'", "''").encode("ascii", errors="replace").decode()
        conf = m.get("confidence","")
        votes = m.get("cache_votes","")
        lines.append(f"# {m['stored']}->{m['cached']}  conf={conf}  votes={votes}  {desc}")
        lines.append(f'$body = \'{{"correct_answer":"{m["cached"]}"}}\' ')
        lines.append("try {")
        lines.append(f'    Invoke-WebRequest -Uri "{url}" -Method PATCH -Headers $headers -Body $body -SkipCertificateCheck -UseBasicParsing | Out-Null')
        lines.append(f'    $ok++; Write-Host "OK  {m["id"][:8]}  {m["stored"]}->{m["cached"]}"')
        lines.append("} catch {")
        lines.append(f'    $err++; Write-Host "ERR {m["id"][:8]}: $_"')
        lines.append("}")
        lines.append("")
    lines += ['Write-Host ""', 'Write-Host "Done: $ok OK, $err errors"']
    with open(OUT_PS1, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"PS1  -> {OUT_PS1}")
    print(f"\nApply with: pwsh -File \"{OUT_PS1}\"")

if __name__ == "__main__":
    main()
