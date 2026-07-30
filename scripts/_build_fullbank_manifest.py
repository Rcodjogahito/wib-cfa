import json
from pathlib import Path
from collections import defaultdict

report = json.loads(Path('scripts/_audit_match_report.json').read_text(encoding='utf-8'))
dump = json.loads(Path('scripts/_full_dump_fresh_20260730.json').read_text(encoding='utf-8'))
dump_by_id = {d['id']: d for d in dump}

lowconf173 = json.loads(Path('scripts/_lowconf_all_results.json').read_text(encoding='utf-8'))
done_ids = {x['id'] for x in lowconf173}

matched = [r for r in report if r['status'] == 'matched']
remaining = [r for r in matched if r['id'] not in done_ids]
print('matched total:', len(matched), 'excluding 173 done:', len(remaining))

items = []
missing = 0
for r in remaining:
    q = dump_by_id.get(r['id'])
    if not q:
        missing += 1
        continue
    items.append({
        'id': r['id'], 'source': r['source'], 'score': r['score'],
        'pdf': r['pdf'], 'page_idx': r['best_page'],
        'topic': q.get('topic'), 'subtopic': q.get('subtopic'),
        'question_en': q.get('question_en'),
        'option_a': q.get('option_a'), 'option_b': q.get('option_b'), 'option_c': q.get('option_c'),
        'correct_answer': q.get('correct_answer'),
        'explanation_en': q.get('explanation_en'),
    })
print('missing from fresh dump:', missing)
print('final manifest size:', len(items))

by_source = defaultdict(int)
for it in items:
    by_source[it['source']] += 1
print(dict(by_source))

Path('scripts/_fullbank_manifest.json').write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')
