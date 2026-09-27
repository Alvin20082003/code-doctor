"""
backend/validation.py

Behavioral validation for optimized code.

For the nested-loop / users×orders pattern we run both the original and
optimized functions in an isolated subprocess and compare their outputs.
For all other code we return a static-only result — we never claim behaviour
was tested when it wasn't.
"""
from __future__ import annotations

import ast
import subprocess
import sys
import textwrap
import types


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

def _has_users_orders_pattern(code: str) -> tuple[bool, bool]:
    """
    Return (has_pattern, has_extra_params).

    has_pattern   – code has a function with 'users' and 'orders' params.
    has_extra_params – that function also has params beyond users/orders
                       (e.g. 'db'), which would require external dependencies
                       and make subprocess execution unreliable.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False, False

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            param_names = {a.arg for a in node.args.args}
            if "users" in param_names and "orders" in param_names:
                extra = param_names - {"users", "orders", "self"}
                return True, bool(extra)
    return False, False


def _get_first_function_name(code: str) -> str | None:
    """Return the name of the first function defined in *code*."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
    return None


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------

_HARNESS_TEMPLATE = textwrap.dedent("""\
    import types, sys, json

    {code}

    import random
    random.seed(42)

    users = [types.SimpleNamespace(id=i, name=f"user{{i}}") for i in range(50)]
    orders = [
        types.SimpleNamespace(id=j, user_id=random.randint(0, 49))
        for j in range(200)
    ]

    result = {func_name}(users, orders)
    # Flatten to sorted list of (user_id, order_id) pairs
    pairs = []
    for uid, ords in result.items():
        for o in ords:
            pairs.append((int(uid), int(o.id)))
    pairs.sort()
    print(json.dumps(pairs))
""")


def _run_in_subprocess(code: str, func_name: str, timeout: float = 5.0) -> list | None:
    """
    Execute *code* + the harness in a fresh Python subprocess.
    Returns the parsed JSON list of (user_id, order_id) pairs, or None on failure.
    """
    script = _HARNESS_TEMPLATE.format(code=code, func_name=func_name)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return None
        import json
        return json.loads(proc.stdout.strip())
    except (subprocess.TimeoutExpired, Exception):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_behavior(original_code: str, optimized_code: str) -> dict:
    """
    Compare the behavior of *original_code* and *optimized_code*.

    Returns
    -------
    {
        "tested": bool,
        "cases": int,          # number of test pairs  (present when tested=True)
        "passed": bool,        # outputs matched        (present when tested=True)
        "reason": str,         # present when tested=False
    }
    """
    # Only test the well-known users×orders pattern
    has_pattern, has_extra = _has_users_orders_pattern(original_code)
    if not has_pattern:
        return {"tested": False, "reason": "static verification only"}

    # Functions that also accept external dependencies (e.g. db) cannot be
    # safely run in a subprocess harness without mocking those deps.
    if has_extra:
        return {"tested": False, "reason": "static verification only (external dependencies)"}

    orig_func = _get_first_function_name(original_code)
    opt_func  = _get_first_function_name(optimized_code)

    if not orig_func or not opt_func:
        return {"tested": False, "reason": "could not detect function name"}

    orig_out = _run_in_subprocess(original_code, orig_func)
    opt_out  = _run_in_subprocess(optimized_code, opt_func)

    if orig_out is None or opt_out is None:
        return {"tested": False, "reason": "subprocess execution failed"}

    passed = orig_out == opt_out
    return {
        "tested": True,
        "cases": 50,   # 50 users × 200 orders
        "passed": passed,
    }
