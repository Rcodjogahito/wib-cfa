#!/usr/bin/env python3
"""
fix_answers_consistency.py — Vérifie et corrige correct_answer pour TOUTES les
questions (tous sources) en utilisant les explications stockées en DB.

Algorithme (4 passes, du plus fiable au moins fiable) :
  Pass 1 : mention explicite de la lettre dans l'explication
           ("correct answer is B", "B is correct", etc.)
  Pass 2 : texte exact de l'option dans la 1re phrase de l'explication
           (uniquement si len(option) > 8 pour éviter les faux positifs)
  Pass 3 : overlap de mots-clés stemmatisés (confiance moyenne — reporté)
  Pass 4 : match numérique (reporté)

Seules les passes 1 et 2 (haute confiance) déclenchent une correction.
Les passes 3/4 sont loggées mais non appliquées automatiquement.

Usage:
    cd D:\\CLAUDE\\Projet CFA\\wib-cfa
    python scripts/fix_answers_consistency.py [--dry-run] [--source SOURCE]

SOURCE: uworld|kaplan|extra|kevin|cfaweb|wib|all (défaut: all)
        'cfaweb' = source "CFA_WEB"
        'wib'    = source "WIB Internal"
"""

import re
import sys
import time
import tomllib
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

SECRETS_PATH = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"

def _retry(fn, retries=5, delay=3):
    """Retry fn on any exception, with exponential backoff."""
    last_exc = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            wait = delay * (2 ** attempt)
            print(f"  [RETRY {attempt+1}/{retries}] {type(e).__name__}: {e} — attente {wait}s", flush=True)
            time.sleep(wait)
    raise last_exc

SOURCE_MAP = {
    "uworld": "UWorld",
    "kaplan": "Kaplan",
    "extra":  "Extra_QB",
    "kevin":  "Kevin_Mock",
    "cfaweb": "CFA_WEB",
    "wib":    "WIB Internal",
}

# ── Tokenizer (same as fix_kaplan_v2) ────────────────────────────────────────

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

def _tokenize(text: str) -> list:
    return [_stem(w) for w in re.findall(r'[a-z]+', text.lower())
            if w not in _STOPS and len(w) > 3]

def _fuzzy(opt_word: str, expl_words: list) -> bool:
    if len(opt_word) < 5:
        return opt_word in expl_words
    for ew in expl_words:
        if ew.startswith(opt_word) or opt_word.startswith(ew):
            return True
        if len(opt_word) >= 6 and len(ew) >= 6:
            common = sum(a == b for a, b in zip(opt_word, ew))
            if common / max(len(opt_word), len(ew)) >= 0.85:
                return True
    return False

# ── Core detector ─────────────────────────────────────────────────────────────

def detect_correct(q_text, opt_a, opt_b, opt_c, explanation):
    """
    Returns (letter, pass_num, confidence) or (None, 0, 0.0).
    letter    : "A", "B", "C"
    pass_num  : 1=explicit-letter, 2=exact-option, 3=stemmed, 4=numerical
    confidence: 0.0–1.0 (1=pass1, 0.9=pass2, 0.5–0.8=pass3, 0.4=pass4)
    """
    if not explanation or len(explanation.strip()) < 15:
        return None, 0, 0.0

    expl = explanation.strip()
    opts = {"A": (opt_a or "").strip(), "B": (opt_b or "").strip(), "C": (opt_c or "").strip()}

    # Pass 1: explicit letter mention
    for letter in ("A", "B", "C"):
        if re.search(
            rf'\b(correct\s+answer\s+is\s+{letter}|answer\s+is\s+{letter}|'
            rf'{letter}\s+is\s+(the\s+)?(correct|right|best|answer)|'
            rf'(choose|select|answer|option)\s*[:\s]+{letter}|'
            rf'{letter}\s+correctly|correctly\s+{letter}|'
            rf'choice\s+{letter}|{letter}\s+is\s+correct)\b',
            expl, re.IGNORECASE,
        ):
            return letter, 1, 1.0

    # Pass 2: exact option text in first sentence (only if option is long enough)
    first_sent = (re.split(r'(?<=[.!?])\s+', expl) or [""])[0].lower()
    for letter in ("A", "B", "C"):
        opt_clean = opts[letter].lower().rstrip(".").strip()
        if opt_clean and len(opt_clean) > 8 and opt_clean in first_sent:
            return letter, 2, 0.9

    # Pass 3: stemmed overlap (report only, don't auto-apply)
    focus = " ".join(re.split(r'(?<=[.!?])\s+', expl)[:3])
    expl_stems = set(_tokenize(focus))
    expl_raw   = re.findall(r'[a-z]+', focus.lower())
    scores = {}
    for letter in ("A", "B", "C"):
        opt_stems = list(_tokenize(opts[letter]))
        if not opt_stems:
            scores[letter] = 0.0
            continue
        matched = sum(1 for ow in opt_stems if ow in expl_stems or _fuzzy(ow, expl_raw))
        scores[letter] = matched / len(opt_stems)
    max_s = max(scores.values())
    if max_s >= 0.5:
        winners = [l for l, s in scores.items() if s == max_s]
        if len(winners) == 1:
            return winners[0], 3, max_s
        abs_m = {l: sum(1 for ow in _tokenize(opts[l]) if ow in expl_stems or _fuzzy(ow, expl_raw))
                 for l in winners}
        best = max(abs_m, key=abs_m.get)
        if abs_m[best] > min(abs_m.values()):
            return best, 3, max_s

    # Pass 4: numerical match
    def _nums(t):
        raw = re.findall(r'[\d,]+\.?\d*\s*(?:%|bps?|pp)?', t.lower())
        return {n.replace(',', '').strip() for n in raw if n.strip()}
    expl_nums = _nums(expl[:400])
    for letter in ("A", "B", "C"):
        opt_nums = _nums(opts[letter])
        if opt_nums and opt_nums <= expl_nums:
            return letter, 4, 0.4

    return None, 0, 0.0

