import json
from pathlib import Path
from collections import defaultdict
import hashlib

import fitz  # PyMuPDF

items = json.loads(Path('scripts/_fullbank_manifest.json').read_text(encoding='utf-8'))
print('manifest items:', len(items))

out_dir = Path('scripts/_fullbank_png')
out_dir.mkdir(exist_ok=True)

# Dedup by (pdf, page_idx)
pages = defaultdict(list)
for it in items:
    pages[(it['pdf'], it['page_idx'])].append(it['id'])
print('unique pages to render:', len(pages))

def page_key(pdf, page_idx):
    h = hashlib.md5(pdf.encode('utf-8')).hexdigest()[:10]
    return f"{h}_p{page_idx}"

rendered = {}
fail = 0
doc_cache = {}
for i, ((pdf, page_idx), ids) in enumerate(pages.items()):
    key = page_key(pdf, page_idx)
    png_path = out_dir / f"{key}.png"
    if png_path.exists():
        rendered[(pdf, page_idx)] = str(png_path)
        continue
    try:
        if pdf not in doc_cache:
            doc_cache[pdf] = fitz.open(pdf)
        doc = doc_cache[pdf]
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
        pix.save(str(png_path))
        rendered[(pdf, page_idx)] = str(png_path)
    except Exception as e:
        fail += 1
        rendered[(pdf, page_idx)] = None
    if (i + 1) % 200 == 0:
        print(f'  rendered {i+1}/{len(pages)}')
        # close docs periodically to limit memory
        for d in doc_cache.values():
            d.close()
        doc_cache = {}

for d in doc_cache.values():
    d.close()

print(f'Rendering done. Failures: {fail}')

for it in items:
    it['png'] = rendered.get((it['pdf'], it['page_idx']))

Path('scripts/_fullbank_manifest.json').write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')
print('manifest updated with png paths')
