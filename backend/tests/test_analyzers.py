"""
tests/test_analyzers.py

Pytest suite for the Code Doctor analyzers.
Tests are fixture-file-driven: we read the actual fixture source and pass it
to each analyzer, then assert on the results.
"""
import pathlib
import pytest

# Resolve fixture paths relative to this file's location
_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _read(filename: str) -> str:
    return (_FIXTURES / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# complexity.py tests
# ---------------------------------------------------------------------------

class TestTimeComplexity:
    def setup_method(self):
        from analyzers.complexity import analyze_time
        self.analyze_time = analyze_time

    def test_nested_loop_is_n_times_m(self):
        code = _read("nested_loop.py")
        result = self.analyze_time(code)
        assert result["complexity"] == "O(n*m)", (
            f"Expected O(n*m), got {result['complexity']}. Evidence: {result['evidence']}"
        )

    def test_recursive_fib_is_exponential(self):
        code = _read("recursive_fib.py")
        result = self.analyze_time(code)
        assert result["complexity"] == "O(2^n)", (
            f"Expected O(2^n), got {result['complexity']}. Evidence: {result['evidence']}"
        )

    def test_confidence_is_string(self):
        code = _read("nested_loop.py")
        result = self.analyze_time(code)
        assert result["confidence"] in ("high", "medium", "low")

    def test_evidence_is_list_of_dicts(self):
        code = _read("nested_loop.py")
        result = self.analyze_time(code)
        assert isinstance(result["evidence"], list)
        for item in result["evidence"]:
            assert "line" in item
            assert "reason" in item

    def test_error_resilience(self):
        result = self.analyze_time("def foo(: pass")  # syntax error
        assert result["complexity"] in ("unknown", "O(1)")
        assert result["confidence"] in ("low",)


class TestSpaceComplexity:
    def setup_method(self):
        from analyzers.complexity import analyze_space
        self.analyze_space = analyze_space

    def test_recursive_fib_stack_is_O_n(self):
        code = _read("recursive_fib.py")
        result = self.analyze_space(code)
        assert result["complexity"] == "O(n)", (
            f"Expected O(n), got {result['complexity']}. Evidence: {result['evidence']}"
        )

    def test_error_resilience(self):
        result = self.analyze_space("not valid python ::::")
        assert result["complexity"] in ("unknown", "O(1)")


# ---------------------------------------------------------------------------
# performance.py tests
# ---------------------------------------------------------------------------

class TestPerformance:
    def setup_method(self):
        from analyzers.performance import analyze_performance
        self.analyze = analyze_performance

    def test_n_plus_one_detected(self):
        code = _read("n_plus_one.py")
        findings = self.analyze(code)
        assert len(findings) >= 1, "Expected at least one N+1 finding"
        n_plus_one = [f for f in findings if f["type"] == "n_plus_one"]
        assert len(n_plus_one) >= 1, f"No n_plus_one findings in: {findings}"

    def test_n_plus_one_correct_line(self):
        code = _read("n_plus_one.py")
        findings = self.analyze(code)
        n_plus_one = [f for f in findings if f["type"] == "n_plus_one"]
        # The db.query() call is inside a for loop — verify a finding has a plausible line
        lines = [f["line"] for f in n_plus_one]
        assert any(line > 0 for line in lines), f"All lines are 0: {lines}"

    def test_returns_list(self):
        code = _read("n_plus_one.py")
        findings = self.analyze(code)
        assert isinstance(findings, list)

    def test_finding_fields(self):
        code = _read("n_plus_one.py")
        findings = self.analyze(code)
        for f in findings:
            assert "type" in f
            assert "severity" in f
            assert "line" in f
            assert "evidence" in f
            assert "fix" in f

    def test_error_resilience(self):
        result = self.analyze("def bad(: pass")
        assert result == []


# ---------------------------------------------------------------------------
# security.py tests
# ---------------------------------------------------------------------------

class TestSecurity:
    def setup_method(self):
        from analyzers.security import analyze_security
        self.analyze = analyze_security

    def test_at_least_three_findings(self):
        code = _read("insecure.py")
        findings = self.analyze(code)
        assert len(findings) >= 3, (
            f"Expected ≥3 security findings, got {len(findings)}: {findings}"
        )

    def test_sql_injection_detected(self):
        code = _read("insecure.py")
        findings = self.analyze(code)
        sql = [f for f in findings if f["category"] == "sql_injection"]
        assert len(sql) >= 1, f"No sql_injection findings in: {findings}"

    def test_eval_detected(self):
        code = _read("insecure.py")
        findings = self.analyze(code)
        evl = [f for f in findings if f["category"] == "eval_exec"]
        assert len(evl) >= 1, f"No eval_exec findings in: {findings}"

    def test_hardcoded_secret_detected(self):
        code = _read("insecure.py")
        findings = self.analyze(code)
        secrets = [f for f in findings if f["category"] == "hardcoded_secret"]
        assert len(secrets) >= 1, f"No hardcoded_secret findings in: {findings}"

    def test_finding_fields(self):
        code = _read("insecure.py")
        findings = self.analyze(code)
        for f in findings:
            assert "severity" in f
            assert "category" in f
            assert "line" in f
            assert "evidence" in f
            assert "fix" in f

    def test_error_resilience(self):
        result = self.analyze("def broken(: pass")
        assert result == []


# ---------------------------------------------------------------------------
# New complexity tests — BUG1, BUG2, BUG3, IMPROVEMENT
# ---------------------------------------------------------------------------

class TestComplexityBugFixes:
    def setup_method(self):
        from analyzers.complexity import analyze_time, analyze_space
        self.analyze_time = analyze_time
        self.analyze_space = analyze_space

    # BUG 1 — parse failure must return "unknown", not "O(1)"
    def test_syntax_error_returns_unknown_time(self):
        result = self.analyze_time("def f(:\n  pass")
        assert result["complexity"] == "unknown", (
            f"Expected 'unknown' for broken input, got {result['complexity']}"
        )
        assert result["confidence"] == "low"
        assert len(result["evidence"]) >= 1
        assert result["evidence"][0]["line"] == 0
        assert "could not parse" in result["evidence"][0]["reason"]

    def test_syntax_error_returns_unknown_space(self):
        result = self.analyze_space("def f(:\n  pass")
        assert result["complexity"] == "unknown"

    # BUG 1 — BOM prefix must be stripped and not cause a parse failure
    def test_bom_prefix_stripped_before_parse(self):
        code = "\ufeff" + _read("nested_loop.py")
        result = self.analyze_time(code)
        assert result["complexity"] == "O(n*m)", (
            f"BOM-prefixed code should still parse as O(n*m), got {result['complexity']}"
        )

    # BUG 2 — optimized grouped-dict match is O(n+m), not O(n*m)
    def test_optimized_match_time_is_n_plus_m(self):
        code = _read("optimized_match.py")
        result = self.analyze_time(code)
        assert result["complexity"] == "O(n+m)", (
            f"Expected O(n+m) for grouped dict match, got {result['complexity']}. "
            f"Evidence: {result['evidence']}"
        )

    def test_optimized_match_space_is_n_plus_m(self):
        code = _read("optimized_match.py")
        result = self.analyze_space(code)
        assert result["complexity"] == "O(n+m)", (
            f"Expected O(n+m) space for grouped dict match, got {result['complexity']}. "
            f"Evidence: {result['evidence']}"
        )

    # IMPROVEMENT — sequential loops over different collections = O(n+m)
    def test_sequential_loops_different_iterables_is_n_plus_m(self):
        code = """
def process(users, orders):
    result = []
    for user in users:
        result.append(user)
    for order in orders:
        result.append(order)
    return result
"""
        result = self.analyze_time(code)
        assert result["complexity"] == "O(n+m)", (
            f"Expected O(n+m) for sequential loops over users/orders, "
            f"got {result['complexity']}. Evidence: {result['evidence']}"
        )

    # Sequential loops over SAME iterable should stay O(n), not O(n+m)
    def test_sequential_loops_same_iterable_stays_O_n(self):
        code = """
def process(items):
    total = 0
    for x in items:
        total += x
    for x in items:
        total -= x
    return total
"""
        result = self.analyze_time(code)
        assert result["complexity"] == "O(n)", (
            f"Expected O(n) for sequential loops over same iterable, "
            f"got {result['complexity']}"
        )
