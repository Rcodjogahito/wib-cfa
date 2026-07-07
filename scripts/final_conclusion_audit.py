#!/usr/bin/env python3
"""
final_conclusion_audit.py — Audit correct_answer against the explanation's CONCLUDING
statement (last numeric token / last sentence), not just the first sentence or an
explicit letter mention.

Root cause this catches: previous NLP audits (P1 = explicit letter, P2 = option text
in the FIRST sentence of the explanation) never checked whether the explanation's final
computed value matches a DIFFERENT option than the one stored as correct_answer. This is
the Oregon Corp bug found in session 45: explanation ends "...= 2,370,000 / 12 = 197,500."
(matches option A) but correct_answer was stored as "C".

This script only DETECTS candidates (writes a JSON file) — it never patches Supabase.
High false-positive mode: the explanation's last part sometimes rebuts a DISTRACTOR
option rather than stating the true answer (e.g. "if you divide instead of multiply by
101%, you get 13,130 bonds"). Candidates must be verified (manually or via an LLM pass
that re-derives the calculation) before applying any correction.

Run: python scripts/final_conclusion_audit.py
Output: scripts/_final_conclusion_candidates.json
"""
import difflib
import json
import re
import sys
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

SECRETS_PATH = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
OUTPUT_PATH = Path(__file__).parent / "_final_conclusion_candidates.json"

SENT_SPLIT = re.compile(r"(?<!\d)\.(?!\d)\s+")
FINAL_NUM = re.compile(r"([\$]?-?[\d,]+\.?\d*\s*%?)\.?\s*$")


def load_secrets(path: Path) -> dict:
    result: dict = {}
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


def fetch_all_questions(url: str, anon_key: str) -> list[dict]:
    headers = {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}
    cols = (
        "id,topic,subtopic,question_en,option_a,option_b,option_c,"
        "correct_answer,explanation_en,source"
    )
    rows: list[dict] = []
    offset, page_size = 0, 1000
    while True:
        h = dict(headers, Range=f"{offset}-{offset + page_size - 1}")
        r = requests.get(
            f"{url}/rest/v1/questions", headers=h,
            params={"select": cols, "order": "id"}, timeout=30,
        )
        r.raise_for_status()
        page = r.json()
        rows.extend(page)
        if len(page) < page_size:
            break
        offset += page_size
    return rows


def norm_opt(s: str) -> str:
    if not s:
        return ""
    s = s.strip().rstrip(".").strip()
    return re.sub(r"\s+", " ", s).lower()


def norm_num(s: str) -> str:
    if not s:
        return ""
    s = s.strip().rstrip(".").strip()
    return re.sub(r"\s+", "", s).lower()


def last_sentence(expl: str) -> str:
    expl = expl.strip()
    parts = [p for p in SENT_SPLIT.split(expl) if p.strip()]
    return parts[-1].strip() if parts else expl


def audit(rows: list[dict]) -> list[dict]:
    candidates = []
    for row in rows:
        expl = (row.get("explanation_en") or "").strip()
        if not expl or len(expl) < 15:
            continue

        opts = {"A": row.get("option_a") or "", "B": row.get("option_b") or "", "C": row.get("option_c") or ""}
        stored = (row.get("correct_answer") or "").strip().upper()
        if stored not in ("A", "B", "C"):
            continue

        # Signal 1: exact final numeric token match (high precision)
        detected_by_number = None
        m = FINAL_NUM.search(expl)
        if m:
            final_tok = norm_num(m.group(1))
            if final_tok and len(final_tok) >= 2:
                for letter, text in opts.items():
                    if norm_num(text) == final_tok:
                        detected_by_number = letter
                        break

        # Signal 2: last-sentence containment against option texts (noisier)
        lsent_norm = norm_opt(last_sentence(expl))
        detected_by_sentence = None
        for letter, text in opts.items():
            nt = norm_opt(text)
            if not nt or len(nt) < 3:
                continue
            if nt in lsent_norm:
                detected_by_sentence = letter if detected_by_sentence is None else "AMBIGUOUS"

        detected, reason = None, None
        if detected_by_number and detected_by_number != stored:
            detected, reason = detected_by_number, "final_number_mismatch"
        elif detected_by_sentence not in (None, "AMBIGUOUS") and detected_by_sentence != stored:
            detected, reason = detected_by_sentence, "last_sentence_containment_mismatch"

        if detected:
            candidates.append({
                "id": row["id"], "source": row.get("source"), "topic": row.get("topic"),
                "subtopic": row.get("subtopic"), "stored": stored, "detected": detected,
                "reason": reason, "question_en": row.get("question_en"),
                "option_a": opts["A"], "option_b": opts["B"], "option_c": opts["C"],
                "explanation_en": expl,
            })
    return candidates


def main() -> None:
    secrets = load_secrets(SECRETS_PATH)["supabase"]
    rows = fetch_all_questions(secrets["SUPABASE_URL"], secrets["SUPABASE_ANON_KEY"])
    print(f"Total rows: {len(rows)}")

    candidates = audit(rows)
    print(f"Flagged candidates (stored != detected from conclusion): {len(candidates)}")

    by_reason: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for c in candidates:
        by_reason[c["reason"]] = by_reason.get(c["reason"], 0) + 1
        by_source[c["source"]] = by_source.get(c["source"], 0) + 1
    print("By reason:", by_reason)
    print("By source:", by_source)

    OUTPUT_PATH.write_text(json.dumps(candidates, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Written: {OUTPUT_PATH}")
    print("NEXT STEP: verify each candidate (redo the calculation / reasoning) before patching "
          "correct_answer — do not trust 'detected' blindly, see docstring false-positive mode.")


if __name__ == "__main__":
    main()
