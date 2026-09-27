"""
backend/scoring.py

Scale-aware scoring of an analysis result.
No LLM dependency — pure arithmetic.
"""
from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------------------
# Time-complexity score table (max 35 points)
# ---------------------------------------------------------------------------
_TIME_SCORE: dict[str, int] = {
    "O(1)":        35,
    "O(log n)":    35,
    "O(n)":        30,
    "O(n+m)":      28,
    "O(n log n)":  25,
    "O(n*m)":       5,
    "O(n^2)":       5,
    "O(n^2 log n)": 3,
    "O(n^3)":       2,
    "O(2^n)":       0,
    "unknown":     15,
}

# Space-complexity score table (max 15 points)
_SPACE_SCORE: dict[str, int] = {
    "O(1)":        15,
    "O(log n)":    15,
    "O(n)":        10,
    "O(n+m)":      10,
    "O(n log n)":   8,
    "O(n*m)":       3,
    "O(n^2)":       3,
    "O(n^2 log n)": 2,
    "O(n^3)":       2,
    "O(2^n)":       2,
    "unknown":      7,
}


def scale_score(
    time: dict,
    space: dict,
    perf_findings: list[dict],
    sec_findings: list[dict],
) -> dict:
    """
    Compute an overall 0-100 score from analyzer outputs.

    Parameters
    ----------
    time : result of analyze_time()
    space : result of analyze_space()
    perf_findings : result of analyze_performance()
    sec_findings  : result of analyze_security()

    Returns
    -------
    {
        "score": int,              # 0-100
        "breakdown": {
            "time": int,           # 0-35
            "space": int,          # 0-15
            "performance": int,    # 0-25
            "security": int,       # 0-25
        }
    }
    """
    time_pts = _TIME_SCORE.get(time.get("complexity", "unknown"), 15)
    space_pts = _SPACE_SCORE.get(space.get("complexity", "unknown"), 7)

    # Performance (25 pts): -10 per high, -5 per medium
    perf_pts = 25
    for f in perf_findings:
        sev = f.get("severity", "")
        if sev == "high":
            perf_pts -= 10
        elif sev == "medium":
            perf_pts -= 5
    perf_pts = max(perf_pts, 0)

    # Security (25 pts): -10 per high, -5 per medium
    sec_pts = 25
    for f in sec_findings:
        sev = f.get("severity", "")
        if sev == "high":
            sec_pts -= 10
        elif sev == "medium":
            sec_pts -= 5
    sec_pts = max(sec_pts, 0)

    total = time_pts + space_pts + perf_pts + sec_pts

    # -----------------------------------------------------------------------
    # Security hard caps
    # Any high-severity security finding → cap at 40.
    # Any medium-severity security finding (no high) → cap at 70.
    # -----------------------------------------------------------------------
    capped_reason: str = ""
    has_high_sec    = any(f.get("severity") in ("high", "critical") for f in sec_findings)
    has_medium_sec  = any(f.get("severity") == "medium"             for f in sec_findings)

    if has_high_sec and total > 40:
        total = 40
        capped_reason = "Capped at 40: critical security issues present"
    elif has_medium_sec and not has_high_sec and total > 70:
        total = 70
        capped_reason = "Capped at 70: medium security issues present"

    return {
        "score": total,
        "breakdown": {
            "time": time_pts,
            "space": space_pts,
            "performance": perf_pts,
            "security": sec_pts,
        },
        "capped_reason": capped_reason,
    }


# ---------------------------------------------------------------------------
# Growth curve
# ---------------------------------------------------------------------------

_N_VALUES = [10, 100, 1_000, 10_000, 100_000]
_OPS_CAP = 1e15


def growth_curve(complexity: str) -> list[dict]:
    """
    Return [{"n": n, "ops": value}] for each n in [10, 100, 1000, 10000, 100000].

    m is treated as equal to n.
    All ops are capped at 1e15 to avoid overflow (especially O(2^n)).
    Unknown complexity returns an empty list.
    """
    if complexity == "unknown":
        return []

    points: list[dict] = []
    for n in _N_VALUES:
        ops = _ops(complexity, n)
        ops = min(ops, _OPS_CAP)
        points.append({"n": n, "ops": ops})
    return points


def _ops(complexity: str, n: int) -> float:
    """Map a complexity string to a floating-point operation count for n."""
    c = complexity
    if c in ("O(1)",):
        return 1.0
    if c in ("O(log n)",):
        return math.log2(n)
    if c in ("O(n)",):
        return float(n)
    if c in ("O(n+m)",):
        return float(n + n)          # m = n
    if c in ("O(n log n)",):
        return n * math.log2(n)
    if c in ("O(n*m)",):
        return float(n * n)          # m = n
    if c in ("O(n^2)",):
        return float(n ** 2)
    if c in ("O(n^2 log n)",):
        return (n ** 2) * math.log2(n)
    if c in ("O(n^3)",):
        return float(n ** 3)
    if c in ("O(2^n)",):
        # Cap early to avoid OverflowError — 2^1000 is astronomically large
        if n >= 53:                  # 2^53 ≈ 9e15, already over cap
            return _OPS_CAP
        return min(2.0 ** n, _OPS_CAP)
    # Fallback for anything unrecognised
    return float(n)
