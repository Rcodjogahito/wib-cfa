"""Apply confirmed corrections from a batch results file to Supabase.

Input: a results JSON (list of dicts) with at least:
  {"id": ..., "verdict": "ok"|"correct_answer_wrong"|"explanation_wrong"|
   "formatting_missing"|"wrong_page"|"unclear",
   "field": "correct_answer"|"explanation_en"|"question_en" (if a correction),
   "new_value": "...", "evidence": "..."}

Only rows with a non-"ok"/"unclear"/"wrong_page" verdict AND a non-empty new_value
are patched. Pre-checks current DB value, PATCHes, then re-fetches to confirm.

Usage: python scripts/_fullbank_apply_corrections.py <results_file.json>
"""
import json
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
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
    if len(sys.argv) < 2:
        print("Usage: python scripts/_fullbank_apply_corrections.py <results_file.json>")
        sys.exit(1)
    results_path = Path(sys.argv[1])
    results = json.loads(results_path.read_text(encoding="utf-8"))

    secrets = load_secrets(Path(".streamlit/secrets.toml"))["supabase"]
    url = secrets["SUPABASE_URL"]
    key = secrets["SUPABASE_SERVICE_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    to_patch = [r for r in results if r.get("verdict") not in (None, "ok", "unclear", "wrong_page") and r.get("new_value")]
    print(f"{len(results)} verdicts, {len(to_patch)} corrections to apply")

    applied, skipped = [], []
    for r in to_patch:
        qid, field, new_val = r["id"], r["field"], r["new_value"]
        cur = requests.get(f"{url}/rest/v1/questions", headers=headers,
                            params={"id": f"eq.{qid}", "select": field}, timeout=30).json()
        if not cur:
            print(f"  [SKIP] {qid} not found in DB")
            skipped.append(qid)
            continue
        before = cur[0].get(field)
        for attempt in range(4):
            try:
                pr = requests.patch(f"{url}/rest/v1/questions", headers=dict(headers, Prefer="return=minimal"),
                                     params={"id": f"eq.{qid}"}, json={field: new_val}, timeout=30)
                pr.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if attempt == 3:
                    print(f"  [FAIL-NETWORK] {qid} field={field}: {e}")
                    skipped.append(qid)
                    pr = None
                    break
        if pr is None:
            continue
        for attempt in range(4):
            try:
                after_r = requests.get(f"{url}/rest/v1/questions", headers=headers,
                                        params={"id": f"eq.{qid}", "select": field}, timeout=30).json()
                break
            except requests.exceptions.RequestException:
                if attempt == 3:
                    after_r = []
        after = after_r[0].get(field) if after_r else None
        ok = after == new_val
        print(f"  {'[OK]' if ok else '[FAIL]'} {qid} field={field} before={str(before)[:40]!r} -> after={str(after)[:40]!r}")
        applied.append({"id": qid, "field": field, "verified": ok})

    print(f"Applied: {len(applied)}, verified OK: {sum(1 for a in applied if a['verified'])}, skipped: {len(skipped)}")
    out = results_path.with_name(results_path.stem + "_applied.json")
    out.write_text(json.dumps(applied, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
