#!/usr/bin/env python3
"""
Fix Kaplan answer detection — improved algorithm, zero API calls.

Replaces word-overlap with a multi-pass detector:
  Pass 1 : explicit letter pattern in explanation ("correct answer is B", etc.)
  Pass 2 : exact option text in first sentence
  Pass 3 : stemmed word overlap on first 3 sentences (more tolerant than v1)
  Pass 4 : numerical value match (explanation contains the option's number)

Run: python scripts/fix_kaplan_v2.py [--dry-run]
"""

import re
import sys
import tomllib
from pathlib import Path
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

DRY_RUN = "--dry-run" in sys.argv
SECRETS_PATH = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"

with open(SECRETS_PATH, "rb") as f:
    _s = tomllib.load(f)

from supabase import create_client
sb = create_client(_s["supabase"]["SUPABASE_URL"], _s["supabase"]["SUPABASE_SERVICE_KEY"])

# ── Tokenizer ─────────────────────────────────────────────────────────────────

_STOPS = {
    'the','a','an','and','or','but','is','are','was','were','be','been','being',
    'have','has','had','do','does','did','to','of','in','for','on','with','as',
    'at','by','from','that','this','which','who','it','its','will','would',
    'could','should','may','might','can','not','no','more','than','less','most',
    'least','such','also','both','all','any','each','if','when','then','they',
    'their','them','there','these','those','we','our','you','your','he','she',
    'his','her','what','how','why','about','into','through','after','before',
    'between','same','other','however','therefore','because','since','while',
    'although','only','typically','generally','usually','often','always','never',
    'sometimes','relatively','compared','similar','different','another',
    'include','includes','included','using','used','use','known','based',
}

def _stem(w: str) -> str:
    for suf in ('ations','ation','tions','tion','ments','ment','ness',
                'ing','ings','ed','ers','er','es','s'):
        if len(w) > len(suf) + 4 and w.endswith(suf):
            return w[:-len(suf)]
    return w

def _tokenize(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r'[a-z]+', text.lower())
            if w not in _STOPS and len(w) > 3]

def _fuzzy_token_match(opt_word: str, expl_words: list[str]) -> bool:
    """True if opt_word is a prefix/substring of any explanation word, or vice versa."""
    if len(opt_word) < 5:
        return opt_word in expl_words
    for ew in expl_words:
        if ew.startswith(opt_word) or opt_word.startswith(ew):
            return True
        # fuzzy: difflib ratio for short words
        if len(opt_word) >= 6 and len(ew) >= 6:
            common = sum(a == b for a, b in zip(opt_word, ew))
            if common / max(len(opt_word), len(ew)) >= 0.85:
                return True
    return False

# ── Original overlap (to identify zero-overlap questions) ─────────────────────

def _original_has_signal(opt_a, opt_b, opt_c, explanation: str) -> bool:
    sents = re.split(r'(?<=[.!?])\s+', (explanation or '').strip())
    core = ' '.join(sents[:2]) if sents else explanation
    core_words = set(re.findall(r'[a-z]+', core.lower()))
    core_words -= _STOPS
    for opt in [opt_a, opt_b, opt_c]:
        opt_words = set(re.findall(r'[a-z]+', (opt or '').lower())) - _STOPS
        opt_words = {w for w in opt_words if len(w) > 2}
        if opt_words and len(opt_words & core_words) / len(opt_words) > 0:
            return True
    return False

# ── Improved detection ────────────────────────────────────────────────────────

_NEGATED = re.compile(
    r'\b(least\s+accurate|least\s+likely|least\s+correct|incorrect|not\s+accurate|'
    r'not\s+correct|is\s+false|not\s+true|except|inaccurate|violates|least\s+appropriate)\b',
    re.IGNORECASE,
)

