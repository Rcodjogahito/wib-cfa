#!/usr/bin/env python3
"""Analyze incomplete questions to understand which truly have missing tables."""
import sys, re
from pathlib import Path
from collections import defaultdict

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

# Stricter patterns for truly missing tables
TABLE_RE = re.compile(
    r'the following\s+(?:data|exhibit|table|figure|chart|financial statements?|financial information|information)[:\.]?\s*$',
    re.IGNORECASE,
)

def is_truly_incomplete(q):
    """More strict: question text ends abruptly after the exhibit reference."""
    text = (q.get('question_en', '') or '').strip()
    # Already has a table
    if '|' in text:
        return False
    # Text ends with "following [noun]" or very close to it
    if TABLE_RE.search(text):
        return True
    # Options are just entity names (Company A, Portfolio B, etc.)
    opts = [(q.get(f'option_{k}') or '').strip() for k in ('a', 'b', 'c')]
    if all(NAME_ONLY_OPT_RE.match(o) for o in opts if o):
        return True
    # Text is truncated mid-sentence after exhibit reference
    m = MISSING_RE.search(text)
    if m:
        after = text[m.end():].strip()
        # If text continues with a colon+space and then immediately next sentence
        # (meaning the table was between them), it's truly incomplete
        if after.startswith(':') or after == '':
            return True
    return False

page_size = 1000
offset = 0
truly_incomplete = []
false_positives = []
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
        text = q.get('question_en', '') or ''
        has_pattern = bool(MISSING_RE.search(text) and '|' not in text)
        opts = [(q.get(f'option_{k}') or '').strip() for k in ('a', 'b', 'c')]
        has_name_opts = all(NAME_ONLY_OPT_RE.match(o) for o in opts if o) and bool(re.search(r'following|exhibit|table|data', text, re.IGNORECASE))

        if has_pattern or has_name_opts:
            if is_truly_incomplete(q):
                truly_incomplete.append(q)
            else:
                false_positives.append(q)

    offset += page_size
    print(f"  checked {total_count}...", end="\r")
    if len(rows.data) < page_size:
        break

print(f"\nTotal questions: {total_count}")
print(f"Truly incomplete (need table fix): {len(truly_incomplete)}")
print(f"False positives (no fix needed): {len(false_positives)}")

# By source
from collections import Counter
ti_src = Counter(q.get('source', '?') for q in truly_incomplete)
fp_src = Counter(q.get('source', '?') for q in false_positives)
print(f"\nTruly incomplete by source: {dict(ti_src)}")
print(f"False positives by source: {dict(fp_src)}")

print("\n=== TRULY INCOMPLETE SAMPLES ===")
for q in truly_incomplete[:10]:
    print(f"\n[{q.get('source','?')}] {q['topic']}")
    print(f"  Subtopic: {q.get('subtopic','')[:60]}")
    print(f"  Q: {q['question_en'][:150]}")
    print(f"  A: {q.get('option_a','')[:60]}")
    print(f"  B: {q.get('option_b','')[:60]}")
    print(f"  C: {q.get('option_c','')[:60]}")

print("\n=== FALSE POSITIVE SAMPLES ===")
for q in false_positives[:5]:
    print(f"\n[{q.get('source','?')}] {q['topic']}")
    print(f"  Q: {q['question_en'][:150]}")
