import json
from pathlib import Path

BATCH_SIZE = 20

items = json.loads(Path('scripts/_fullbank_manifest.json').read_text(encoding='utf-8'))
no_png = [it for it in items if not it.get('png')]
print('items without a rendered png (render failures):', len(no_png))

items = [it for it in items if it.get('png')]
# Sort by source then pdf then page so adjacent batches share source/context
items.sort(key=lambda x: (x['source'], x['pdf'], x['page_idx']))

out_dir = Path('scripts/_fullbank_batches')
out_dir.mkdir(exist_ok=True)

batches = [items[i:i+BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
print('total batches:', len(batches))

manifest_index = []
for i, batch in enumerate(batches):
    bid = f"{i:04d}"
    path = out_dir / f"batch_{bid}.json"
    path.write_text(json.dumps(batch, ensure_ascii=False, indent=1), encoding='utf-8')
    manifest_index.append({
        "batch_id": bid, "path": str(path), "n": len(batch),
        "sources": sorted(set(x['source'] for x in batch)),
        "status": "pending",
    })

Path('scripts/_fullbank_progress.json').write_text(
    json.dumps({"batches": manifest_index, "total_items": len(items)}, ensure_ascii=False, indent=1),
    encoding='utf-8'
)
print('wrote scripts/_fullbank_progress.json tracking', len(manifest_index), 'batches')
