"""
analyzers/complexity.py

AST-based time and space complexity analyzer.
No LLM — pure static analysis using Python's ast module.
"""
import ast
from typing import Any


_EMPTY = {"complexity": "unknown", "confidence": "low", "evidence": []}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_func_name(node: ast.AST) -> str | None:
    """Return the dotted name of a Call node's function, or None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _iter_name(node: ast.AST) -> str | None:
    """Return a stable string key for the iterable of a For loop."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts = []
        n: ast.AST = node
        while isinstance(n, ast.Attribute):
            parts.append(n.attr)
            n = n.value
        if isinstance(n, ast.Name):
            parts.append(n.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):
        return None  # treat call iterables as distinct
    return None


def _collect_for_while_nesting(
    body: list[ast.stmt],
    current_depth: int,
    iterables: list[str | None],
    findings: list[dict],
) -> int:
    """
    Walk a list of statements, tracking nesting depth of For/While loops.
    Returns the maximum depth reached within this body.
    """
    max_depth = current_depth
    for stmt in body:
        if isinstance(stmt, (ast.For, ast.While)):
            iterable_key: str | None = None
            if isinstance(stmt, ast.For):
                iterable_key = _iter_name(stmt.iter)
            new_depth = current_depth + 1
            new_iterables = iterables + [iterable_key]
            inner_max = _collect_for_while_nesting(
                stmt.body, new_depth, new_iterables, findings
            )
            max_depth = max(max_depth, inner_max)
        elif isinstance(stmt, (ast.If, ast.With, ast.Try, ast.ExceptHandler)):
            sub_bodies = []
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
                d = _collect_for_while_nesting(sub, current_depth, iterables, findings)
                max_depth = max(max_depth, d)
    return max_depth


def _has_in_list_check(node: ast.AST) -> bool:
    """Return True if node contains `x in some_name` where some_name might be a list."""
    for child in ast.walk(node):
        if isinstance(child, ast.Compare):
            for op in child.ops:
                if isinstance(op, ast.In):
                    # Check comparators are names (variables), not sets/dicts
                    for comp in child.comparators:
                        if isinstance(comp, ast.Name):
                            return True
    return False


