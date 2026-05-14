#!/usr/bin/env python3
"""Refined count of truly incomplete questions."""
import sys, re
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

def load_secrets(path):
    result = {}; section = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]; result[section] = {}
            elif "=" in line and section:
                k, _, v = line.partition("=")
                result[section][k.strip()] = v.strip().strip('"').strip("'")
    return result

secrets = load_secrets(Path(".streamlit/secrets.toml"))
from supabase import create_client
sb = create_client(secrets["supabase"]["SUPABASE_URL"], secrets["supabase"]["SUPABASE_SERVICE_KEY"])

# Questions where the table image is missing
# Pattern: "following X:" immediately followed by question-flow word (not data values)
TRULY_MISSING_RE = re.compile(
    r'the following\s+(?:data|exhibit|table|figure|chart|financial statements?|financial information|information)\s*:\s*'
    r'(?:Based|If|Assuming|Which|The company|The analyst|An analyst|Using|From|According|Given that|Determine|Calculate)',
    re.IGNORECASE,
)
NAME_ONLY_RE = re.compile(r'^(?:Company|Portfolio|Fund|Firm|Manager|Account)\s+[A-Z]$', re.IGNORECASE)

page_size = 1000
offset = 0
truly = []
total = 0

while True:
    rows = sb.table("questions").select(
        "id,topic,subtopic,source,question_en,option_a,option_b,option_c"
    ).range(offset, offset + page_size - 1).execute()
    if not rows.data:
        break
    total += len(rows.data)
    for q in rows.data:
        text = q.get("question_en", "") or ""
        if "|" in text:
            continue
        opts = [(q.get(f"option_{k}") or "").strip() for k in ("a", "b", "c")]
        name_opts = all(NAME_ONLY_RE.match(o) for o in opts if o)
        if TRULY_MISSING_RE.search(text) or name_opts:
            truly.append(q)
    offset += page_size
    print(f"  checked {total}...", end="\r")
    if len(rows.data) < page_size:
        break

print(f"\nTotal: {total} | Truly missing table: {len(truly)}")
print(f"By source: {dict(Counter(q.get('source','?') for q in truly))}")
print()
print("=== SAMPLES ===")
for q in truly[:15]:
    text = q["question_en"]
    opts = [q.get(f"option_{k}", "") for k in ("a", "b", "c")]
    m = re.search(r"following\s+\w+\s*:", text, re.IGNORECASE)
    after = text[m.end():m.end()+50] if m else text[:50]
    print(f"[{q.get('source','?')}] {(q.get('subtopic') or '')[:50]}")
    print(f"  text[...colon+]: '{after}'")
    print(f"  A: {opts[0][:40]} | B: {opts[1][:40]}")
