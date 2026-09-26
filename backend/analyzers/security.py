"""
analyzers/security.py

Security analyzer combining bandit (subprocess) + custom AST checks.
Detects:
  - SQL injection via f-string/concatenation in execute()/query()
  - eval() / exec() usage
  - Hardcoded secrets (password/secret/api_key/token = "literal")
  - General bandit findings
"""
import ast
import json
import os
import subprocess
import tempfile
from typing import Any


# ---------------------------------------------------------------------------
# Bandit runner
# ---------------------------------------------------------------------------

def _run_bandit(code: str) -> list[dict]:
    """Write code to a temp file, run bandit -f json, parse results."""
    findings: list[dict] = []
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as fh:
            fh.write(code)
            tmp_path = fh.name

        result = subprocess.run(
            ["bandit", "-f", "json", "-q", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        raw = result.stdout.strip()
        if not raw:
            return []
        data = json.loads(raw)
        for issue in data.get("results", []):
            findings.append({
                "severity": issue.get("issue_severity", "medium").lower(),
                "category": issue.get("test_id", "unknown") + ": " + issue.get("test_name", ""),
                "line": issue.get("line_number", 0),
                "evidence": issue.get("issue_text", ""),
                "fix": issue.get("more_info", "See bandit docs"),
            })
    except (json.JSONDecodeError, KeyError):
        pass
    except Exception:
        pass
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return findings


# ---------------------------------------------------------------------------
# AST checks
# ---------------------------------------------------------------------------

def _is_fstring_or_concat(node: ast.AST) -> bool:
    """Return True if node is an f-string (JoinedStr) or string concatenation (BinOp +)."""
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return True
    # Variable that might hold a constructed string — we flag Name nodes too when
    # they are the sole argument to execute/query (covered by broader check)
    return False


def _collect_fstring_vars(scope: ast.AST) -> set[str]:
    """
    Return names of variables that are assigned an f-string or string concatenation
    anywhere within the given scope node.
    """
    fstring_vars: set[str] = set()
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign):
            if _is_fstring_or_concat(node.value):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        fstring_vars.add(target.id)
        elif isinstance(node, (ast.AnnAssign,)):
            if node.value and _is_fstring_or_concat(node.value):
                if isinstance(node.target, ast.Name):
                    fstring_vars.add(node.target.id)
    return fstring_vars


def _check_sql_injection(tree: ast.Module) -> list[dict]:
    findings: list[dict] = []
    # Collect all f-string/concat variable names at module scope
    module_fstring_vars = _collect_fstring_vars(tree)

    for scope in [tree] + [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]:
        # Collect f-string vars within this scope
        scope_fstring_vars = _collect_fstring_vars(scope) | module_fstring_vars

        for node in ast.walk(scope):
            if isinstance(node, ast.Call):
                func = node.func
                method_name: str | None = None
                if isinstance(func, ast.Attribute) and func.attr in ("execute", "query"):
                    method_name = func.attr
                elif isinstance(func, ast.Name) and func.id in ("execute", "query"):
                    method_name = func.id

                if method_name and node.args:
                    first_arg = node.args[0]
                    # Direct f-string / concat as argument
                    if _is_fstring_or_concat(first_arg):
                        try:
                            evidence_text = ast.unparse(first_arg)
                        except Exception:
                            evidence_text = "<unparseable>"
                        findings.append({
                            "severity": "high",
                            "category": "sql_injection",
                            "line": getattr(node, "lineno", 0),
                            "evidence": (
                                f"f-string/concatenation passed to {method_name}(): "
                                f"{evidence_text[:120]}"
                            ),
                            "fix": "Use parameterized queries / prepared statements",
                        })
                    # Variable holding an f-string passed to execute/query
                    elif isinstance(first_arg, ast.Name) and first_arg.id in scope_fstring_vars:
                        findings.append({
                            "severity": "high",
                            "category": "sql_injection",
                            "line": getattr(node, "lineno", 0),
                            "evidence": (
                                f"Variable '{first_arg.id}' (built from f-string/concat) "
                                f"passed to {method_name}() — potential SQL injection"
                            ),
                            "fix": "Use parameterized queries / prepared statements",
                        })
    return findings


def _check_eval_exec(tree: ast.Module) -> list[dict]:
    findings: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name: str | None = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in ("eval", "exec"):
                findings.append({
                    "severity": "high",
                    "category": "eval_exec",
                    "line": getattr(node, "lineno", 0),
                    "evidence": f"Dangerous {name}() call with potentially untrusted input",
                    "fix": (
                        "Remove eval/exec; use ast.literal_eval() for safe parsing "
                        "or refactor to avoid dynamic execution"
                    ),
                })
    return findings


_SECRET_KEYWORDS = frozenset({
    "password", "passwd", "secret", "api_key", "apikey",
    "token", "auth_token", "access_token", "private_key",
})


def _check_hardcoded_secrets(tree: ast.Module) -> list[dict]:
    findings: list[dict] = []
    for node in ast.walk(tree):
        # Module-level or function-level assignments: VAR = "literal"
        if isinstance(node, ast.Assign):
            for target in node.targets:
                name: str | None = None
                if isinstance(target, ast.Name):
                    name = target.id.lower()
                elif isinstance(target, ast.Attribute):
                    name = target.attr.lower()

                if name and any(kw in name for kw in _SECRET_KEYWORDS):
                    if isinstance(node.value, ast.Constant) and isinstance(
                        node.value.value, str
                    ):
                        findings.append({
                            "severity": "high",
                            "category": "hardcoded_secret",
                            "line": getattr(node, "lineno", 0),
                            "evidence": (
                                f"Variable '{target.id if isinstance(target, ast.Name) else target.attr}' "
                                f"assigned a string literal — possible hardcoded secret"
                            ),
                            "fix": "Move secret to environment variable (os.getenv) or secret manager",
                        })
    return findings


# ---------------------------------------------------------------------------
# De-duplication
# ---------------------------------------------------------------------------

def _deduplicate(findings: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for f in findings:
        key = (f["line"], f["category"])
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_security(code: str) -> list[dict]:
    """
    Analyze security issues in the given Python source code.

    Returns a list of findings:
        [{
            "severity": "high"|"medium"|"low",
            "category": str,
            "line": int,
            "evidence": str,
            "fix": str,
        }, ...]
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
        findings.extend(_run_bandit(code))
        findings.extend(_check_sql_injection(tree))
        findings.extend(_check_eval_exec(tree))
        findings.extend(_check_hardcoded_secrets(tree))
        return _deduplicate(findings)
    except Exception:
        return []
