"""
WIB CFA — Adaptive question selection.

Weighting logic:
  - Topic mastery 0-30%  → 5x  (critical weakness)
  - Topic mastery 30-50% → 3x  (weakness)
  - Topic mastery 50-70% → 2x  (needs work)
  - Topic mastery 70%+   → 1x  (strong)
  - Previously wrong question (any topic) → additional 2x multiplier
  - Unseen topic (no attempts yet) → treated as 0% mastery → 5x
"""

import random
from typing import Optional, List, Dict
from src.database import Database


def _topic_weight(mastery: float) -> int:
    if mastery < 30:
        return 5
    if mastery < 50:
        return 3
    if mastery < 70:
        return 2
    return 1


def get_weighted_questions(
    user_id: str,
    topic: Optional[str] = None,
    n: int = 20,
    db: Optional[Database] = None,
) -> List[Dict]:
    """
    Return `n` questions weighted by user profile.
    Combines topic-level mastery gradient with per-question wrong-answer boost.
    """
    if db is None:
        from src.database import get_db
        db = get_db()

    progress = db.get_progress(user_id)
    mastery_map: Dict[str, float] = {
        r["topic"]: float(r.get("mastery_pct") or 0) for r in progress
    }

    # Questions the user has answered incorrectly get an extra 2x boost
    wrong_ids: set = set(db.get_wrong_question_ids(user_id, limit=400))

    if topic and topic != "All":
        pool_size = max(n * 5, 100)
        pool = db.get_questions(topic=topic, n=pool_size)
    else:
        pool_size = min(n * 10, 700)
        pool = db.get_questions(n=pool_size)

    if not pool:
        return []

    weighted: List[Dict] = []
    for q in pool:
        mastery = mastery_map.get(q.get("topic", ""), 0.0)
        tw = _topic_weight(mastery)
        wrong_boost = 2 if q.get("id") in wrong_ids else 1
        total_weight = tw * wrong_boost
        for _ in range(total_weight):
            weighted.append(q)

    random.shuffle(weighted)

    seen: set = set()
    unique: List[Dict] = []
    for q in weighted:
        qid = q.get("id")
        if qid not in seen:
            seen.add(qid)
            unique.append(q)
        if len(unique) >= n:
            break

    # Pad if pool was too small (shouldn't happen with 7k+ questions)
    if len(unique) < n:
        for q in pool:
            if q.get("id") not in seen:
                unique.append(q)
                seen.add(q.get("id"))
            if len(unique) >= n:
                break

    return unique[:n]


def get_exam_questions(
    user_id: str,
    topic_counts: Dict[str, int],
    db: Optional[Database] = None,
) -> List[Dict]:
    """
    Fetch questions for exam simulator respecting CFA topic counts,
    but within each topic prioritizing questions the user has struggled with.
    """
    if db is None:
        from src.database import get_db
        db = get_db()

    wrong_ids: set = set(db.get_wrong_question_ids(user_id, limit=500))

    all_qs: List[Dict] = []
    for topic, n in topic_counts.items():
        pool = db.get_questions(topic=topic, n=max(n * 4, 40))
        if wrong_ids:
            wrong_in_topic = [q for q in pool if q["id"] in wrong_ids]
            others = [q for q in pool if q["id"] not in wrong_ids]
            random.shuffle(wrong_in_topic)
            random.shuffle(others)
            selected = (wrong_in_topic + others)[:n]
        else:
            random.shuffle(pool)
            selected = pool[:n]
        # Pad if topic has fewer questions than needed
        all_qs.extend(selected)

    random.shuffle(all_qs)
    return all_qs
