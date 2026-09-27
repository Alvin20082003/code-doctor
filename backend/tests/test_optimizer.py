"""
tests/test_optimizer.py

Tests for agents/optimizer.py.

ALL LLM calls are mocked — tests must not contact Ollama or any external service.
"""
from __future__ import annotations

import ast
import pathlib
import textwrap
from unittest.mock import AsyncMock, patch

import pytest

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers — realistic optimized code for the nested_loop fixture
# ---------------------------------------------------------------------------

_GOOD_OPTIMIZED = textwrap.dedent("""\
    from dataclasses import dataclass
    from typing import List

    @dataclass
    class User:
        id: int
        name: str

    @dataclass
    class Order:
        id: int
        user_id: int
        amount: float

    def match_orders(users: List[User], orders: List[Order]) -> dict:
        # Build a dict keyed by user_id in one pass — O(m)
        orders_by_user: dict = {}
        for order in orders:
            orders_by_user.setdefault(order.user_id, []).append(order)
        # Look up each user's orders in O(1) — O(n) total
        result = {}
        for user in users:
            result[user.id] = orders_by_user.get(user.id, [])
        return result
""")

_BAD_OPTIMIZED = textwrap.dedent("""\
    from dataclasses import dataclass
    from typing import List

    @dataclass
    class User:
        id: int
        name: str

    @dataclass
    class Order:
        id: int
        user_id: int
        amount: float

    def match_orders(users: List[User], orders: List[Order]) -> dict:
        # still nested loop — not fixed
        result = {}
        for user in users:
            user_orders = []
            for order in orders:
                if user.id == order.user_id:
                    user_orders.append(order)
            result[user.id] = user_orders
        return result
""")

_SYNTAX_ERROR_CODE = "def match_orders(users, orders:\n    pass"


def _make_llm_response(code: str, explanation: str = "Fixed the nested loop.") -> str:
    return f"```python\n{code}\n```\nEXPLANATION: {explanation}"


# ---------------------------------------------------------------------------
# Analysis fixture used across tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def nested_loop_analysis():
    from analyzers.complexity import analyze_time, analyze_space
    from analyzers.performance import analyze_performance
    from analyzers.security import analyze_security
    code = _read("nested_loop.py")
    return {
        "time":        analyze_time(code),
        "space":       analyze_space(code),
        "performance": analyze_performance(code),
        "security":    analyze_security(code),
    }


# ---------------------------------------------------------------------------
# 1. LLM returns good code on first attempt → status "verified"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_optimize_verified_on_first_attempt(nested_loop_analysis):
    from agents.optimizer import optimize

    good_response = _make_llm_response(_GOOD_OPTIMIZED)

    with patch("agents.optimizer.generate", new=AsyncMock(return_value=good_response)):
        result = await optimize(_read("nested_loop.py"), nested_loop_analysis)

    assert result["status"] == "verified", (
        f"Expected 'verified', got '{result['status']}'. Note: {result.get('note')}"
    )
    assert result["optimized_code"] is not None
    assert result["attempts"] == 1
    assert result["before"]["time"] in ("O(n*m)", "O(n^2)")
    after_time = result["after"].get("time", "unknown")
    from analyzers.complexity import _COMPLEXITY_RANK
    assert _COMPLEXITY_RANK.get(after_time, 99) < _COMPLEXITY_RANK.get(result["before"]["time"], 0), (
        f"After complexity {after_time} should rank lower than before {result['before']['time']}"
    )
    assert result["explanation"] != ""
    assert "syntax_ok" in result["validation"]
    assert result["validation"]["syntax_ok"] is True
    assert result["validation"]["complexity_improved"] is True


