"""
WIB CFA — Progress analytics helpers.
"""

from typing import Dict, List, Optional
from src.auth import CFA_TOPICS


def compute_mastery_map(progress_rows: List[Dict]) -> Dict[str, float]:
    """Return {topic: mastery_pct} for all 10 CFA topics (0.0 if not started)."""
    result = {t: 0.0 for t in CFA_TOPICS}
    for row in progress_rows:
        topic = row.get("topic")
        if topic in result:
            result[topic] = float(row.get("mastery_pct") or 0.0)
    return result


def count_mastered(mastery_map: Dict[str, float], threshold: float = 70.0) -> int:
    return sum(1 for v in mastery_map.values() if v >= threshold)


def weak_topics(mastery_map: Dict[str, float], threshold: float = 50.0) -> List[str]:
    return [t for t, v in mastery_map.items() if v < threshold]


def readiness_score(mastery_map: Dict[str, float]) -> float:
    """Weighted readiness estimate based on CFA exam topic weights."""
    weights = {
        "Ethics & Professional Standards": 0.15,
        "Quantitative Methods": 0.10,
        "Economics": 0.10,
        "Financial Statement Analysis": 0.13,
        "Corporate Issuers": 0.09,
        "Equity Investments": 0.11,
        "Fixed Income": 0.11,
        "Derivatives": 0.06,
        "Alternative Investments": 0.06,
        "Portfolio Management": 0.09,
    }
    score = sum(mastery_map.get(t, 0.0) * w for t, w in weights.items())
    return round(score, 1)
