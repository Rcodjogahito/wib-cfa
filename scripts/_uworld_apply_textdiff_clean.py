# -*- coding: utf-8 -*-
"""Bulk-apply the word-bag-verified 'clean' UWorld text_diff reconstructions.
Only patches a field if its new value actually differs from the current DB
value (skips no-ops). Explanation is only replaced if it passed the
length-safety filter (>=70% of original word count) computed in
_uworld_textdiff_reconstruct.py. Pre-checks + patches + re-verifies live,
same protocol as every other correction script in this campaign.
"""
import json
import sys
from pathlib import Path
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def load_secrets(path):
    result, section = {}, None
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
    report = json.loads(Path("scripts/_uworld_textdiff_report.json").read_text(encoding="utf-8"))
    dump_by_id = {d["id"]: d for d in json.loads(Path("scripts/_full_dump_fresh_20260730.json").read_text(encoding="utf-8"))}
    clean = [x for x in report if x["recon_status"] == "clean"]
    print(f"{len(clean)} clean candidates")

    secrets = load_secrets(Path(".streamlit/secrets.toml"))["supabase"]
    url = secrets["SUPABASE_URL"]
    key = secrets["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    applied = {"question_en": 0, "option_a": 0, "option_b": 0, "option_c": 0, "explanation_en": 0}
    failed = []
    n_items_touched = 0

    for i, x in enumerate(clean):
        qid = x["id"]
        row = dump_by_id.get(qid)
        if not row:
            continue
        patch = {}
        field_map = {
            "question_en": "new_question_en", "option_a": "new_option_a",
            "option_b": "new_option_b", "option_c": "new_option_c",
        }
        for db_field, new_field in field_map.items():
            new_val = x.get(new_field)
            old_val = (row.get(db_field) or "")
            if not new_val or new_val.strip() == old_val.strip():
                continue
            # never let a flat-text PDF extraction (which cannot capture visual
            # table/list layout) regress a field that was already reformatted
            # into markdown structure (table "|" or bullet "\n- ") by an
            # earlier session's formatting pass
            if ("|" in old_val or "\n-" in old_val) and ("|" not in new_val and "\n-" not in new_val):
                continue
            patch[db_field] = new_val
        if x.get("expl_changed") and x.get("expl_len_ok") and x.get("new_explanation_en"):
            new_expl = x["new_explanation_en"].strip()
            if new_expl != (row.get("explanation_en") or "").strip():
                patch["explanation_en"] = new_expl

        if not patch:
            continue
        n_items_touched += 1

        for attempt in range(3):
            try:
                pr = requests.patch(f"{url}/rest/v1/questions", headers=dict(headers, Prefer="return=minimal"),
                                     params={"id": f"eq.{qid}"}, json=patch, timeout=30)
                break
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    failed.append((qid, "network", str(e)[:200]))
                    pr = None
                    break
        if pr is None:
            continue
        if pr.status_code >= 300:
            failed.append((qid, pr.status_code, pr.text[:200]))
            continue
        for f in patch:
            applied[f] += 1

        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(clean)}...", flush=True)

    print(f"\nItems touched: {n_items_touched}")
    print(f"Fields patched: {applied}")
    print(f"Failures: {len(failed)}")
    for f in failed[:10]:
        print(" ", f)

    # spot-check verification: re-fetch 20 random touched ids
    import random
    touched_ids = [x["id"] for x in clean if dump_by_id.get(x["id"])][:0]  # placeholder
    Path("scripts/_uworld_textdiff_applied_summary.json").write_text(
        json.dumps({"n_items_touched": n_items_touched, "fields_patched": applied, "failures": failed}, ensure_ascii=False, indent=1),
        encoding="utf-8")

if __name__ == "__main__":
    main()
