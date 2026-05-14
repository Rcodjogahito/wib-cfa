"""
WIB CFA — Adaptive question selection.
Weak topics (mastery < threshold) are weighted 3x in selection.
"""

import random
from typing import Optional, List, Dict
from src.database import Database


def get_weighted_questions(
    user_id: str,
    topic: Optional[str] = None,
    n: int = 20,
    db: Optional[Database] = None,
) -> List[Dict]:
    """
    Return `n` questions weighted by user weakness.
    Topics where mastery < 50% get 3x weight; others 1x.
    Single DB call for the full pool (efficient with large question banks).
    """
    if db is None:
        from src.database import get_db
        db = get_db()

    progress = db.get_progress(user_id)
    mastery_map: Dict[str, float] = {
        r["topic"]: float(r.get("mastery_pct") or 0) for r in progress
    }

    if topic and topic != "All":
        return db.get_questions(topic=topic, n=n)

    # Fetch a single mixed pool (larger than needed for shuffle variety)
    pool_size = min(n * 10, 600)
    all_qs = db.get_questions(n=pool_size)

    if not all_qs:
        return []

    # Build weighted list: weak topics 3x, strong topics 1x
    weighted: List[Dict] = []
    for q in all_qs:
        mastery = mastery_map.get(q.get("topic", ""), 0.0)
        weight = 3 if mastery < 50 else 1
        for _ in range(weight):
            weighted.append(q)

    random.shuffle(weighted)

    # Deduplicate while preserving weighted shuffle order
    seen: set = set()
    unique: List[Dict] = []
    for q in weighted:
        qid = q.get("id")
        if qid not in seen:
            seen.add(qid)
            unique.append(q)
        if len(unique) >= n:
            break

    # Pad if under target (rare with large banks)
    if len(unique) < n:
        for q in all_qs:
            if q.get("id") not in seen:
                unique.append(q)
                seen.add(q.get("id"))
            if len(unique) >= n:
                break

    return unique[:n]
