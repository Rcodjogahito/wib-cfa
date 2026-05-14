#!/usr/bin/env python3
"""Count incomplete questions in Supabase."""
import sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

SECRETS_PATH = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"

def _load_secrets(path):
    result = {}
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

secrets = _load_secrets(SECRETS_PATH)
from supabase import create_client
sb = create_client(secrets["supabase"]["SUPABASE_URL"], secrets["supabase"]["SUPABASE_SERVICE_KEY"])

MISSING_RE = re.compile(
    r'the following\s+(?:data|exhibit|table|figure|chart|financial|statements?|information)',
    re.IGNORECASE,
)
NAME_ONLY_OPT_RE = re.compile(
    r'^(?:Company|Portfolio|Fund|Firm|Manager|Account)\s+[A-C]$',
    re.IGNORECASE,
)

def is_incomplete(q):
    text = q.get('question_en', '') or ''
    if MISSING_RE.search(text) and '|' not in text:
        return True
    opts = [(q.get(f'option_{k}') or '').strip() for k in ('a', 'b', 'c')]
    if (all(NAME_ONLY_OPT_RE.match(o) for o in opts if o)
        and re.search(r'following|exhibit|table|data', text, re.IGNORECASE)):
        return True
    return False

page_size = 1000
offset = 0
incomplete = []
total_count = 0

print("Fetching questions...")
while True:
    rows = sb.table("questions").select(
        "id,topic,subtopic,source,question_en,option_a,option_b,option_c"
    ).range(offset, offset + page_size - 1).execute()
    if not rows.data:
        break
    total_count += len(rows.data)
    for q in rows.data:
        if is_incomplete(q):
            incomplete.append(q)
    offset += page_size
    print(f"  checked {total_count}...", end="\r")
    if len(rows.data) < page_size:
        break

print(f"\nTotal questions:    {total_count}")
print(f"Incomplete:         {len(incomplete)}")
print(f"Complete:           {total_count - len(incomplete)}")

# Group by source
from collections import Counter
src_counts = Counter(q.get('source', 'unknown') for q in incomplete)
print(f"\nBy source: {dict(src_counts)}")

# Sample
print("\nSample incomplete questions:")
for q in incomplete[:8]:
    print(f"  [{q.get('source','?')}] {q['topic'][:30]:<30} | {(q.get('subtopic') or '')[:40]}")
    print(f"    text: {q['question_en'][:100]}")
