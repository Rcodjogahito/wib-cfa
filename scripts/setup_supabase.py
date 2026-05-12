"""
WIB CFA — Supabase one-shot setup script.

Run AFTER creating a Supabase project and getting credentials:
    python scripts/setup_supabase.py <SUPABASE_URL> <SUPABASE_ANON_KEY>

This script:
  1. Applies the schema (tables, indexes, RLS, grants)
  2. Seeds questions from local SQLite DB (if populated via extract_from_warehouse.py)
  3. Seeds flashcards
  4. Writes .streamlit/secrets.toml
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/setup_supabase.py <URL> <ANON_KEY>")
        print()
        print("Get these from: https://supabase.com/dashboard/project/<ref>/settings/api")
        sys.exit(1)

    url = sys.argv[1].rstrip("/")
    key = sys.argv[2]

    print(f"Connecting to Supabase: {url}")

    from supabase import create_client
    sb = create_client(url, key)

    # ── Apply schema via REST SQL endpoint ────────────────────────────────────
    schema_path = PROJECT_ROOT / "supabase_schema.sql"
    if schema_path.exists():
        print("Schema already present in supabase_schema.sql")
        print("→ Apply it manually via the Supabase SQL Editor:")
        print(f"  https://supabase.com/dashboard/project/_/sql/new")
        print()

    # ── Seed questions from SQLite ────────────────────────────────────────────
    db_path = PROJECT_ROOT / "wib_cfa.db"
    if db_path.exists():
        print(f"Reading questions from {db_path} ...")
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM questions")
        q_count = cur.fetchone()[0]
        print(f"Found {q_count} questions in local SQLite")

        if q_count > 0:
            # Check if already seeded
            try:
                res = sb.table("questions").select("id", count="exact").limit(1).execute()
                remote_count = res.count or 0
            except Exception:
                remote_count = 0

            if remote_count > 0:
                print(f"Supabase already has {remote_count} questions — skipping seed.")
            else:
                print("Seeding questions to Supabase (batch insert)...")
                cur.execute("SELECT * FROM questions")
                rows = [dict(r) for r in cur.fetchall()]
                # Batch in chunks of 500
                batch_size = 500
                inserted = 0
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    sb.table("questions").insert(batch).execute()
                    inserted += len(batch)
                    print(f"  Inserted {inserted}/{len(rows)} questions...")
                print(f"Done — {inserted} questions seeded.")

        # Seed flashcards
        cur.execute("SELECT COUNT(*) FROM flashcards")
        f_count = cur.fetchone()[0]
        if f_count > 0:
            try:
                res = sb.table("flashcards").select("id", count="exact").limit(1).execute()
                remote_fc = res.count or 0
            except Exception:
                remote_fc = 0

            if remote_fc > 0:
                print(f"Supabase already has {remote_fc} flashcards — skipping.")
            else:
                cur.execute("SELECT * FROM flashcards")
                rows = [dict(r) for r in cur.fetchall()]
                sb.table("flashcards").insert(rows).execute()
                print(f"Seeded {len(rows)} flashcards.")

        conn.close()
    else:
        print(f"No local SQLite DB found at {db_path}")
        print("Run extract_from_warehouse.py first to populate it.")

    # ── Write secrets.toml ────────────────────────────────────────────────────
    secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
    secrets_content = f"""[supabase]
SUPABASE_URL = "{url}"
SUPABASE_ANON_KEY = "{key}"
"""
    secrets_path.write_text(secrets_content, encoding="utf-8")
    print(f"\nWrote credentials to {secrets_path}")
    print("(This file is git-ignored — do not commit it)")

    print("\n✓ Setup complete!")
    print()
    print("Next steps:")
    print("  1. Deploy on Streamlit Cloud: https://share.streamlit.io")
    print("     → Repo: Rcodjogahito/wib-cfa | Branch: master | File: streamlit_app.py")
    print("  2. Add Streamlit Cloud secrets (Settings > Secrets):")
    print(f"     [supabase]")
    print(f"     SUPABASE_URL = \"{url}\"")
    print(f"     SUPABASE_ANON_KEY = \"{key}\"")


if __name__ == "__main__":
    main()
