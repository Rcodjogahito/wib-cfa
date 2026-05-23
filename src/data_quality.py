"""
WIB CFA — Data Quality: answer consistency checker.

detect_correct(q_text, opt_a, opt_b, opt_c, explanation)
  Returns (letter, pass_num, confidence) or (None, 0, 0.0).

  Pass 1: explicit letter in explanation ("correct answer is B", "B is correct", etc.)
  Pass 2: exact option text in first sentence of explanation (len > 8)
  Pass 3: stemmed keyword overlap (≥ 0.5 score) — advisory only
  Pass 4: numeric match — advisory only

  Only passes 1 and 2 are used for auto-correction (high confidence).
"""

import re


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
    for suf in ('ations', 'ation', 'tions', 'tion', 'ments', 'ment', 'ness',
                'ing', 'ings', 'ed', 'ers', 'er', 'es', 's'):
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


def detect_correct(q_text: str, opt_a: str, opt_b: str, opt_c: str,
                   explanation: str):
    """
    Infer the correct answer from the explanation text.

    Returns (letter, pass_num, confidence):
      - letter     : "A", "B", "C" or None if no signal
      - pass_num   : 1=explicit-letter  2=exact-option  3=stemmed  4=numerical  0=no signal
      - confidence : 1.0 (pass1) | 0.9 (pass2) | 0.5–0.8 (pass3) | 0.4 (pass4) | 0.0
    """
    if not explanation or len(explanation.strip()) < 15:
        return None, 0, 0.0

    expl = explanation.strip()
    opts = {
        "A": (opt_a or "").strip(),
        "B": (opt_b or "").strip(),
        "C": (opt_c or "").strip(),
    }

    # Pass 1: explicit letter mention
    # Note: "option/choice/answer + space + letter" is intentionally excluded —
    # too many false positives ("option C shows", "option A for X") in CFA explanations.
    # Only colon-delimited forms ("option: A") and unambiguous verb forms are matched.
    for letter in ("A", "B", "C"):
        if re.search(
            rf'\b(correct\s+answer\s+is\s+{letter}|answer\s+is\s+{letter}|'
            rf'{letter}\s+is\s+(the\s+)?(correct|right|best|answer)|'
            rf'(choose|select)\s+{letter}\b|'
            rf'(answer|option|choice)\s*:\s*{letter}\b|'
            rf'{letter}\s+is\s+correct)\b',
            expl, re.IGNORECASE,
        ):
            return letter, 1, 1.0

    # Pass 2: exact option text in first sentence (len > 8 to avoid false positives)
    first_sent = (re.split(r'(?<=[.!?])\s+', expl) or [""])[0].lower()
    for letter in ("A", "B", "C"):
        opt_clean = opts[letter].lower().rstrip(".").strip()
        if opt_clean and len(opt_clean) > 8 and opt_clean in first_sent:
            return letter, 2, 0.9

    # Pass 3: stemmed overlap (advisory — do NOT auto-correct)
    focus = " ".join(re.split(r'(?<=[.!?])\s+', expl)[:3])
    expl_stems = set(_tokenize(focus))
    expl_raw = re.findall(r'[a-z]+', focus.lower())
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
        abs_m = {
            l: sum(1 for ow in _tokenize(opts[l]) if ow in expl_stems or _fuzzy(ow, expl_raw))
            for l in winners
        }
        best = max(abs_m, key=abs_m.get)
        if abs_m[best] > min(abs_m.values()):
            return best, 3, max_s

    # Pass 4: numerical match (advisory)
    def _nums(t):
        raw = re.findall(r'[\d,]+\.?\d*\s*(?:%|bps?|pp)?', t.lower())
        return {n.replace(',', '').strip() for n in raw if n.strip()}

    expl_nums = _nums(expl[:400])
    for letter in ("A", "B", "C"):
        opt_nums = _nums(opts[letter])
        if opt_nums and opt_nums <= expl_nums:
            return letter, 4, 0.4

    return None, 0, 0.0


def audit_questions(questions: list) -> dict:
    """
    Run consistency check on a list of question dicts.

    Returns {
      "p1_fixes":  [(id, stored, detected, snippet), ...],   # high-confidence
      "p2_fixes":  [(id, stored, detected, snippet), ...],   # high-confidence
      "p3_flags":  [(id, stored, detected, snippet), ...],   # advisory
      "no_signal": int,
      "ok":        int,
    }
    """
    p1_fixes = []
    p2_fixes = []
    p3_flags = []
    no_signal = 0
    ok = 0

    for row in questions:
        expl = (row.get("explanation_en") or "").strip()
        if len(expl) < 15:
            no_signal += 1
            continue

        detected, pass_num, conf = detect_correct(
            row.get("question_en", ""),
            row.get("option_a", ""),
            row.get("option_b", ""),
            row.get("option_c", ""),
            expl,
        )
        if detected is None:
            no_signal += 1
            continue

        stored = (row.get("correct_answer") or "").strip().upper()
        snippet = f"Q: {row.get('question_en','')[:60]}… | Expl: {expl[:80]}…"

        if detected == stored:
            ok += 1
        elif pass_num == 1:
            p1_fixes.append((row["id"], stored, detected, snippet))
        elif pass_num == 2:
            p2_fixes.append((row["id"], stored, detected, snippet))
        elif pass_num == 3:
            p3_flags.append((row["id"], stored, detected, snippet))
        else:
            ok += 1  # pass 4 differences are too weak to be advisory

    return {
        "p1_fixes":  p1_fixes,
        "p2_fixes":  p2_fixes,
        "p3_flags":  p3_flags,
        "no_signal": no_signal,
        "ok":        ok,
    }
