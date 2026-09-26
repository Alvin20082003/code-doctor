"""
analyzers/performance.py

AST-based performance issue detector. No LLM.
Detects:
  - N+1 queries (DB/HTTP calls inside loops)
  - `in` membership test on a list inside a loop
  - Repeated identical function calls inside a loop
"""
import ast
from typing import Any


_DB_METHODS = frozenset({
    "query", "execute", "find", "find_one", "get",
    "filter", "fetch", "all", "first",
})

_HTTP_PAIRS = frozenset({("requests", "get"), ("requests", "post")})


def _call_key(node: ast.Call) -> str | None:
    """Return a stable string key for a Call node (func + args), or None."""
    try:
        return ast.dump(node)
    except Exception:
        return None


def _func_attr(node: ast.Call) -> tuple[str | None, str | None]:
    """Return (object_name, method_name) for an attribute call, or (None, name)."""
    func = node.func
    if isinstance(func, ast.Attribute):
        obj = func.value
        obj_name = obj.id if isinstance(obj, ast.Name) else None
        return obj_name, func.attr
    if isinstance(func, ast.Name):
        return None, func.id
    return None, None


def _is_n_plus_one_call(node: ast.Call) -> bool:
    obj_name, method_name = _func_attr(node)
    if method_name in _DB_METHODS:
        return True
    if obj_name and method_name:
        if (obj_name, method_name) in _HTTP_PAIRS:
            return True
    return False


def _collect_calls_in_body(body: list[ast.stmt]) -> list[ast.Call]:
    """Return all Call nodes that are DIRECT children (not nested in sub-loops)."""
    calls: list[ast.Call] = []
    for stmt in body:
        if isinstance(stmt, (ast.For, ast.While)):
            continue  # don't recurse into inner loops for this check
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                calls.append(node)
    return calls


def _walk_loops(
    stmts: list[ast.stmt],
    in_loop: bool,
    loop_line: int | None,
    findings: list[dict],
):
    for stmt in stmts:
        if isinstance(stmt, (ast.For, ast.While)):
            current_line = stmt.lineno
            # --- N+1 check ---
            body_calls = _collect_calls_in_body(stmt.body)
            for call in body_calls:
                if _is_n_plus_one_call(call):
                    _, method = _func_attr(call)
                    findings.append({
                        "type": "n_plus_one",
                        "severity": "high",
                        "line": getattr(call, "lineno", current_line),
                        "evidence": f"'{method}()' called inside a loop — N+1 query pattern",
                        "fix": "batch into one query using IN / JOIN / prefetch",
                    })

            # --- `in` membership on a list inside loop ---
            for node in ast.walk(stmt):
                if isinstance(node, (ast.For, ast.While)) and node is not stmt:
                    break  # handled when we recurse
            _check_in_list(stmt.body, current_line, findings)

            # --- repeated identical calls inside loop ---
            _check_repeated_calls(stmt.body, current_line, findings)

            # Recurse into loop body
            _walk_loops(stmt.body, in_loop=True, loop_line=current_line, findings=findings)

        elif isinstance(stmt, (ast.If, ast.With, ast.Try)):
            sub_bodies: list[list[ast.stmt]] = []
            if hasattr(stmt, "body"):
                sub_bodies.append(stmt.body)
            if hasattr(stmt, "orelse") and stmt.orelse:
                sub_bodies.append(stmt.orelse)
            if hasattr(stmt, "handlers"):
                for h in stmt.handlers:
                    sub_bodies.append(h.body)
            if hasattr(stmt, "finalbody"):
                sub_bodies.append(stmt.finalbody)
            for sub in sub_bodies:
                _walk_loops(sub, in_loop, loop_line, findings)


def _check_in_list(body: list[ast.stmt], loop_line: int, findings: list[dict]):
    """Detect `x in some_variable` comparisons that likely hit a list."""
    for stmt in body:
        if isinstance(stmt, (ast.For, ast.While)):
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Compare):
                for i, op in enumerate(node.ops):
                    if isinstance(op, ast.In):
                        comp = node.comparators[i]
                        if isinstance(comp, ast.Name):
                            findings.append({
                                "type": "list_membership_in_loop",
                                "severity": "medium",
                                "line": getattr(node, "lineno", loop_line),
                                "evidence": (
                                    f"`{ast.unparse(node.left)} in {ast.unparse(comp)}` "
                                    f"inside a loop — O(n) membership test"
                                ),
                                "fix": "convert to set for O(1) lookup",
                            })


def _check_repeated_calls(body: list[ast.stmt], loop_line: int, findings: list[dict]):
    """Detect the same function called with the same args multiple times inside a loop."""
    seen: dict[str, int] = {}
    for stmt in body:
        if isinstance(stmt, (ast.For, ast.While)):
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                key = _call_key(node)
                if key is None:
                    continue
                lineno = getattr(node, "lineno", loop_line)
                if key in seen:
                    findings.append({
                        "type": "repeated_call_in_loop",
                        "severity": "medium",
                        "line": lineno,
                        "evidence": (
                            f"identical call `{ast.unparse(node)}` repeated inside loop "
                            f"(first at line {seen[key]})"
                        ),
                        "fix": "compute once before the loop",
                    })
                else:
                    seen[key] = lineno


def _deduplicate(findings: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for f in findings:
        key = (f["type"], f["line"])
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def analyze_performance(code: str) -> list[dict]:
    """
    Analyze performance issues in the given Python source code.

    Returns a list of findings:
        [{"type": str, "severity": str, "line": int, "evidence": str, "fix": str}, ...]
    On any error, returns [].
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    except Exception:
        return []

    try:
        findings: list[dict] = []
        _walk_loops(tree.body, in_loop=False, loop_line=None, findings=findings)
        # Also walk function bodies
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _walk_loops(node.body, in_loop=False, loop_line=None, findings=findings)
        return _deduplicate(findings)
    except Exception:
        return []
