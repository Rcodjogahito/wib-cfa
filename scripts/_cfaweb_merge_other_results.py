import json
from pathlib import Path
from collections import defaultdict

CACHE_DIR = Path("scripts/_cache_cfaweb_qb")
BATCH_DIR = Path("scripts/_cfaweb_other_batches")

by_cache = defaultdict(list)
n_merged = 0
n_files = 0
for f in sorted(BATCH_DIR.glob("batch_*_results.json")):
    for r in json.loads(f.read_text(encoding="utf-8")):
        by_cache[r["cache_name"]].append(r)
    n_files += 1

print(f"processed {n_files} result batch files")

for cache_name, results in by_cache.items():
    cache_path = CACHE_DIR / cache_name
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    by_page_idx = {x["page_idx"]: x for x in cache}
    for r in results:
        pidx = r["page_idx"]
        entry = by_page_idx.get(pidx)
        if entry is None:
            continue
        entry["page_type"] = r["page_type"]
        items = []
        for it in r.get("items", []):
            new_it = dict(it)
            if "qnum" in new_it:
                new_it["n"] = new_it.pop("qnum")
            items.append(new_it)
        entry["items"] = items
        if r.get("note"):
            entry["_vision_note"] = r["note"]
        n_merged += 1
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {cache_name}: merged {len(results)} pages")

print(f"total pages merged: {n_merged}")
