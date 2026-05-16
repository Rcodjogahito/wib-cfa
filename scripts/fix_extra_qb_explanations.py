#!/usr/bin/env python3
"""
Fix Extra_QB explanations: the original import script stored wrong/scrambled explanations.
This script re-parses EXTRA 700 MCQs.pdf to extract verbatim explanations,
then updates Supabase using multi-tier stem matching.

Usage: python scripts/fix_extra_qb_explanations.py [--dry-run]
"""
import sys, re, argparse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import pdfplumber

BASE = Path(r"D:\CLAUDE\Projet CFA\CFA L1")
EXTRA_PDF = BASE / "7. EXTRA QB-700MCQs" / "EXTRA 700 MCQs.pdf"

SECTION_MAP = {
    r"ethical\s+and\s+professional": "Ethics & Professional Standards",
    r"ethics":                        "Ethics & Professional Standards",
    r"quantitative\s+method":         "Quantitative Methods",
    r"quant":                         "Quantitative Methods",
    r"economic":                      "Economics",
    r"financial\s+report":            "Financial Statement Analysis",
    r"financial\s+statement":         "Financial Statement Analysis",
    r"fsa":                           "Financial Statement Analysis",
    r"corporate\s+(finance|issuer)":  "Corporate Issuers",
    r"equity\s+invest":               "Equity Investments",
    r"equity":                        "Equity Investments",
    r"derivative":                    "Derivatives",
    r"fixed\s+income":                "Fixed Income",
    r"alternative":                   "Alternative Investments",
    r"portfolio":                     "Portfolio Management",
}


def _match_section(line: str) -> str:
    low = line.lower()
    for pattern, topic in SECTION_MAP.items():
        if re.search(pattern, low):
            return topic
    return None


def _de_triple(s: str) -> str:
    if not s or len(s) < 9:
        return s
    sample = s[:60].replace(" ", "")
    if not sample:
        return s
    triples = sum(1 for i in range(0, len(sample) - 2, 3)
                  if sample[i] == sample[i + 1] == sample[i + 2])
    if triples > 0 and triples >= len(sample) // 6:
        return re.sub(r"(.)\1\1", r"\1", s)
    return s


def _norm(text: str, length: int) -> str:
    """Normalize: lowercase, collapse whitespace, truncate."""
    return re.sub(r"\s+", " ", (text or "").lower().strip())[:length]


def _clean_expl(text: str) -> str:
    text = text.replace("", "•").replace("", "-").replace("", "=")
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\d{1,3}\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def parse_questions_from_pdf() -> dict:
    """Returns {(topic, qnum): stem_text}"""
    with pdfplumber.open(EXTRA_PDF) as pdf:
        q_parts = [pdf.pages[pi].extract_text() or "" for pi in range(0, 127)]
    q_text = "\n".join(q_parts)
    q_lines = q_text.split("\n")

    stem_map = {}
    current_topic = "Ethics & Professional Standards"
    i = 0
    while i < len(q_lines):
        line = q_lines[i].strip()
        if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", line) and not re.match(r"^\d", line):
            t = _match_section(line)
            if t:
                current_topic = t
            i += 1
            continue
        m = re.match(r"^(\d+)\.\s+(.+)", line)
        if m:
            qnum = int(m.group(1))
            stem_parts = [m.group(2)]
            i += 1
            while i < len(q_lines):
                nxt = q_lines[i].strip()
                if re.match(r"^[A-C]\.\s+", nxt):
                    break
                if re.match(r"^\d+\.\s+\S", nxt):
                    break
                if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", nxt) and _match_section(nxt):
                    break
                stem_parts.append(nxt)
                i += 1
            stem = " ".join(s for s in stem_parts if s).strip()
            key = (current_topic, qnum)
            if key not in stem_map:
                stem_map[key] = stem
        else:
            i += 1
    return stem_map


def parse_explanations_from_pdf() -> dict:
    """Returns {(topic, qnum): {"correct": "A/B/C", "expl": "..."}}"""
    TOPIC_MARKER = "\x00TOPIC\x00"
    pages_data = []
    with pdfplumber.open(EXTRA_PDF) as pdf:
        sol_topic = "Ethics & Professional Standards"
        for pi in range(127, min(214, len(pdf.pages))):
            raw = pdf.pages[pi].extract_text() or ""
            text = _de_triple(raw)
            for ln in text.split("\n"):
                ln = ln.strip()
                if re.match(r"^[A-Z][A-Z\s&,\-/]{4,}$", ln) and not re.match(r"^\d", ln):
                    t = _match_section(ln)
                    if t:
                        sol_topic = t
                        break
            pages_data.append((pi, sol_topic, text))

    chunks = []
    prev_topic = None
    for _, topic, text in pages_data:
        if topic != prev_topic:
            chunks.append(f"{TOPIC_MARKER}{topic}{TOPIC_MARKER}")
            prev_topic = topic
        chunks.append(text)
    full_text = "\n".join(chunks)

    topic_blocks = re.split(r"\x00TOPIC\x00([^\x00]+)\x00TOPIC\x00", full_text)
    results = {}
    i = 1
    while i < len(topic_blocks) - 1:
        topic = topic_blocks[i].strip()
        block = topic_blocks[i + 1]
        i += 2
        ans_pattern = re.compile(r"(\d{1,3})\.\s+Answer\s*[=:]\s*([A-C])\b", re.IGNORECASE)
        matches = list(ans_pattern.finditer(block))
        for j, m in enumerate(matches):
            qnum = int(m.group(1))
            letter = m.group(2).upper()
            expl_start = m.end()
            expl_end = matches[j + 1].start() if j + 1 < len(matches) else len(block)
            expl = _clean_expl(block[expl_start:expl_end])
            key = (topic, qnum)
            if key not in results:
                results[key] = {"correct": letter, "expl": expl}
    return results


