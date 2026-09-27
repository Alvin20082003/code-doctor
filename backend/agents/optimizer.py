"""
backend/agents/optimizer.py

Stub optimizer agent.
IBM Granite will be connected in a future step.
Keep the signature stable.
"""
from __future__ import annotations


async def optimize(code: str, analysis: dict) -> dict:
    """
    Placeholder optimizer.

    Parameters
    ----------
    code     : the original Python source submitted for analysis
    analysis : full analysis dict (time, space, performance, security)

    Returns
    -------
    A dict with at least "status".  When the optimizer is connected it will
    also return "optimized_code" and "explanation".
    """
    return {
        "status": "skipped",
        "note": "optimizer not connected yet",
    }
