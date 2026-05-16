#!/usr/bin/env python3
"""
audit_questions.py — Quick DB audit: missing tables, missing explanations, per source.

Run: python scripts/audit_questions.py
"""
import re
import sys
from pathlib import Path
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(Path(__file__).parent.parent))

SECRETS_PATH = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
MIN_EXPL_LEN = 50

MISSING_RE = re.compile(
    r"the following\s+[\w\s]{1,40}\s*:\s*"
    r"(?:Based|If|Assuming|Which|The company|The analyst|An analyst|Using|From|According|"
    r"Given|Determine|Calculate|What|Over the|The fund|A fund|The portfolio|An investor|"
    r"The investor|Select|Identify|Choose|Classify)",
    re.IGNORECASE,
)


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


def main():
    secrets = load_secrets(SECRETS_PATH)
    from supabase import create_client
    sb = create_client(secrets["supabase"]["SUPABASE_URL"], secrets["supabase"]["SUPABASE_SERVICE_KEY"])

    page_size = 1000
    offset = 0
    total = 0
    missing_table: list[dict] = []
    missing_expl: list[dict] = []
    both: list[dict] = []

    print("Scanning all questions...", flush=True)
    while True:
        rows = sb.table("questions").select(
            "id,source,topic,question_en,explanation_en"
        ).range(offset, offset + page_size - 1).execute()
        if not rows.data:
            break
        for q in rows.data:
            total += 1
            qen = q.get("question_en", "") or ""
            expl = (q.get("explanation_en") or "").strip()
            has_table_ref = bool(MISSING_RE.search(qen)) and "|" not in qen
            has_no_expl = len(expl) < MIN_EXPL_LEN
            if has_table_ref and has_no_expl:
                both.append(q)
            elif has_table_ref:
                missing_table.append(q)
            elif has_no_expl:
                missing_expl.append(q)
        offset += page_size
        if len(rows.data) < page_size:
            break

    print(f"\n{'='*55}")
    print(f"  AUDIT RAPPORT — {total} questions total")
    print(f"{'='*55}")

    ok = total - len(missing_table) - len(missing_expl) - len(both)
    print(f"  ✅ Complètes (table + explication)  : {ok:>5}")
    print(f"  ⚠️  Table manquante seulement        : {len(missing_table):>5}")
    print(f"  ⚠️  Explication manquante seulement  : {len(missing_expl):>5}")
    print(f"  ❌ Les deux manquants               : {len(both):>5}")
    print(f"{'='*55}\n")

    all_missing_expl = missing_expl + both
    all_missing_table = missing_table + both

    if all_missing_expl:
        print("Explications manquantes par source :")
        src_cnt = Counter(q["source"] for q in all_missing_expl)
        for src, cnt in sorted(src_cnt.items()):
            print(f"  {src:<15} {cnt}")
        print(f"  {'TOTAL':<15} {sum(src_cnt.values())}")
        print()

    if all_missing_table:
        print("Tables manquantes par source :")
        src_cnt = Counter(q["source"] for q in all_missing_table)
        for src, cnt in sorted(src_cnt.items()):
            print(f"  {src:<15} {cnt}")
        print(f"  {'TOTAL':<15} {sum(src_cnt.values())}")
        print()

    if all_missing_expl:
        print("Détail explications manquantes :")
        for q in all_missing_expl[:20]:
            print(f"  [{q['source']:<12}] {(q.get('topic') or '')[:25]:25s} | {(q.get('question_en') or '')[:55]}")
        if len(all_missing_expl) > 20:
            print(f"  ... et {len(all_missing_expl) - 20} autres")


if __name__ == "__main__":
    main()
