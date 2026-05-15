#!/usr/bin/env python3
"""
Fix Kaplan questions with unreliable correct answer detection (all-zero overlap).

Identifies questions where word-overlap gave 0 for all options (meaning the
detection defaulted to 'A' without real signal), then uses Claude to re-detect
the correct answer from question + options + explanation.

Run from project root:
    python scripts/fix_kaplan_answers.py [--dry-run]
"""

import re
import sys
import time
import tomllib
from pathlib import Path

import anthropic

DRY_RUN = "--dry-run" in sys.argv

SECRETS_PATH = Path(r"D:\CLAUDE\Projet CFA\wib-cfa\.streamlit\secrets.toml")

with open(SECRETS_PATH, "rb") as f:
    _secrets = tomllib.load(f)

_SB_URL = _secrets["supabase"]["SUPABASE_URL"]
_SB_KEY = _secrets["supabase"].get("SUPABASE_SERVICE_KEY") or _secrets["supabase"]["SUPABASE_ANON_KEY"]
_CLAUDE_KEY = _secrets.get("anthropic", {}).get("ANTHROPIC_API_KEY") or None

# Try to get Claude key from environment if not in secrets
import os
if not _CLAUDE_KEY:
    _CLAUDE_KEY = os.environ.get("ANTHROPIC_API_KEY")

if not _CLAUDE_KEY:
    print("ERROR: No Anthropic API key found.")
    print("  Option 1: Add to .streamlit/secrets.toml:")
    print("    [anthropic]")
    print('    ANTHROPIC_API_KEY = "sk-ant-..."')
    print("  Option 2: Set env var:  set ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

from supabase import create_client
sb = create_client(_SB_URL, _SB_KEY)
claude = anthropic.Anthropic(api_key=_CLAUDE_KEY)

# ── Answer detection (current algorithm) ─────────────────────────────────────

_STOPS = {
    'the','a','an','and','or','but','is','are','was','were','be','been',
    'being','have','has','had','do','does','did','to','of','in','for',
    'on','with','as','at','by','from','that','this','which','who','it',
    'its','will','would','could','should','may','might','can','not','no',
    'more','than','less','most','least','such','also','both','all','any',
    'each','if','when','then','they','their','them','there','these','those',
    'we','our','you','your','he','she','his','her','what','how','why',
    'about','into','through','after','before','between','same','other',
    'however','therefore','because','since','while','although','only',
}


def _tokenize(text: str) -> list:
    words = re.findall(r'[a-z]+', text.lower())
    return [w for w in words if w not in _STOPS and len(w) > 2]


_NEGATED = re.compile(
    r'\b(least accurate|least likely|incorrect|not accurate|not correct|'
    r'does not|is not|is false|not true|except|inaccurate|violates)\b',
    re.IGNORECASE,
)


def _overlap_scores(q_text: str, opt_a: str, opt_b: str, opt_c: str, explanation: str):
    sents = re.split(r'(?<=[.!?])\s+', explanation.strip())
    expl_core = ' '.join(sents[:2]) if sents else explanation
    expl_words = set(_tokenize(expl_core))
    scores = {}
    for letter, opt in [('A', opt_a), ('B', opt_b), ('C', opt_c)]:
        opt_words = set(_tokenize(opt))
        scores[letter] = len(opt_words & expl_words) / len(opt_words) if opt_words else 0.0
    return scores


def _has_signal(scores: dict) -> bool:
    return max(scores.values()) > 0


# ── Claude detection ──────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a CFA Level 1 expert. Given a multiple-choice question with three options "
    "and its explanation, determine which option (A, B, or C) is the correct answer. "
    "Reply with ONLY the single letter A, B, or C."
)

_RETRY_DELAYS = [5, 10, 30]


def _ask_claude(question: str, opt_a: str, opt_b: str, opt_c: str,
                explanation: str, attempt: int = 0) -> str | None:
    prompt = (
        f"Question: {question}\n\n"
        f"A) {opt_a}\n"
        f"B) {opt_b}\n"
        f"C) {opt_c}\n\n"
        f"Explanation: {explanation}\n\n"
        f"Which option is correct? Reply with only A, B, or C."
    )
    try:
        resp = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip().upper()
        if text and text[0] in ("A", "B", "C"):
            return text[0]
        return None
    except Exception as e:
        err = str(e)
        if ("429" in err or "rate_limit" in err or "overloaded" in err) and attempt < len(_RETRY_DELAYS):
            wait = _RETRY_DELAYS[attempt]
            print(f"  [RATE LIMIT] waiting {wait}s...", flush=True)
            time.sleep(wait)
            return _ask_claude(question, opt_a, opt_b, opt_c, explanation, attempt + 1)
        print(f"  [ERROR] {e}")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Fetching all Kaplan questions...", flush=True)
    all_data = []
    offset = 0
    while True:
        r = sb.table("questions").select(
            "id,question_en,option_a,option_b,option_c,explanation_en,correct_answer"
        ).eq("source", "Kaplan").range(offset, offset + 999).execute()
        all_data.extend(r.data)
        if len(r.data) < 1000:
            break
        offset += 1000
    print(f"Loaded {len(all_data)} Kaplan questions")

    # Find zero-overlap questions (definitely defaulted to A or min of equal zeros)
    zero_overlap = []
    for q in all_data:
        expl = q.get("explanation_en") or ""
        scores = _overlap_scores(
            q["question_en"], q["option_a"], q["option_b"], q["option_c"], expl
        )
        if not _has_signal(scores):
            zero_overlap.append(q)

    print(f"Zero-overlap questions: {len(zero_overlap)} (will re-detect with Claude)")

    if DRY_RUN:
        print("[DRY RUN] Would process", len(zero_overlap), "questions")
        return

    fixed = 0
    unchanged = 0
    errors = 0
    for i, q in enumerate(zero_overlap):
        if i % 50 == 0:
            print(f"  Progress {i}/{len(zero_overlap)} (fixed={fixed}, err={errors})", flush=True)

        new_answer = _ask_claude(
            q["question_en"], q["option_a"], q["option_b"], q["option_c"],
            q.get("explanation_en") or ""
        )
        time.sleep(0.5)  # 2 req/s to stay safe

        if new_answer is None:
            errors += 1
            continue

        if new_answer == q["correct_answer"]:
            unchanged += 1
        else:
            sb.table("questions").update({"correct_answer": new_answer}).eq("id", q["id"]).execute()
            fixed += 1

    print(f"\nDone — Fixed: {fixed} | Unchanged: {unchanged} | Errors: {errors}")

    # Show new distribution
    r = sb.table("questions").select("correct_answer").eq("source", "Kaplan").execute()
    from collections import Counter
    dist = Counter(item["correct_answer"] for item in r.data)
    total = sum(dist.values())
    print(f"New Kaplan distribution: A={dist['A']} ({dist['A']*100//total}%)  B={dist['B']} ({dist['B']*100//total}%)  C={dist['C']} ({dist['C']*100//total}%)")


if __name__ == "__main__":
    main()
