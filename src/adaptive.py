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
    """
    if db is None:
        from src.database import get_db
        db = get_db()

    # Fetch mastery per topic
    progress = db.get_progress(user_id)
    mastery_map: Dict[str, float] = {r["topic"]: float(r.get("mastery_pct") or 0) for r in progress}

    if topic and topic != "All":
        # Single topic requested — return randomly from that topic
        all_qs = db.get_questions(topic=topic)
        random.shuffle(all_qs)
        return all_qs[:n]

    # Multi-topic weighted selection
    from src.auth import CFA_TOPICS
    pools: Dict[str, List[Dict]] = {}
    for t in CFA_TOPICS:
        qs = db.get_questions(topic=t)
        if qs:
            pools[t] = qs

    weighted: List[Dict] = []
    for t, qs in pools.items():
        mastery = mastery_map.get(t, 0.0)
        weight = 3 if mastery < 50 else 1
        weighted.extend(qs * weight)

    random.shuffle(weighted)
    # Deduplicate by id while preserving shuffle order
    seen = set()
    unique: List[Dict] = []
    for q in weighted:
        qid = q.get("id")
        if qid not in seen:
            seen.add(qid)
            unique.append(q)
        if len(unique) >= n:
            break

    # Pad with random if not enough
    if len(unique) < n:
        all_ids = seen
        for t, qs in pools.items():
            for q in qs:
                if q.get("id") not in all_ids:
                    unique.append(q)
                    all_ids.add(q.get("id"))
                if len(unique) >= n:
                    break
            if len(unique) >= n:
                break

    return unique[:n]