def _detect_v2(q_text: str, opt_a: str, opt_b: str, opt_c: str,
               explanation: str) -> str | None:
    if not explanation or len(explanation.strip()) < 15:
        return None

    expl = explanation.strip()
    opts = {'A': (opt_a or '').strip(), 'B': (opt_b or '').strip(), 'C': (opt_c or '').strip()}

    # ── Pass 1: explicit letter mention ──────────────────────────────────────
    for letter in ('A', 'B', 'C'):
        if re.search(
            rf'\b(correct\s+answer\s+is\s+{letter}|answer\s+is\s+{letter}|'
            rf'{letter}\s+is\s+(the\s+)?(correct|right|best)|'
            rf'(choose|select|answer)\s*[:\s]+{letter})\b',
            expl, re.IGNORECASE,
        ):
            return letter

    # ── Pass 2: exact option text in first sentence ───────────────────────────
    first_sent = (re.split(r'(?<=[.!?])\s+', expl) or [''])[0].lower()
    for letter in ('A', 'B', 'C'):
        opt_clean = opts[letter].lower().rstrip('.').strip()
        if opt_clean and len(opt_clean) > 8 and opt_clean in first_sent:
            return letter

    # ── Pass 3: stemmed + fuzzy overlap on first 3 sentences ────────────────
    focus_sents = re.split(r'(?<=[.!?])\s+', expl)[:3]
    focus = ' '.join(focus_sents)
    expl_stems = set(_tokenize(focus))
    expl_raw_words = re.findall(r'[a-z]+', focus.lower())

    scores: dict[str, float] = {}
    for letter in ('A', 'B', 'C'):
        opt_stems = list(_tokenize(opts[letter]))
        if not opt_stems:
            scores[letter] = 0.0
            continue
        # Count: exact stem match OR fuzzy prefix match
        matched = sum(
            1 for ow in opt_stems
            if ow in expl_stems or _fuzzy_token_match(ow, expl_raw_words)
        )
        scores[letter] = matched / len(opt_stems)

    max_score = max(scores.values())
    if max_score > 0:
        winners = [l for l, s in scores.items() if s == max_score]
        if len(winners) == 1:
            return winners[0]
        # Tie: pick by most absolute tokens matched
        abs_match = {
            l: sum(1 for ow in _tokenize(opts[l])
                   if ow in expl_stems or _fuzzy_token_match(ow, expl_raw_words))
            for l in winners
        }
        best = max(abs_match, key=abs_match.get)
        if abs_match[best] > min(abs_match.values()):
            return best

    # ── Pass 4: numerical value match ────────────────────────────────────────
    def _nums(text: str) -> set[str]:
        raw = re.findall(r'[\d,]+\.?\d*\s*(?:%|bps?|pp)?', text.lower())
        return {n.replace(',', '').strip() for n in raw if n.strip()}

    expl_nums = _nums(expl[:400])
    for letter in ('A', 'B', 'C'):
        opt_nums = _nums(opts[letter])
        if opt_nums and opt_nums <= expl_nums:
            return letter

    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading all Kaplan questions...", flush=True)
    all_data: list[dict] = []
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

    # Identify zero-overlap questions
    zero = [
        q for q in all_data
        if not _original_has_signal(
            q.get("option_a"), q.get("option_b"), q.get("option_c"),
            q.get("explanation_en") or "",
        )
    ]
    print(f"Zero-overlap (potential wrong answers): {len(zero)}")

    # Apply improved detection
    fixed = 0
    unchanged = 0
    undetermined = 0
    updates: list[tuple[str, str]] = []  # (id, new_answer)

    for q in zero:
        new = _detect_v2(
            q["question_en"], q["option_a"], q["option_b"], q["option_c"],
            q.get("explanation_en") or "",
        )
        if new is None:
            undetermined += 1
        elif new == q["correct_answer"]:
            unchanged += 1
        else:
            fixed += 1
            updates.append((q["id"], new))

    print(f"\nDetection results:")
    print(f"  Fixed (answer changes)  : {fixed}")
    print(f"  Unchanged (already OK)  : {unchanged}")
    print(f"  Undetermined (no signal): {undetermined}")

    if DRY_RUN:
        print("\n[DRY RUN] No changes written.")
        # Sample undetermined
        undet_qs = [
            q for q in zero
            if _detect_v2(q["question_en"], q["option_a"], q["option_b"], q["option_c"],
                          q.get("explanation_en") or "") is None
        ]
        print(f"\nSample undetermined ({min(5, len(undet_qs))}):")
        for q in undet_qs[:5]:
            print(f"  [{q['correct_answer']}] {q['question_en'][:80]}")
            print(f"       Expl: {(q.get('explanation_en') or '')[:100]}")
        return

    # Apply updates in batches of 50
    print(f"\nApplying {len(updates)} answer corrections...", flush=True)
    for i in range(0, len(updates), 50):
        batch = updates[i:i+50]
        for qid, ans in batch:
            sb.table("questions").update({"correct_answer": ans}).eq("id", qid).execute()
        print(f"  {min(i+50, len(updates))}/{len(updates)}", flush=True)

    # Final distribution
    print("\nFetching final Kaplan distribution...", flush=True)
    final: list[dict] = []
    offset = 0
    while True:
        r = sb.table("questions").select("correct_answer").eq("source", "Kaplan").range(offset, offset+999).execute()
        final.extend(r.data)
        if len(r.data) < 1000: break
        offset += 1000

    dist = Counter(q["correct_answer"] for q in final)
    total = sum(dist.values())
    print(f"\nFinal distribution ({total} questions):")
    for l in ("A", "B", "C"):
        pct = dist[l] * 100 // total if total else 0
        bar = "#" * (pct // 2)
        print(f"  {l}: {dist[l]:4d} ({pct:2d}%)  {bar}")

    print(f"\nDone — {fixed} answers corrected, {undetermined} still undetermined.")
    if undetermined > 0:
        print(f"  Note: {undetermined} questions have no detectable signal in their explanation.")
        print(f"  These were left at their current value (likely correct or no explanation).")


if __name__ == "__main__":
    main()