# ---------------------------------------------------------------------------
# 2. First attempt bad, second attempt good → still "verified", attempts=2
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_optimize_verified_on_second_attempt(nested_loop_analysis):
    from agents.optimizer import optimize

    bad_response  = _make_llm_response(_BAD_OPTIMIZED)
    good_response = _make_llm_response(_GOOD_OPTIMIZED)

    call_count = 0

    async def side_effect(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        return bad_response if call_count == 1 else good_response

    with patch("agents.optimizer.generate", new=side_effect):
        result = await optimize(_read("nested_loop.py"), nested_loop_analysis)

    assert result["status"] == "verified"
    assert result["attempts"] == 2


# ---------------------------------------------------------------------------
# 3. Both attempts bad → status "rejected" (code returned, not verified)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_optimize_rejected_when_both_attempts_fail(nested_loop_analysis):
    from agents.optimizer import optimize

    bad_response = _make_llm_response(_BAD_OPTIMIZED)

    with patch("agents.optimizer.generate", new=AsyncMock(return_value=bad_response)):
        result = await optimize(_read("nested_loop.py"), nested_loop_analysis)

    assert result["status"] == "rejected", (
        f"Expected 'rejected', got '{result['status']}'"
    )
    assert result["optimized_code"] is not None  # code returned but not verified
    assert result["attempts"] == 2
    assert "note" in result and result["note"] != ""
    assert result["validation"]["complexity_improved"] is False


# ---------------------------------------------------------------------------
# 4. LLM unreachable → status "failed"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_optimize_failed_when_llm_unreachable(nested_loop_analysis):
    from agents.optimizer import optimize

    async def fail(_prompt: str) -> str:
        raise RuntimeError("Ollama unreachable at http://127.0.0.1:11434")

    with patch("agents.optimizer.generate", new=fail):
        result = await optimize(_read("nested_loop.py"), nested_loop_analysis)

    assert result["status"] == "failed"
    assert result["optimized_code"] is None
    assert "AI optimization unavailable" in result["note"]
    assert result["attempts"] == 1


# ---------------------------------------------------------------------------
# 5. LLM returns syntax-error code → retries, then rejects
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_optimize_handles_syntax_error_in_llm_output(nested_loop_analysis):
    from agents.optimizer import optimize

    bad_response = _make_llm_response(_SYNTAX_ERROR_CODE)

    with patch("agents.optimizer.generate", new=AsyncMock(return_value=bad_response)):
        result = await optimize(_read("nested_loop.py"), nested_loop_analysis)

    # After both attempts, syntax error means no valid code was ever produced
    # → either "failed" (no parseable code at all) or "rejected"
    assert result["status"] in ("failed", "rejected")


# ---------------------------------------------------------------------------
# 6. LLM returns no code block → eventually "failed"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_optimize_handles_no_code_block(nested_loop_analysis):
    from agents.optimizer import optimize

    with patch("agents.optimizer.generate", new=AsyncMock(return_value="Sure! Here is some advice...")):
        result = await optimize(_read("nested_loop.py"), nested_loop_analysis)

    assert result["status"] == "failed"
    assert result["optimized_code"] is None


# ---------------------------------------------------------------------------
# 7. Return schema completeness
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_optimize_result_has_required_keys(nested_loop_analysis):
    from agents.optimizer import optimize

    good_response = _make_llm_response(_GOOD_OPTIMIZED)

    with patch("agents.optimizer.generate", new=AsyncMock(return_value=good_response)):
        result = await optimize(_read("nested_loop.py"), nested_loop_analysis)

    required = {"status", "optimized_code", "explanation", "attempts",
                "before", "after", "after_findings", "validation", "note"}
    missing = required - set(result.keys())
    assert not missing, f"Missing keys: {missing}"

    assert isinstance(result["attempts"], int)
    assert isinstance(result["before"], dict)
    assert "time" in result["before"]
    assert "space" in result["before"]


# ---------------------------------------------------------------------------
# 8. hero_endpoint.py — verify analyzers find all four issues
# ---------------------------------------------------------------------------

def test_hero_endpoint_scores_below_30():
    from analyzers.complexity import analyze_time, analyze_space
    from analyzers.performance import analyze_performance
    from analyzers.security import analyze_security
    from scoring import scale_score

    code = _read("hero_endpoint.py")
    t = analyze_time(code)
    s = analyze_space(code)
    p = analyze_performance(code)
    sec = analyze_security(code)
    result = scale_score(t, s, p, sec)

    assert result["score"] < 30, (
        f"hero_endpoint should score below 30, got {result['score']}. "
        f"time={t['complexity']} perf={len(p)} sec={len(sec)}"
    )
    # Verify all four issue types present
    perf_types = {f["type"] for f in p}
    sec_cats   = {f["category"] for f in sec}
    assert "n_plus_one" in perf_types, f"N+1 not detected. perf={p}"
    assert "sql_injection" in sec_cats, f"SQL injection not detected. sec={sec}"
    assert "hardcoded_secret" in sec_cats, f"Hardcoded secret not detected. sec={sec}"


# ---------------------------------------------------------------------------
# 9. _build_fix_hints covers expected patterns
# ---------------------------------------------------------------------------

def test_build_fix_hints_nested_loop():
    from agents.optimizer import _build_fix_hints
    analysis = {
        "time":        {"complexity": "O(n*m)", "confidence": "high", "evidence": []},
        "space":       {"complexity": "O(n^2)", "confidence": "high", "evidence": []},
        "performance": [{"type": "n_plus_one", "severity": "high", "line": 5,
                         "evidence": "query() in loop", "fix": "batch"}],
        "security":    [{"severity": "high", "category": "sql_injection",
                         "line": 3, "evidence": "f-string", "fix": "parameterize"},
                        {"severity": "high", "category": "hardcoded_secret",
                         "line": 1, "evidence": "API_KEY", "fix": "env var"}],
    }
    hints = _build_fix_hints(analysis)
    assert "NESTED LOOP FIX" in hints
    assert "N+1 QUERY FIX" in hints
    assert "SQL INJECTION FIX" in hints
    assert "HARDCODED SECRET FIX" in hints


# ---------------------------------------------------------------------------
# 10. _parse_response extracts code + explanation
# ---------------------------------------------------------------------------

def test_parse_response_extracts_code_and_explanation():
    from agents.optimizer import _parse_response
    text = (
        "Here is the fix:\n"
        "```python\ndef foo():\n    return 42\n```\n"
        "EXPLANATION: We replaced the loop with a dict lookup."
    )
    code, explanation = _parse_response(text)
    assert code == "def foo():\n    return 42"
    assert "dict lookup" in explanation


def test_parse_response_returns_none_when_no_code_block():
    from agents.optimizer import _parse_response
    code, explanation = _parse_response("No code here, just text.")
    assert code is None
    assert explanation == ""


# ---------------------------------------------------------------------------
# 11. validation.py behavioral check
# ---------------------------------------------------------------------------

def test_behavioral_check_nested_loop_fixture():
    from validation import check_behavior
    original  = _read("nested_loop.py")
    optimized = _read("optimized_match.py")
    result = check_behavior(original, optimized)
    assert result["tested"] is True
    assert result["passed"] is True
    assert result["cases"] == 50


def test_behavioral_check_returns_static_for_non_pattern():
    from validation import check_behavior
    simple = "def process(items):\n    return [x*2 for x in items]\n"
    result = check_behavior(simple, simple)
    assert result["tested"] is False
    assert "reason" in result