# ── Supabase connection ───────────────────────────────────────────────────────

import requests as _requests
import ssl as _ssl

_SECRETS = None

def _load_secrets():
    global _SECRETS
    if _SECRETS is None:
        with open(SECRETS_PATH, "rb") as f:
            _SECRETS = tomllib.load(f)
    return _SECRETS

def _api_headers():
    s = _load_secrets()
    key = s["supabase"].get("SUPABASE_SERVICE_KEY") or s["supabase"]["SUPABASE_ANON_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

def _base_url():
    s = _load_secrets()
    return s["supabase"]["SUPABASE_URL"].rstrip("/") + "/rest/v1"

def _get(path, params=None):
    url = _base_url() + path
    r = _retry(lambda: _requests.get(url, headers=_api_headers(), params=params, timeout=30))
    r.raise_for_status()
    return r.json()

def _patch(path, payload):
    url = _base_url() + path
    r = _retry(lambda: _requests.patch(url, headers=_api_headers(), json=payload, timeout=30))
    r.raise_for_status()

def fetch_questions(source_filter=None):
    """Fetch all questions. Paginated via direct REST API (bypasses httpx SSL issue)."""
    rows = []
    offset = 0
    PAGE = 1000
    while True:
        params = {
            "select": "id,source,topic,question_en,option_a,option_b,option_c,correct_answer,explanation_en",
            "offset": offset,
            "limit": PAGE,
            "order": "id",
        }
        if source_filter:
            params["source"] = f"eq.{source_filter}"
        batch = _get("/questions", params)
        rows.extend(batch)
        print(f"  Fetched {len(rows)} questions…", end="\r", flush=True)
        if len(batch) < PAGE:
            break
        offset += PAGE
    print(f"  Fetched {len(rows)} questions total.     ")
    return rows

def connect():
    """Legacy helper — not used directly anymore."""
    s = _load_secrets()
    from supabase import create_client
    return create_client(
        s["supabase"]["SUPABASE_URL"],
        s["supabase"].get("SUPABASE_SERVICE_KEY") or s["supabase"]["SUPABASE_ANON_KEY"],
    )

# ── Main audit ────────────────────────────────────────────────────────────────

def audit_source(sb, source_label, questions, dry_run):
    print(f"\n{'='*60}")
    print(f"{source_label} — Cohérence correct_answer via explications")
    print(f"{'='*60}")
    print(f"  {len(questions)} questions à vérifier", flush=True)

    total = len(questions)
    no_expl = 0
    pass1_ok = pass1_wrong = 0
    pass2_ok = pass2_wrong = 0
    pass3_ok = pass3_wrong = 0
    pass4_ok = pass4_wrong = 0
    no_signal = 0
    updates = []

    # Show first N diffs
    shown = 0
    MAX_SHOW = 50

    for row in questions:
        expl = (row.get("explanation_en") or "").strip()
        if len(expl) < 15:
            no_expl += 1
            continue

        detected, pass_num, conf = detect_correct(
            row["question_en"],
            row["option_a"], row["option_b"], row["option_c"],
            expl,
        )

        if detected is None:
            no_signal += 1
            continue

        stored = (row.get("correct_answer") or "").strip().upper()
        match = (detected == stored)

        if pass_num == 1:
            if match: pass1_ok += 1
            else:     pass1_wrong += 1
        elif pass_num == 2:
            if match: pass2_ok += 1
            else:     pass2_wrong += 1
        elif pass_num == 3:
            if match: pass3_ok += 1
            else:     pass3_wrong += 1
        elif pass_num == 4:
            if match: pass4_ok += 1
            else:     pass4_wrong += 1

        # Auto-fix only for high-confidence passes (1 and 2)
        if not match and pass_num <= 2:
            updates.append({"id": row["id"], "correct_answer": detected})
            if shown < MAX_SHOW:
                print(f"  [P{pass_num} conf={conf:.2f}] {row['question_en'][:70]}")
                print(f"    stored={stored}  detected={detected}")
                print(f"    expl: {expl[:100]}")
                shown += 1
        elif not match and pass_num == 3 and shown < MAX_SHOW:
            print(f"  [P3 conf={conf:.2f} — log only] {row['question_en'][:70]}")
            print(f"    stored={stored}  detected={detected}")
            shown += 1

    print(f"\n  Sans explication : {no_expl} | Sans signal : {no_signal}")
    print(f"  Pass1 (lettre explicite) — OK: {pass1_ok} | WRONG: {pass1_wrong}")
    print(f"  Pass2 (texte exact)      — OK: {pass2_ok} | WRONG: {pass2_wrong}")
    print(f"  Pass3 (stemmed, log)     — OK: {pass3_ok} | WRONG: {pass3_wrong}")
    print(f"  Pass4 (numérique, log)   — OK: {pass4_ok} | WRONG: {pass4_wrong}")
    print(f"  Corrections haute confiance (P1+P2): {len(updates)}", flush=True)

    if not updates:
        return {"total": total, "fixed": 0, "p1_wrong": pass1_wrong, "p2_wrong": pass2_wrong}

    if dry_run:
        print(f"  [DRY RUN] {len(updates)} corrections non appliquées")
        return {"total": total, "fixed": len(updates), "p1_wrong": pass1_wrong, "p2_wrong": pass2_wrong}

    # Apply updates via REST API (bypasses httpx SSL issue)
    done = errors = 0
    for u in updates:
        qid = u["id"]
        payload = {k: v for k, v in u.items() if k != "id"}
        try:
            _patch(f"/questions?id=eq.{qid}", payload)
            done += 1
        except Exception as e:
            print(f"  [ERR] {qid}: {e}", flush=True)
            errors += 1
    print(f"  Appliqué: {done}/{len(updates)+errors} ({errors} erreurs)")
    return {"total": total, "fixed": done, "p1_wrong": pass1_wrong, "p2_wrong": pass2_wrong}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", choices=list(SOURCE_MAP.keys()) + ["all"], default="all")
    args = parser.parse_args()

    if args.source == "all":
        sources_to_run = list(SOURCE_MAP.items())
    else:
        sources_to_run = [(args.source, SOURCE_MAP[args.source])]

    all_results = {}
    for key, label in sources_to_run:
        print(f"\nFetch {label} …", flush=True)
        qs = fetch_questions(label)
        result = audit_source(None, label, qs, args.dry_run)
        all_results[label] = result

    print(f"\n{'='*60}")
    print("RÉSUMÉ GLOBAL")
    print(f"{'='*60}")
    total_q = total_fixed = total_p1 = total_p2 = 0
    for src, r in all_results.items():
        print(f"  {src:<15} total={r['total']:5d}  "
              f"p1_wrong={r['p1_wrong']:4d}  p2_wrong={r['p2_wrong']:4d}  "
              f"fixed={r['fixed']:4d}")
        total_q     += r["total"]
        total_fixed += r["fixed"]
        total_p1    += r["p1_wrong"]
        total_p2    += r["p2_wrong"]
    print(f"\n  Total questions vérifiées : {total_q}")
    print(f"  Mauvaises réponses P1     : {total_p1}")
    print(f"  Mauvaises réponses P2     : {total_p2}")
    print(f"  Corrections appliquées    : {total_fixed}")
    if args.dry_run:
        print("\n  [DRY RUN] Aucune modification en base.")
    else:
        print("\n  Toutes corrections appliquées en base.")


if __name__ == "__main__":
    main()
