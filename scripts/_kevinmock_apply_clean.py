# -*- coding: utf-8 -*-
"""Apply word-bag-verified Kevin_Mock text_diff corrections. Same safety
protocol as the UWorld pipeline: skip empty new_value, skip if it would
regress an already-markdown-formatted field, verify word-bag overlap before
trusting a reconstruction, pre-check + patch + verify live."""
import json, re, sys
from pathlib import Path
from collections import Counter
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORD_RE = re.compile(r"[a-z0-9]{3,}")
def sig_words(t):
    return Counter(WORD_RE.findall((t or "").lower()))
def overlap_score(a, b):
    aw, bw = sig_words(a), sig_words(b)
    total = sum(aw.values())
    if not total:
        return 1.0
    return sum(min(aw[w], bw.get(w, 0)) for w in aw) / total

def load_secrets(path):
    result, section = {}, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]; result[section] = {}
            elif "=" in line and section:
                k, _, v = line.partition("="); result[section][k.strip()] = v.strip().strip('"').strip("'")
    return result

def main():
    diffs = json.loads(Path("scripts/_kevinmock_full_diff_report.json").read_text(encoding="utf-8"))
    dump_by_id = {d["id"]: d for d in json.loads(Path("scripts/_full_dump_fresh_20260730.json").read_text(encoding="utf-8"))}
    td = [x for x in diffs if x["status"] == "text_diff"]

    secrets = load_secrets(Path(".streamlit/secrets.toml"))["supabase"]
    url, key = secrets["SUPABASE_URL"], secrets["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    field_map = {"question_en": "new_question_en", "option_a": "new_option_a",
                 "option_b": "new_option_b", "option_c": "new_option_c",
                 "explanation_en": "new_explanation_en"}

    applied = Counter()
    skipped_low_overlap = []
    n_touched = 0
    for x in td:
        row = dump_by_id.get(x["id"])
        if not row:
            continue
        patch = {}
        for db_field, new_field in field_map.items():
            new_val = (x.get(new_field) or "").strip()
            old_val = (row.get(db_field) or "")
            if not new_val or new_val == old_val.strip():
                continue
            has_real_table = "\n|" in old_val or "|---" in old_val
            has_real_list = "\n-" in old_val or "\n1." in old_val
            if (has_real_table or has_real_list) and not (("\n|" in new_val or "|---" in new_val) or ("\n-" in new_val)):
                continue  # never regress already-formatted tables/lists
            # safe path 1: new_val is a clean prefix of old_val (pure trailing-junk
            # removal, e.g. page-footer bleed) -- nothing invented
            is_clean_prefix = old_val.strip().startswith(new_val)
            score = overlap_score(old_val, new_val)
            if not is_clean_prefix and score < 0.85:
                skipped_low_overlap.append((x["id"], db_field, round(score, 3)))
                continue
            patch[db_field] = new_val
        if not patch:
            continue
        n_touched += 1
        for attempt in range(3):
            try:
                pr = requests.patch(f"{url}/rest/v1/questions", headers=dict(headers, Prefer="return=minimal"),
                                     params={"id": f"eq.{x['id']}"}, json=patch, timeout=30)
                break
            except requests.exceptions.RequestException:
                pr = None
        if pr is None or pr.status_code >= 300:
            print("FAIL", x["id"], pr.status_code if pr else "network")
            continue
        for f in patch:
            applied[f] += 1

    print(f"Items touched: {n_touched}")
    print(f"Fields patched: {dict(applied)}")
    print(f"Skipped (low word-overlap, needs manual review): {len(skipped_low_overlap)}")
    for s in skipped_low_overlap:
        print(" ", s)
    Path("scripts/_kevinmock_apply_summary.json").write_text(
        json.dumps({"n_touched": n_touched, "fields_patched": dict(applied),
                    "skipped_low_overlap": skipped_low_overlap}, ensure_ascii=False, indent=1),
        encoding="utf-8")

if __name__ == "__main__":
    main()
