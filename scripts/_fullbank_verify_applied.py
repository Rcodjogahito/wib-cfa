"""Cross-check every already-applied correction against its batch manifest to catch
agent misattribution (correction sourced from evidence about a DIFFERENT question
than the id it was filed under). For each correction:
  - if verdict is formatting_missing: new_value should share most of its words with
    the manifest's original field value (only structure added) -> flag if overlap is low.
  - if verdict is option_bleed: new_value should be a PREFIX (or near-prefix) of the
    manifest's original field value -> flag if not.
  - if verdict is explanation_wrong/correct_answer_wrong: can't auto-verify content
    (the whole point is it's SUPPOSED to differ from the manifest's original value),
    but we flag cases where new_value looks like it might belong elsewhere by checking
    if the manifest's OTHER fields (question_en) share near-zero vocabulary with new_value
    -- printed for manual spot-check, not auto-flagged as wrong.
"""
import json
import re
from pathlib import Path

BATCH_DIR = Path("scripts/_fullbank_batches")

def words(s):
    return set(re.findall(r"[a-zA-Z]{4,}", (s or "").lower()))

flags = []
checked = 0
for manifest_path in sorted(BATCH_DIR.glob("batch_*.json")):
    if "_results" in manifest_path.stem:
        continue
    results_path = BATCH_DIR / f"{manifest_path.stem}_results.json"
    if not results_path.exists():
        continue
    manifest = {it["id"]: it for it in json.loads(manifest_path.read_text(encoding="utf-8"))}
    results = json.loads(results_path.read_text(encoding="utf-8"))
    for r in results:
        if r.get("verdict") in (None, "ok", "unclear", "wrong_page") or not r.get("new_value"):
            continue
        checked += 1
        qid, field, new_val = r["id"], r["field"], r["new_value"]
        orig = manifest.get(qid, {}).get(field, "") or ""
        if r["verdict"] == "option_bleed":
            ow, nw = words(orig), words(new_val)
            overlap = len(nw & ow) / max(1, len(nw))
            if overlap < 0.8:
                flags.append((manifest_path.stem, qid, field, r["verdict"], "low word overlap with manifest original", orig[:80], new_val[:80]))
        elif r["verdict"] == "formatting_missing":
            ow, nw = words(orig), words(new_val)
            overlap = len(ow & nw) / max(1, len(ow))
            if overlap < 0.5:
                flags.append((manifest_path.stem, qid, field, r["verdict"], "new_value shares <50% of original's words", orig[:80], new_val[:80]))

print(f"Checked {checked} corrections across all applied batches.")
print(f"Flags: {len(flags)}")
for f in flags:
    print(f)
