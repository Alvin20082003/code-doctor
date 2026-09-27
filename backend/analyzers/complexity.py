"""
analyzers/complexity.py

AST-based time and space complexity analyzer.
No LLM — pure static analysis using Python's ast module.
"""
import ast


# ---------------------------------------------------------------------------
# Complexity rank table
# O(n+m) sits between O(n) and O(n log n) — it's super-linear but sub-quadratic.
# ---------------------------------------------------------------------------
_COMPLEXITY_RANK: dict[str, int] = {
    "O(1)":        0,
    "O(log n)":    1,
    "O(n)":        2,
    "O(n+m)":      3,   # sequential multi-collection work (additive)
    "O(n log n)":  4,
    "O(n*m)":      5,
    "O(n^2)":      6,
    "O(n^2 log n)": 7,
    "O(n^3)":      8,
    "O(2^n)":      9,
    "unknown":     -1,
}


def _rank(c: str) -> int:
    return _COMPLEXITY_RANK.get(c, 0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_func_name(node: ast.AST) -> str | None:
    """Return the plain name of a Call node's function attribute, or None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


# ---------------------------------------------------------------------------
# Built-in O(n) / O(n log n) call detector
# ---------------------------------------------------------------------------

# Bare-name builtins that iterate their first argument — O(n) each
_LINEAR_BUILTINS: frozenset[str] = frozenset({
    "sum", "max", "min", "any", "all",
    "list", "set", "tuple", "dict",
})

# Attribute calls that iterate the receiver or first arg — O(n) each
# e.g.  ",".join(items)   items.count(x)   items.index(x)   items.copy()
_LINEAR_METHODS: frozenset[str] = frozenset({
    "join", "count", "index", "copy",
})


def _is_linear_builtin_call(node: ast.Call) -> tuple[bool, str]:
    """
    Return (True, reason) if *node* is a call whose work is O(n) in the
    size of its argument / receiver.  Returns (False, "") otherwise.

    Excluded: len() — O(1) in CPython.
    Does NOT flag sorted() / sort() — handled separately as O(n log n).
    """
    func = node.func

    # --- bare name: sum(xs), max(xs), … ---
    if isinstance(func, ast.Name) and func.id in _LINEAR_BUILTINS:
        name = func.id
        return True, f"{name}() iterates the whole collection — O(n)"

    # --- attribute call: xs.count(v), xs.index(v), xs.copy(), "sep".join(xs) ---
    if isinstance(func, ast.Attribute) and func.attr in _LINEAR_METHODS:
        attr = func.attr
        return True, f".{attr}() iterates the collection — O(n)"

    # --- `x in name` where name is a Name node (likely a parameter/variable) ---
    # This is handled in the Compare walk below; not a Call, so skip here.

    return False, ""


def _has_linear_in_check(stmt: ast.stmt) -> list[tuple[int, str]]:
    """
    Return a list of (lineno, reason) for every `x in some_name` comparison
    found inside *stmt* (not inside nested loops).

    `x in some_name` is O(n) for lists/tuples; we flag it conservatively.
    We skip `x in {literal_set}` (that's O(1)).
    """
    results: list[tuple[int, str]] = []
    for child in ast.walk(stmt):
        if isinstance(child, ast.Compare):
            for i, op in enumerate(child.ops):
                if isinstance(op, ast.In):
                    comp = child.comparators[i]
                    if isinstance(comp, ast.Name):
                        line = getattr(child, "lineno", 0)
                        results.append((line, f"`{ast.unparse(child.left)} in {comp.id}` — O(n) membership test"))
    return results


def _iter_key(iter_node: ast.expr) -> str:
    """
    Return a stable string identity for a For-loop iterable.
    Uses ast.unparse so that calls, subscripts, and attributes all get
    a meaningful key instead of None.
    BUG 3 fix: always use ast.unparse rather than manual Name/Attribute walk.
    """
    try:
        return ast.unparse(iter_node)
    except Exception:
        return "<unknown>"


def _halves_variable(loop_node: ast.stmt) -> bool:
    """Return True if a While loop body contains //= 2 or >>= 1 or mid-index pattern."""
    for child in ast.walk(loop_node):
        if isinstance(child, ast.AugAssign):
            if isinstance(child.op, ast.FloorDiv):
                if isinstance(child.value, ast.Constant) and child.value.value == 2:
                    return True
            if isinstance(child.op, ast.RShift):
                if isinstance(child.value, ast.Constant) and child.value.value == 1:
                    return True
        if isinstance(child, ast.Assign):
            if isinstance(child.value, ast.BinOp) and isinstance(
                child.value.op, ast.FloorDiv
            ):
                return True
    return False


def _has_in_list_check(loop_node: ast.stmt) -> bool:
    """Return True if loop body contains `x in some_name` (likely a list)."""
    for child in ast.walk(loop_node):
        if isinstance(child, ast.Compare):
            for i, op in enumerate(child.ops):
                if isinstance(op, ast.In):
                    comp = child.comparators[i]
                    if isinstance(comp, ast.Name):
                        return True
    return False


# ---------------------------------------------------------------------------
# Dict-grouping tracker
# Detects: dict_var = {}; for x in collection: dict_var[...] = ... / .setdefault(...)
# So that inner loops over dict_var.get(...) / dict_var[key] are tagged as
# "grouped lookup" and treated as additive, not multiplicative.
# ---------------------------------------------------------------------------

def _collect_grouped_dicts(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    """
    Scan a function body for dicts built by iterating over a collection.

    Returns a mapping: dict_var_name -> source_iterable_key

    Pattern detected:
        dict_var = {}  (or dict())
        for item in <collection>:
            dict_var[...] = ...       # Subscript assign
            dict_var.setdefault(...)  # setdefault call
            dict_var.update(...)      # update call
    """
    # Step 1: find names assigned to empty dicts at function top level
    empty_dicts: set[str] = set()
    for stmt in func_node.body:
        if isinstance(stmt, ast.Assign):
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name):
                    val = stmt.value
                    if (
                        (isinstance(val, ast.Dict) and not val.keys)
                        or (
                            isinstance(val, ast.Call)
                            and isinstance(val.func, ast.Name)
                            and val.func.id == "dict"
                            and not val.args
                            and not val.keywords
                        )
                    ):
                        empty_dicts.add(tgt.id)
        # Also pick up annotated: d: dict = {}
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.value:
                val = stmt.value
                if isinstance(val, ast.Dict) and not val.keys:
                    empty_dicts.add(stmt.target.id)

    if not empty_dicts:
        return {}

    grouped: dict[str, str] = {}

    # Step 2: look for for-loops that populate those dicts
    for stmt in func_node.body:
        if not isinstance(stmt, ast.For):
            continue
        collection_key = _iter_key(stmt.iter)
        # Walk the loop body looking for mutations of empty_dicts
        for child in ast.walk(stmt):
            # dict_var[key] = value  →  Assign where target is Subscript
            if isinstance(child, ast.Assign):
                for tgt in child.targets:
                    if (
                        isinstance(tgt, ast.Subscript)
                        and isinstance(tgt.value, ast.Name)
                        and tgt.value.id in empty_dicts
                    ):
                        grouped[tgt.value.id] = collection_key
            # dict_var.setdefault(...) or dict_var.update(...)
            if isinstance(child, ast.Call):
                func = child.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr in ("setdefault", "update", "append")
                    and isinstance(func.value, ast.Name)
                    and func.value.id in empty_dicts
                ):
                    grouped[func.value.id] = collection_key

    return grouped


def _is_grouped_lookup(
    loop_node: ast.For,
    grouped_dicts: dict[str, str],
) -> tuple[bool, str, str]:
    """
    Return (True, dict_name, source_collection) if this For loop iterates over
    the result of a grouped dict lookup — i.e., the loop's iterable is
    dict_var.get(key, ...) or dict_var[key] where dict_var is a grouped dict.

    These patterns mean the total inner iterations across all outer iterations
    are bounded by len(source_collection), making the relationship additive.
    """
    iter_node = loop_node.iter

    # Pattern: for x in grouped_dict.get(key, default):
    if isinstance(iter_node, ast.Call):
        func = iter_node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in ("get", "values", "items")
            and isinstance(func.value, ast.Name)
            and func.value.id in grouped_dicts
        ):
            d = func.value.id
            return True, d, grouped_dicts[d]

    # Pattern: for x in grouped_dict[key]:
    if (
        isinstance(iter_node, ast.Subscript)
        and isinstance(iter_node.value, ast.Name)
        and iter_node.value.id in grouped_dicts
    ):
        d = iter_node.value.id
        return True, d, grouped_dicts[d]

    return False, "", ""