def load_secrets():
    p = Path(".streamlit/secrets.toml")
    result = {}; section = None
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]; result[section] = {}
            elif "=" in line and section:
                k, _, v = line.partition("=")
                result[section][k.strip()] = v.strip().strip('"').strip("'")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Parsing question stems from PDF …")
    stem_map = parse_questions_from_pdf()
    print(f"  Found {len(stem_map)} question stems")

    print("Extracting explanations from solutions section …")
    expl_map = parse_explanations_from_pdf()
    non_empty = sum(1 for d in expl_map.values() if d["expl"])
    print(f"  Found {len(expl_map)} answer entries, {non_empty} with explanation text")

    # Merge: (topic, qnum) → {stem, correct, expl}
    merged = {}
    for key, stem in stem_map.items():
        if key in expl_map and expl_map[key]["expl"]:
            merged[key] = {"stem": stem, **expl_map[key]}
    print(f"  Merged {len(merged)} questions with both stem and explanation")

    # Build lookup tables for multi-tier matching
    # norm_key → (topic, qnum, stem, correct, expl)
    pdf_by_norm = {}
    for (topic, qnum), data in merged.items():
        for length in [120, 80, 60, 40, 25]:
            k = _norm(data["stem"], length)
            if k and k not in pdf_by_norm:
                pdf_by_norm[(length, k)] = (topic, qnum, data)

    if not args.dry_run:
        secrets = load_secrets()
        from supabase import create_client
        sb = create_client(secrets["supabase"]["SUPABASE_URL"],
                           secrets["supabase"]["SUPABASE_SERVICE_KEY"])

    print("Fetching Extra_QB questions from Supabase …")
    if not args.dry_run:
        resp = sb.table("questions").select("id,question_en,topic,explanation_en").eq("source", "Extra_QB").execute()
        db_questions = resp.data
    else:
        # For dry run, load DB to count matches
        secrets = load_secrets()
        from supabase import create_client
        sb = create_client(secrets["supabase"]["SUPABASE_URL"],
                           secrets["supabase"]["SUPABASE_SERVICE_KEY"])
        resp = sb.table("questions").select("id,question_en,topic,explanation_en").eq("source", "Extra_QB").execute()
        db_questions = resp.data
    print(f"  {len(db_questions)} Extra_QB records in DB")

    # Match DB records to PDF merged records
    updates = []
    matched = 0
    no_match = 0
    for db_rec in db_questions:
        db_stem = db_rec.get("question_en") or ""
        found = None
        for length in [120, 80, 60, 40, 25]:
            k = _norm(db_stem, length)
            if (length, k) in pdf_by_norm:
                found = pdf_by_norm[(length, k)]
                break
        if found:
            _, _, data = found
            updates.append({"id": db_rec["id"], "explanation_en": data["expl"]})
            matched += 1
        else:
            no_match += 1

    print(f"\nMatch results: {matched} matched, {no_match} not matched")

    if args.dry_run:
        print("\n[DRY RUN] Sample updates:")
        for u in updates[:5]:
            db_rec = next(q for q in db_questions if q["id"] == u["id"])
            print(f'  Q: {(db_rec["question_en"] or "")[:70]}')
            print(f'  → expl[{len(u["explanation_en"])}]: {u["explanation_en"][:100]}')
            print()
        print(f"Would update {len(updates)} records")
        if no_match > 0:
            print(f"\nWould leave {no_match} records unchanged (no match in PDF)")
        return

    # Apply updates
    updated = 0
    for i in range(0, len(updates), 50):
        batch = updates[i:i + 50]
        for upd in batch:
            sb.table("questions").update(
                {"explanation_en": upd["explanation_en"]}
            ).eq("id", upd["id"]).execute()
        updated += len(batch)
        print(f"  Updated {min(i + 50, len(updates))}/{len(updates)}")

    print(f"\nDONE — Updated {updated} Extra_QB explanations")


if __name__ == "__main__":
    main()