def _halves_variable(node: ast.stmt) -> bool:
    """Return True if a While loop body contains //= 2 or >>= 1 or mid-index pattern."""
    for child in ast.walk(node):
        # AugAssign: x //= 2  or  x >>= 1
        if isinstance(child, ast.AugAssign):
            if isinstance(child.op, ast.FloorDiv):
                if isinstance(child.value, ast.Constant) and child.value.value == 2:
                    return True
            if isinstance(child.op, ast.RShift):
                if isinstance(child.value, ast.Constant) and child.value.value == 1:
                    return True
        # Assign: mid = (lo + hi) // 2
        if isinstance(child, ast.Assign):
            if isinstance(child.value, ast.BinOp) and isinstance(
                child.value.op, ast.FloorDiv
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# Per-function analysis
# ---------------------------------------------------------------------------

class _FuncAnalyzer(ast.NodeVisitor):
    """Visits a single function definition and computes time/space complexity."""

    def __init__(self, func_name: str):
        self.func_name = func_name
        self.time_evidence: list[dict] = []
        self.space_evidence: list[dict] = []
        self.time_complexity = "O(1)"
        self.space_complexity = "O(1)"
        self.time_confidence = "high"
        self.space_confidence = "high"

    # -- loop depth analysis --------------------------------------------------

    def _analyze_loops(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Walk the function body for nested loops and derive time complexity."""
        self._walk_body(func_node.body, depth=0, iterables=[])

    def _walk_body(
        self,
        stmts: list[ast.stmt],
        depth: int,
        iterables: list[str | None],
    ):
        for stmt in stmts:
            if isinstance(stmt, (ast.For, ast.While)):
                loop_line = stmt.lineno
                is_while = isinstance(stmt, ast.While)
                iterable_key: str | None = None

                if isinstance(stmt, ast.For):
                    iterable_key = _iter_name(stmt.iter)

                # Check if while loop is a binary-search style halving
                if is_while and _halves_variable(stmt):
                    self._update_time("O(log n)", "medium",
                                      {"line": loop_line,
                                       "reason": "while loop halving a variable — O(log n)"})
                    self._walk_body(stmt.body, depth + 1, iterables + [iterable_key])
                    continue

                new_iterables = iterables + [iterable_key]
                new_depth = depth + 1

                # Check for `x in list_var` inside this loop body
                in_list_factor = _has_in_list_check(stmt)

                if new_depth == 2:
                    outer_iter = iterables[-1] if iterables else None
                    if (
                        outer_iter is not None
                        and iterable_key is not None
                        and outer_iter == iterable_key
                    ):
                        complexity = "O(n^2)"
                        reason = (
                            f"nested loop over same iterable '{iterable_key}' — O(n^2)"
                        )
                    else:
                        complexity = "O(n*m)"
                        reason = (
                            f"nested loop over different iterables "
                            f"('{outer_iter}' vs '{iterable_key}') — O(n*m)"
                        )
                    self._update_time(complexity, "high",
                                      {"line": loop_line, "reason": reason})
                elif new_depth >= 3:
                    self._update_time("O(n^3)", "high",
                                      {"line": loop_line,
                                       "reason": "triple-nested loop — O(n^3)"})
                else:
                    # depth == 1
                    self._update_time("O(n)", "high",
                                      {"line": loop_line,
                                       "reason": "single loop — O(n)"})

                if in_list_factor and new_depth == 1:
                    self._update_time("O(n^2)", "medium",
                                      {"line": loop_line,
                                       "reason": "`x in list` inside a loop adds O(n) factor"})

                # Check for sorted / .sort() inside loop body
                for child in ast.walk(stmt):
                    if isinstance(child, ast.Call):
                        name = _get_func_name(child.func)
                        if name in ("sorted", "sort"):
                            self._update_time(
                                "O(n^2 log n)", "medium",
                                {"line": getattr(child, "lineno", loop_line),
                                 "reason": "sort inside a loop — O(n * n log n)"},
                            )

                self._walk_body(stmt.body, new_depth, new_iterables)

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
                    self._walk_body(sub, depth, iterables)

    # -- sort calls at top level ----------------------------------------------

    def _check_top_level_sort(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                name = _get_func_name(node.func)
                if name in ("sorted", "sort"):
                    # Only flag if NOT inside a loop (handled above)
                    self._update_time(
                        "O(n log n)", "high",
                        {"line": getattr(node, "lineno", 0),
                         "reason": "sorted() / .sort() call — O(n log n)"},
                    )
                    return

    # -- recursion analysis ---------------------------------------------------

    def _analyze_recursion(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        self_calls: list[int] = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                name = _get_func_name(node.func)
                if name == self.func_name:
                    self_calls.append(getattr(node, "lineno", 0))

        if len(self_calls) >= 2:
            self._update_time(
                "O(2^n)", "high",
                {"line": self_calls[0],
                 "reason": f"function '{self.func_name}' calls itself {len(self_calls)} times — O(2^n)"},
            )
            # Recursion = O(n) stack space
            self._update_space(
                "O(n)", "high",
                {"line": self_calls[0],
                 "reason": f"recursion depth O(n) for '{self.func_name}'"},
            )
        elif len(self_calls) == 1:
            self._update_time(
                "O(n)", "medium",
                {"line": self_calls[0],
                 "reason": f"function '{self.func_name}' calls itself once — O(n)"},
            )
            self._update_space(
                "O(n)", "high",
                {"line": self_calls[0],
                 "reason": f"recursion depth O(n) for '{self.func_name}'"},
            )

    # -- space complexity analysis --------------------------------------------

    def _analyze_space(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        """
        Look for growing data structures:
          - list/dict/set appended inside a loop -> O(n)
          - comprehensions over input -> O(n)
          - structures built inside nested loops -> O(n^2)
        """
        self._walk_space(func_node.body, depth=0)

        # Comprehensions
        for node in ast.walk(func_node):
            if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                self._update_space(
                    "O(n)", "high",
                    {"line": getattr(node, "lineno", 0),
                     "reason": "comprehension over input — O(n) space"},
                )

    def _walk_space(self, stmts: list[ast.stmt], depth: int):
        for stmt in stmts:
            if isinstance(stmt, (ast.For, ast.While)):
                new_depth = depth + 1
                # Look for append/add/update calls or direct assignments to collections
                for child in ast.walk(stmt):
                    if isinstance(child, ast.Call):
                        name = _get_func_name(child.func)
                        if name in ("append", "add", "update", "extend", "insert"):
                            if new_depth >= 2:
                                self._update_space(
                                    "O(n^2)", "high",
                                    {"line": getattr(child, "lineno", stmt.lineno),
                                     "reason": f".{name}() inside nested loop — O(n^2) space"},
                                )
                            else:
                                self._update_space(
                                    "O(n)", "high",
                                    {"line": getattr(child, "lineno", stmt.lineno),
                                     "reason": f".{name}() inside loop — O(n) space"},
                                )
                sub_stmts = []
                if hasattr(stmt, "body"):
                    sub_stmts.extend(stmt.body)
                if hasattr(stmt, "orelse") and stmt.orelse:
                    sub_stmts.extend(stmt.orelse)
                self._walk_space(stmt.body, new_depth)
            elif isinstance(stmt, (ast.If, ast.With, ast.Try)):
                sub_bodies: list[list[ast.stmt]] = []
                if hasattr(stmt, "body"):
                    sub_bodies.append(stmt.body)
                if hasattr(stmt, "orelse") and stmt.orelse:
                    sub_bodies.append(stmt.orelse)
                if hasattr(stmt, "handlers"):
                    for h in stmt.handlers:
                        sub_bodies.append(h.body)
                for sub in sub_bodies:
                    self._walk_space(sub, depth)

    # -- helpers --------------------------------------------------------------

    _COMPLEXITY_RANK = {
        "O(1)": 0,
        "O(log n)": 1,
        "O(n)": 2,
        "O(n log n)": 3,
        "O(n*m)": 4,
        "O(n^2)": 5,
        "O(n^2 log n)": 6,
        "O(n^3)": 7,
        "O(2^n)": 8,
        "unknown": -1,
    }

    def _update_time(self, complexity: str, confidence: str, evidence: dict):
        current_rank = self._COMPLEXITY_RANK.get(self.time_complexity, 0)
        new_rank = self._COMPLEXITY_RANK.get(complexity, 0)
        if new_rank > current_rank:
            self.time_complexity = complexity
            self.time_confidence = confidence
        self.time_evidence.append(evidence)

    def _update_space(self, complexity: str, confidence: str, evidence: dict):
        current_rank = self._COMPLEXITY_RANK.get(self.space_complexity, 0)
        new_rank = self._COMPLEXITY_RANK.get(complexity, 0)
        if new_rank > current_rank:
            self.space_complexity = complexity
            self.space_confidence = confidence
        self.space_evidence.append(evidence)

    def analyze(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        # Time: check recursion first (takes priority for 2^n)
        self._analyze_recursion(func_node)
        # Then loops (may override lower complexities)
        self._analyze_loops(func_node)
        # Sort calls at top level (not inside loops, already counted)
        # Only add sort if no loop-based complexity was found
        if self.time_complexity in ("O(1)", "O(n)"):
            self._check_top_level_sort(func_node)
        # Space
        self._analyze_space(func_node)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _parse(code: str) -> ast.Module | None:
    try:
        return ast.parse(code)
    except SyntaxError:
        return None


def _analyze_functions(code: str) -> list[_FuncAnalyzer]:
    """Parse code and run per-function analysis. Returns list of analyzers."""
    tree = _parse(code)
    if tree is None:
        return []
    results = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fa = _FuncAnalyzer(node.name)
            fa.analyze(node)
            results.append(fa)
    return results


def _worst_case(analyzers: list[_FuncAnalyzer], attr_complexity: str, attr_confidence: str, attr_evidence: str) -> dict:
    """Pick the function with the worst complexity and merge evidence."""
    if not analyzers:
        return dict(_EMPTY)

    rank = _FuncAnalyzer._COMPLEXITY_RANK

    best: _FuncAnalyzer = max(
        analyzers,
        key=lambda fa: rank.get(getattr(fa, attr_complexity), 0),
    )
    all_evidence: list[dict] = []
    for fa in analyzers:
        all_evidence.extend(getattr(fa, attr_evidence))

    return {
        "complexity": getattr(best, attr_complexity),
        "confidence": getattr(best, attr_confidence),
        "evidence": all_evidence,
    }


def analyze_time(code: str) -> dict:
    """
    Analyze time complexity of the given Python source code.

    Returns:
        {
            "complexity": str,       # e.g. "O(n^2)"
            "confidence": str,       # "high" | "medium" | "low"
            "evidence": [{"line": int, "reason": str}, ...]
        }
    On any error, returns {"complexity":"unknown","confidence":"low","evidence":[]}.
    """
    try:
        analyzers = _analyze_functions(code)
        if not analyzers:
            return {"complexity": "O(1)", "confidence": "low", "evidence": []}
        return _worst_case(analyzers, "time_complexity", "time_confidence", "time_evidence")
    except Exception:
        return dict(_EMPTY)


def analyze_space(code: str) -> dict:
    """
    Analyze space complexity of the given Python source code.

    Returns:
        {
            "complexity": str,
            "confidence": str,
            "evidence": [{"line": int, "reason": str}, ...]
        }
    On any error, returns {"complexity":"unknown","confidence":"low","evidence":[]}.
    """
    try:
        analyzers = _analyze_functions(code)
        if not analyzers:
            return {"complexity": "O(1)", "confidence": "low", "evidence": []}
        return _worst_case(analyzers, "space_complexity", "space_confidence", "space_evidence")
    except Exception:
        return dict(_EMPTY)