# ---------------------------------------------------------------------------
# Per-function analyzer
# ---------------------------------------------------------------------------

class _FuncAnalyzer:
    """Analyzes a single function definition for time and space complexity."""

    def __init__(self, func_name: str):
        self.func_name = func_name
        self.time_evidence: list[dict] = []
        self.space_evidence: list[dict] = []
        self.time_complexity = "O(1)"
        self.space_complexity = "O(1)"
        self.time_confidence = "high"
        self.space_confidence = "high"

    # -- helpers -----------------------------------------------------------

    def _update_time(self, complexity: str, confidence: str, evidence: dict):
        if _rank(complexity) > _rank(self.time_complexity):
            self.time_complexity = complexity
            self.time_confidence = confidence
        self.time_evidence.append(evidence)

    def _update_space(self, complexity: str, confidence: str, evidence: dict):
        if _rank(complexity) > _rank(self.space_complexity):
            self.space_complexity = complexity
            self.space_confidence = confidence
        self.space_evidence.append(evidence)

    # -- recursion ---------------------------------------------------------

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

    # -- loop analysis -----------------------------------------------------

    def _analyze_loops(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        grouped_dicts = _collect_grouped_dicts(func_node)
        self._walk_body(func_node.body, depth=0, outer_iters=[], grouped_dicts=grouped_dicts)

    def _walk_body(
        self,
        stmts: list[ast.stmt],
        depth: int,
        outer_iters: list[str],      # stack of iterable keys for enclosing loops
        grouped_dicts: dict[str, str],
    ):
        """
        Walk a statement list at the current nesting depth.

        IMPROVEMENT: Track the set of iterable keys seen at this depth level
        (as sibling loops) to detect sequential multi-collection patterns and
        report O(n+m) instead of O(n) for sequential different-iterable loops.
        """
        # Collect iterables of all For loops at this sibling level first,
        # so we can detect "sequential loops over different iterables".
        sibling_for_iters: list[str] = []
        for stmt in stmts:
            if isinstance(stmt, ast.For) and not isinstance(stmt, ast.While):
                sibling_for_iters.append(_iter_key(stmt.iter))

        # Check if this level has sequential loops over multiple distinct collections
        distinct_sibling_iters = set(sibling_for_iters)
        has_sequential_multi = len(distinct_sibling_iters) > 1 and depth == 0

        # Process each statement
        for stmt in stmts:
            if isinstance(stmt, (ast.For, ast.While)):
                loop_line = stmt.lineno
                is_while = isinstance(stmt, ast.While)

                # Resolve iterable key (BUG 3 fix via _iter_key / ast.unparse)
                iterable_key: str = "<while>" if is_while else _iter_key(stmt.iter)

                # Binary-search while loop
                if is_while and _halves_variable(stmt):
                    self._update_time(
                        "O(log n)", "medium",
                        {"line": loop_line,
                         "reason": "while loop halving a variable — O(log n)"},
                    )
                    self._walk_body(stmt.body, depth + 1, outer_iters + [iterable_key], grouped_dicts)
                    continue

                new_depth = depth + 1

                # ---- BUG 2: grouped dict lookup check ----
                if isinstance(stmt, ast.For) and outer_iters:
                    is_grouped, dict_name, source_coll = _is_grouped_lookup(stmt, grouped_dicts)
                    if is_grouped:
                        self._update_time(
                            "O(n+m)", "high",
                            {"line": loop_line,
                             "reason": (
                                 f"grouped lookup into '{dict_name}' built from '{source_coll}' "
                                 f"— total inner iterations bounded by len({source_coll}), "
                                 f"additive not multiplicative"
                             )},
                        )
                        self._walk_body(stmt.body, new_depth, outer_iters + [iterable_key], grouped_dicts)
                        continue

                # ---- Standard nesting analysis ----
                if new_depth == 1:
                    # IMPROVEMENT: If sibling loops at depth-0 iterate over distinct collections,
                    # the combined complexity is O(n+m), not just O(n).
                    if has_sequential_multi and depth == 0:
                        self._update_time(
                            "O(n+m)", "high",
                            {"line": loop_line,
                             "reason": (
                                 f"sequential loop over '{iterable_key}' "
                                 f"(combined with other loops at this level over different collections) "
                                 f"— O(n+m)"
                             )},
                        )
                    else:
                        self._update_time(
                            "O(n)", "high",
                            {"line": loop_line,
                             "reason": f"single loop over '{iterable_key}' — O(n)"},
                        )

                elif new_depth == 2:
                    outer_iter = outer_iters[-1] if outer_iters else None
                    if outer_iter is not None and iterable_key == outer_iter:
                        complexity = "O(n^2)"
                        reason = f"nested loop over same iterable '{iterable_key}' — O(n^2)"
                    else:
                        complexity = "O(n*m)"
                        reason = (
                            f"nested loop over different iterables "
                            f"('{outer_iter}' vs '{iterable_key}') — O(n*m)"
                        )
                    self._update_time(complexity, "high", {"line": loop_line, "reason": reason})

                elif new_depth >= 3:
                    self._update_time(
                        "O(n^3)", "high",
                        {"line": loop_line, "reason": "triple-nested loop — O(n^3)"},
                    )

                # `x in list_var` inside a depth-1 loop adds a factor n
                if new_depth == 1 and _has_in_list_check(stmt):
                    self._update_time(
                        "O(n^2)", "medium",
                        {"line": loop_line,
                         "reason": "`x in list` inside a loop adds O(n) factor"},
                    )

                # sort / sorted inside a loop
                for child in ast.walk(stmt):
                    if isinstance(child, ast.Call):
                        name = _get_func_name(child.func)
                        if name in ("sorted", "sort"):
                            self._update_time(
                                "O(n^2 log n)", "medium",
                                {"line": getattr(child, "lineno", loop_line),
                                 "reason": "sort inside a loop — O(n * n log n)"},
                            )

                self._walk_body(stmt.body, new_depth, outer_iters + [iterable_key], grouped_dicts)

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
                    self._walk_body(sub, depth, outer_iters, grouped_dicts)

    # -- top-level sort ---------------------------------------------------

    def _check_top_level_sort(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                name = _get_func_name(node.func)
                if name in ("sorted", "sort"):
                    self._update_time(
                        "O(n log n)", "high",
                        {"line": getattr(node, "lineno", 0),
                         "reason": "sorted() / .sort() call — O(n log n)"},
                    )
                    return

    # -- space analysis ---------------------------------------------------

    def _analyze_space(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        grouped_dicts = _collect_grouped_dicts(func_node)
        self._walk_space(func_node.body, depth=0, grouped_dicts=grouped_dicts)

        # Comprehensions always produce O(n) space
        for node in ast.walk(func_node):
            if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                self._update_space(
                    "O(n)", "high",
                    {"line": getattr(node, "lineno", 0),
                     "reason": "comprehension over input — O(n) space"},
                )

    def _walk_space(
        self,
        stmts: list[ast.stmt],
        depth: int,
        grouped_dicts: dict[str, str],
        outer_iters: list[str] | None = None,
    ):
        if outer_iters is None:
            outer_iters = []

        # Detect sequential multi-collection loops at this level
        sibling_for_iters = [
            _iter_key(s.iter)
            for s in stmts
            if isinstance(s, ast.For)
        ]
        distinct_sibling = set(sibling_for_iters)
        has_sequential_multi = len(distinct_sibling) > 1 and depth == 0

        for stmt in stmts:
            if isinstance(stmt, (ast.For, ast.While)):
                new_depth = depth + 1
                iterable_key = (
                    "<while>" if isinstance(stmt, ast.While)
                    else _iter_key(stmt.iter)
                )

                # BUG 2 grouped dict lookup — space is additive
                if isinstance(stmt, ast.For) and outer_iters:
                    is_grouped, dict_name, source_coll = _is_grouped_lookup(stmt, grouped_dicts)
                    if is_grouped:
                        # appends inside grouped inner loop → O(n+m) space
                        for child in ast.walk(stmt):
                            if isinstance(child, ast.Call):
                                mname = _get_func_name(child.func)
                                if mname in ("append", "add", "update", "extend", "insert"):
                                    self._update_space(
                                        "O(n+m)", "high",
                                        {"line": getattr(child, "lineno", stmt.lineno),
                                         "reason": (
                                             f".{mname}() inside grouped lookup loop over '{dict_name}' "
                                             f"(source: '{source_coll}') — O(n+m) space"
                                         )},
                                    )
                        self._walk_space(stmt.body, new_depth, grouped_dicts, outer_iters + [iterable_key])
                        continue

                for child in ast.walk(stmt):
                    if isinstance(child, ast.Call):
                        mname = _get_func_name(child.func)
                        if mname in ("append", "add", "update", "extend", "insert"):
                            if new_depth >= 2:
                                self._update_space(
                                    "O(n^2)", "high",
                                    {"line": getattr(child, "lineno", stmt.lineno),
                                     "reason": f".{mname}() inside nested loop — O(n^2) space"},
                                )
                            else:
                                # Sequential multi-collection at depth 1 → O(n+m) space
                                if has_sequential_multi:
                                    self._update_space(
                                        "O(n+m)", "high",
                                        {"line": getattr(child, "lineno", stmt.lineno),
                                         "reason": f".{mname}() inside sequential multi-collection loop — O(n+m) space"},
                                    )
                                else:
                                    self._update_space(
                                        "O(n)", "high",
                                        {"line": getattr(child, "lineno", stmt.lineno),
                                         "reason": f".{mname}() inside loop — O(n) space"},
                                    )

                self._walk_space(stmt.body, new_depth, grouped_dicts, outer_iters + [iterable_key])

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
                    self._walk_space(sub, depth, grouped_dicts, outer_iters)

    # -- linear builtins (top-level, outside loops) -----------------------

    def _check_linear_builtins(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        """
        Detect O(n) work from built-in calls (sum, max, min, any, all,
        list, set, tuple, dict, .join, .count, .index, .copy) and
        `x in collection` comparisons.

        At the top level (outside loops): contributes O(n).
        Inside a loop: contributes O(n^2) (multiplicative factor).

        This runs after loop analysis, so O(n^2) upgrades are still possible
        even when the loop analysis already set O(n).
        """
        # Walk only the flat (non-loop) statement tree
        self._walk_linear_builtins(func_node.body, in_loop=False)

    def _walk_linear_builtins(
        self,
        stmts: list[ast.stmt],
        in_loop: bool,
    ):
        """
        Recursively walk *stmts*.  When in_loop=True (we are inside a
        for/while), a linear builtin call becomes O(n^2).
        When in_loop=False it is O(n).
        """
        for stmt in stmts:
            if isinstance(stmt, (ast.For, ast.While)):
                # Recurse into loop body with in_loop=True
                self._walk_linear_builtins(stmt.body, in_loop=True)
                # Also check the loop's iterable expression for linear builtins
                # e.g. `for x in sorted(xs):` — but sorted is already caught
                if isinstance(stmt, ast.For):
                    # Check if the iterable itself is a linear builtin call
                    if isinstance(stmt.iter, ast.Call):
                        is_lin, reason = _is_linear_builtin_call(stmt.iter)
                        if is_lin:
                            line = getattr(stmt.iter, "lineno", stmt.lineno)
                            complexity = "O(n^2)" if in_loop else "O(n)"
                            self._update_time(
                                complexity, "medium",
                                {"line": line, "reason": reason},
                            )
                continue

            # For non-loop statements, scan all Call nodes within
            if isinstance(stmt, (ast.If, ast.With, ast.Try)):
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
                    self._walk_linear_builtins(sub, in_loop)
                continue

            # Plain statement: walk for linear calls
            for node in ast.walk(stmt):
                if isinstance(node, ast.Call):
                    is_lin, reason = _is_linear_builtin_call(node)
                    if is_lin:
                        line = getattr(node, "lineno", 0)
                        complexity = "O(n^2)" if in_loop else "O(n)"
                        self._update_time(
                            complexity, "medium",
                            {"line": line, "reason": reason},
                        )

                # `x in name` comparison — O(n) membership.
                # Only emit when NOT in_loop: the loop analyzer already
                # calls _has_in_list_check which emits O(n^2) for those.
                if not in_loop and isinstance(node, ast.Compare):
                    for i, op in enumerate(node.ops):
                        if isinstance(op, ast.In):
                            comp = node.comparators[i]
                            if isinstance(comp, ast.Name):
                                line = getattr(node, "lineno", 0)
                                reason = (
                                    f"`{ast.unparse(node.left)} in {comp.id}`"
                                    f" — O(n) membership test"
                                )
                                self._update_time(
                                    "O(n)", "medium",
                                    {"line": line, "reason": reason},
                                )

    # -- entry point -------------------------------------------------------

    def analyze(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        self._analyze_recursion(func_node)
        self._analyze_loops(func_node)
        if self.time_complexity in ("O(1)", "O(n)", "O(n+m)"):
            self._check_top_level_sort(func_node)
        self._check_linear_builtins(func_node)
        self._analyze_space(func_node)


# ---------------------------------------------------------------------------
# Parsing — BUG 1 fix
# ---------------------------------------------------------------------------

class _ParseError(Exception):
    def __init__(self, msg: str):
        self.msg = msg


def _parse(code: str) -> ast.Module:
    """
    Parse Python source code.
    - Strips a leading BOM (\ufeff) before parsing.
    - Raises _ParseError with a human-readable message on SyntaxError.
    """
    # Strip BOM
    if code.startswith("\ufeff"):
        code = code[1:]
    try:
        return ast.parse(code)
    except SyntaxError as exc:
        raise _ParseError(f"could not parse code: {exc}") from exc


def _parse_error_result(msg: str) -> dict:
    return {
        "complexity": "unknown",
        "confidence": "low",
        "evidence": [{"line": 0, "reason": msg}],
    }


# ---------------------------------------------------------------------------
# Internal analysis entry point
# ---------------------------------------------------------------------------

def _analyze_functions(code: str) -> list[_FuncAnalyzer]:
    """Parse code and run per-function analysis. Raises _ParseError on bad input."""
    tree = _parse(code)  # may raise _ParseError
    results: list[_FuncAnalyzer] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fa = _FuncAnalyzer(node.name)
            fa.analyze(node)
            results.append(fa)
    return results


def _worst_case(
    analyzers: list[_FuncAnalyzer],
    attr_complexity: str,
    attr_confidence: str,
    attr_evidence: str,
) -> dict:
    """Pick the function with the worst complexity; merge all evidence."""
    if not analyzers:
        # No functions found in the code — treat as O(1) (module-level script)
        return {"complexity": "O(1)", "confidence": "low", "evidence": []}

    best: _FuncAnalyzer = max(
        analyzers,
        key=lambda fa: _rank(getattr(fa, attr_complexity)),
    )
    all_evidence: list[dict] = []
    for fa in analyzers:
        all_evidence.extend(getattr(fa, attr_evidence))

    return {
        "complexity": getattr(best, attr_complexity),
        "confidence": getattr(best, attr_confidence),
        "evidence": all_evidence,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_time(code: str) -> dict:
    """
    Analyze time complexity of the given Python source code.

    Returns:
        {
            "complexity": str,       # e.g. "O(n^2)"
            "confidence": str,       # "high" | "medium" | "low"
            "evidence": [{"line": int, "reason": str}, ...]
        }
    On parse failure: {"complexity":"unknown","confidence":"low","evidence":[{"line":0,"reason":"..."}]}
    On any other error: same shape with "unknown".
    """
    try:
        analyzers = _analyze_functions(code)
        return _worst_case(analyzers, "time_complexity", "time_confidence", "time_evidence")
    except _ParseError as exc:
        return _parse_error_result(exc.msg)
    except Exception as exc:
        return _parse_error_result(f"internal error: {exc}")


def analyze_space(code: str) -> dict:
    """
    Analyze space complexity of the given Python source code.

    Returns:
        {
            "complexity": str,
            "confidence": str,
            "evidence": [{"line": int, "reason": str}, ...]
        }
    On parse failure: {"complexity":"unknown","confidence":"low","evidence":[{"line":0,"reason":"..."}]}
    On any other error: same shape with "unknown".
    """
    try:
        analyzers = _analyze_functions(code)
        return _worst_case(analyzers, "space_complexity", "space_confidence", "space_evidence")
    except _ParseError as exc:
        return _parse_error_result(exc.msg)
    except Exception as exc:
        return _parse_error_result(f"internal error: {exc}")
