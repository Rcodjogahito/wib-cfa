#!/usr/bin/env python3
"""
Read pdf_audit_fixes.json and apply corrections to Supabase via a generated
PowerShell script (avoids TLS issue with supabase-py).

Usage:
    python scripts/apply_pdf_fixes.py [--dry-run] [--min-sim 0.55]
"""
import sys, json, argparse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FIXES_PATH = Path(r"C:\Users\codjo\AppData\Local\Temp\pdf_audit_fixes.json")
PS1_PATH   = Path(r"C:\Users\codjo\AppData\Local\Temp\apply_pdf_fixes.ps1")

SUPABASE_URL = "https://qlcakqtrambahrofnhho.supabase.co"
SERVICE_KEY  = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF"
                "sY2FrcXRyYW1iYWhyb2ZuaGhvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODI2"
                "NTA0NCwiZXhwIjoyMDkzODQxMDQ0fQ.epgzG_6n2NBhT7KGLCdhio9HvVZy4A9Mc3xvjjE2oR8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print fixes but do not write PS1 or execute")
    parser.add_argument("--min-sim", type=float, default=0.55,
                        help="Minimum similarity threshold to apply fix (default 0.55)")
    args = parser.parse_args()

    with open(FIXES_PATH, encoding="utf-8") as f:
        fixes = json.load(f)

    # Filter by similarity threshold
    to_apply = [fx for fx in fixes if fx.get("sim", 0) >= args.min_sim]
    skipped  = len(fixes) - len(to_apply)

    print(f"Fixes loaded:  {len(fixes)}")
    print(f"Min-sim {args.min_sim:.2f}: applying {len(to_apply)}, skipping {skipped}")

    if args.dry_run:
        print("\n[DRY RUN] Would apply:")
        for i, fx in enumerate(to_apply):
            print(f"  [{i+1:3d}] {fx['id'][:8]}… {fx['source']} "
                  f"{fx['db_answer']}→{fx['pdf_answer']} sim={fx['sim']:.2f} "
                  f"| {fx['question'][:80]}")
        return

    if not to_apply:
        print("Nothing to apply.")
        return

    # Build PowerShell script
    lines = [
        '$headers = @{',
        f'    "apikey"        = "{SERVICE_KEY}"',
        f'    "Authorization" = "Bearer {SERVICE_KEY}"',
        '    "Content-Type"  = "application/json"',
        '    "Prefer"        = "return=minimal"',
        '}',
        '$base = "' + SUPABASE_URL + '/rest/v1/questions"',
        '$ok = 0; $err = 0',
        '',
    ]

    for fx in to_apply:
        qid = fx["id"]
        new_ans = fx["pdf_answer"]
        q_short = fx["question"][:60].replace('"', "'").replace('`', "'")
        lines += [
            f'# {fx["source"]} | DB={fx["db_answer"]} PDF={new_ans} | {q_short}',
            f'$body = \'{{"correct_answer":"{new_ans}"}}\'',
            f'try {{',
            f'    Invoke-WebRequest -Uri "$base?id=eq.{qid}" -Method PATCH '
            f'-Headers $headers -Body $body -SkipCertificateCheck -UseBasicParsing | Out-Null',
            f'    $ok++; Write-Host "OK  {qid[:8]}  {fx["db_answer"]}→{new_ans}"',
            f'}} catch {{',
            f'    $err++; Write-Host "ERR {qid[:8]}: $_"',
            f'}}',
            '',
        ]

    lines += [
        'Write-Host ""',
        'Write-Host "Done: $ok OK, $err errors"',
    ]

    ps1_content = "\n".join(lines)
    PS1_PATH.write_text(ps1_content, encoding="utf-8")
    print(f"\nPS1 written: {PS1_PATH}")
    print(f"Run with:  powershell -File \"{PS1_PATH}\"")

    # Print preview
    print(f"\nFixes to apply ({len(to_apply)}):")
    for i, fx in enumerate(to_apply):
        print(f"  [{i+1:3d}] {fx['id'][:8]}… {fx['source']} "
              f"{fx['db_answer']}→{fx['pdf_answer']} sim={fx['sim']:.2f} "
              f"| {fx['question'][:80]}")


if __name__ == "__main__":
    main()
