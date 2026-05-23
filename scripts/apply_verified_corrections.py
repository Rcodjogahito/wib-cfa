#!/usr/bin/env python3
"""
Apply the 3 manually verified corrections to Supabase via PowerShell.
Outputs a PowerShell script to execute.
"""
import sys, json, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUMP = r"C:\Users\codjo\AppData\Local\Temp\wib_questions_dump.json"
P3   = r"C:\Users\codjo\AppData\Local\Temp\wib_p3_flags.json"

with open(DUMP, encoding="utf-8-sig") as f:
    questions = json.load(f)
with open(P3, encoding="utf-8") as f:
    p3_flags = json.load(f)

q_by_id = {r["id"]: r for r in questions}

# ── 3 confirmed real errors ────────────────────────────────────────────────────
CONFIRMED = [
    {
        "q_pattern": "unimodal distribution has a skewness of 0.8",
        "stored":    "A",
        "correct":   "C",
        "reason":    "Positively skewed: mode < median < mean — mean is greatest",
    },
    {
        "q_pattern": "fundamental difference between preference shares and common shares",
        "stored":    "A",
        "correct":   "C",
        "reason":    "Preference shares do NOT have more voting rights; C (priority dividends) is the correct difference",
    },
    {
        "q_pattern": "When evaluating mutually exclusive projects, the IRR most likely",
        "stored":    "C",
        "correct":   "B",
        "reason":    "Explanation says IRR has 'Unrealistic reinvestment assumption' and 'Relative scale' problem — stored=C claims 'realistic reinvestment' which is WRONG; B (no scale context) is correct",
    },
]

corrections = []
for spec in CONFIRMED:
    for item in p3_flags:
        if spec["q_pattern"].lower() in item["question"].lower():
            q = q_by_id.get(item["id"], {})
            current = (q.get("correct_answer") or "").upper()
            if current == spec["stored"]:
                corrections.append({
                    "id":      item["id"],
                    "stored":  spec["stored"],
                    "correct": spec["correct"],
                    "reason":  spec["reason"],
                    "source":  item["source"],
                    "question": q.get("question_en","")[:200],
                })
            break

print(f"Applying {len(corrections)} confirmed corrections:\n")
for c in corrections:
    print(f"  [{c['source']}] {c['stored']} -> {c['correct']}")
    print(f"  Q: {c['question'][:100]}")
    print(f"  Reason: {c['reason']}")
    print()

# Write PowerShell patch script
KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFsY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ.epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8"
URL  = "https://qlcakqtrambahrofnhho.supabase.co"

ps_lines = [
    '[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12',
    '[Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }',
    f'$key = "{KEY}"',
    f'$url = "{URL}"',
    '$headers = @{ "apikey" = $key; "Authorization" = "Bearer $key"; "Content-Type" = "application/json"; "Prefer" = "return=minimal" }',
    '',
]
for c in corrections:
    safe_id = c["id"]
    body = json.dumps({"correct_answer": c["correct"]})
    ps_lines.append(f'# {c["source"]} | stored={c["stored"]} -> {c["correct"]} | {c["reason"][:60]}')
    ps_lines.append(f'$resp = Invoke-WebRequest -Method PATCH -Uri "$url/rest/v1/questions?id=eq.{safe_id}" \\')
    ps_lines.append(f'  -Headers $headers -Body \'{body}\' -UseBasicParsing -SkipCertificateCheck')
    ps_lines.append(f'Write-Host "Patched {safe_id}: $($resp.StatusCode)"')
    ps_lines.append('')

ps_script = "\n".join(ps_lines)
out_ps = r"C:\Users\codjo\AppData\Local\Temp\wib_apply_corrections.ps1"
with open(out_ps, "w", encoding="utf-8") as f:
    f.write(ps_script)
print(f"PowerShell script written to: {out_ps}")
