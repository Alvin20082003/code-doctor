"""
backend/agents/optimizer.py

IBM Granite optimizer with deterministic verification loop.

KEY PRINCIPLE: never trust the LLM's complexity claim.
Our AST analyzer (analyzers/complexity.py) is the sole source of truth.

Flow
----
1. Build fix hints from the analysis findings.
2. Build a structured prompt (role, code, measured complexity, findings, hints, output rules).
3. Call the LLM (agents/llm.py).
4. Parse the first ```python block + EXPLANATION section from the response.
5. Verify: ast.parse + re-run all analyzers + complexity rank comparison.
6. If verification fails, retry ONCE with targeted feedback.
7. Return a rich result dict with status, code, explanation, before/after metrics,
   behavioral test result, and attempts count.
"""
from __future__ import annotations

import ast
import re
import textwrap
from typing import Any

from analyzers.complexity import analyze_time, analyze_space, _COMPLEXITY_RANK
from analyzers.performance import analyze_performance
from analyzers.security import analyze_security
from validation import check_behavior
from agents.llm import generate


# ---------------------------------------------------------------------------
# Complexity rank helper (mirrors scoring._COMPLEXITY_RANK)
# ---------------------------------------------------------------------------

def _rank(c: str) -> int:
    return _COMPLEXITY_RANK.get(c, -1)


# ---------------------------------------------------------------------------
# Fix-hint builder
# ---------------------------------------------------------------------------

def _build_fix_hints(analysis: dict) -> str:
    """
    Convert analysis findings into concrete, actionable fix hints for the LLM.
    Returns a markdown-formatted string.
    """
    hints: list[str] = []

    time_c = analysis.get("time", {}).get("complexity", "unknown")
    perf   = analysis.get("performance", []) or []
    sec    = analysis.get("security",    []) or []

    # Complexity-level hint
    if time_c in ("O(n*m)", "O(n^2)"):
        hints.append(
            "NESTED LOOP FIX: Replace the nested loop with a dict-grouping approach. "
            "Build a dict keyed by the join field in ONE pass over the inner collection "
            "(e.g. `orders_by_user = {}; for o in orders: orders_by_user.setdefault(o.user_id, []).append(o)`), "
            "then loop the outer collection and do a single O(1) dict lookup. "
            "This reduces time complexity from O(n*m) to O(n+m)."
        )
    elif time_c == "O(n^3)":
        hints.append(
            "TRIPLE NESTED LOOP: Identify which inner loop can be pre-computed into "
            "a lookup dict or set before the outer loops run."
        )

    for f in perf:
        ftype = f.get("type", "")
        if ftype == "n_plus_one":
            hints.append(
                "N+1 QUERY FIX: Fetch ALL rows in ONE query using IN (...) "
                "(e.g. `WHERE id IN (...)` or `WHERE user_id IN (...)`), "
                "then group the results in a dict for O(1) per-item lookup. "
                "Never call .query() / .execute() / .find() / .get() inside a loop."
            )
            break  # one hint is enough

    for f in perf:
        ftype = f.get("type", "")
        if ftype == "list_membership_in_loop":
            hints.append(
                "LIST MEMBERSHIP FIX: Convert the list used in `x in list_var` to a set "
                "BEFORE the loop so that membership tests are O(1) instead of O(n). "
                "E.g. `item_set = set(list_var)` then `if x in item_set:`."
            )
            break

    for f in sec:
        cat = f.get("category", "")
        if cat == "sql_injection":
            hints.append(
                "SQL INJECTION FIX: Replace the f-string / concatenated SQL with "
                "parameterized query placeholders. "
                "E.g. `cursor.execute('SELECT * FROM t WHERE id = %s', (user_id,))`."
            )
            break

    for f in sec:
        cat = f.get("category", "")
        if cat == "eval_exec":
            hints.append(
                "EVAL FIX: Remove the eval() / exec() call. "
                "Use `ast.literal_eval()` for safe literal parsing, or refactor the "
                "logic to avoid dynamic code execution entirely."
            )
            break

    for f in sec:
        cat = f.get("category", "")
        if cat == "hardcoded_secret":
            hints.append(
                "HARDCODED SECRET FIX: Move the secret to an environment variable. "
                "Replace the literal with `os.environ.get('SECRET_NAME')` or "
                "`os.getenv('SECRET_NAME')`.  Never commit credentials to source code."
            )
            break

    if not hints:
        hints.append("No specific hints — apply general best practices.")

    return "\n".join(f"- {h}" for h in hints)


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(
    code: str,
    analysis: dict,
    fix_hints: str,
    feedback: str = "",
) -> str:
    time_info  = analysis.get("time",  {})
    space_info = analysis.get("space", {})

    time_evidence = "; ".join(
        e.get("reason", "") for e in (time_info.get("evidence") or [])[:3]
    )
    space_evidence = "; ".join(
        e.get("reason", "") for e in (space_info.get("evidence") or [])[:3]
    )

    perf_lines = "\n".join(
        f"  - [line {f.get('line',0)}] {f.get('severity','?').upper()}: {f.get('evidence','')}"
        for f in (analysis.get("performance") or [])
    ) or "  (none)"

    sec_lines = "\n".join(
        f"  - [line {f.get('line',0)}] {f.get('severity','?').upper()} ({f.get('category','?')}): {f.get('evidence','')}"
        for f in (analysis.get("security") or [])
    ) or "  (none)"

    feedback_section = ""
    if feedback:
        feedback_section = f"\n\nPREVIOUS ATTEMPT FEEDBACK:\n{feedback}"

    prompt = textwrap.dedent(f"""\
        You are a senior backend engineer performing a code review and optimization.

        ## Original code
        ```python
        {code}
        ```

        ## Measured complexity (AST analyzer — source of truth)
        Time  : {time_info.get('complexity','unknown')} (confidence: {time_info.get('confidence','?')})
        Reason: {time_evidence}
        Space : {space_info.get('complexity','unknown')} (confidence: {space_info.get('confidence','?')})
        Reason: {space_evidence}

        ## Performance findings
        {perf_lines}

        ## Security findings
        {sec_lines}

        ## Fix hints (apply ALL that are relevant)
        {fix_hints}
        {feedback_section}

        ## Rules
        1. Keep the EXACT same function name, parameters, and return value/shape.
        2. Do NOT remove any functionality.
        3. Apply every fix hint above.
        4. Add a brief inline comment explaining each optimization.

        ## Required output format (EXACTLY as shown — no other text before the code block)
        ```python
        <full optimized code>
        ```
        EXPLANATION: <3-5 plain-English sentences: what was slow, why it breaks at scale, what changed>
    """)
    return prompt


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

_CODE_RE = re.compile(r"```python\s*(.*?)```", re.DOTALL)
_EXPL_RE = re.compile(r"EXPLANATION:\s*(.*)", re.DOTALL)


def _parse_response(text: str) -> tuple[str | None, str]:
    """
    Extract (optimized_code, explanation) from the LLM response text.
    Returns (None, "") if no code block is found.
    """
    code_match = _CODE_RE.search(text)
    if not code_match:
        return None, ""
    code = code_match.group(1).strip()

    expl_match = _EXPL_RE.search(text)
    explanation = expl_match.group(1).strip() if expl_match else ""
    return code, explanation


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

def _count_high_findings(perf: list[dict], sec: list[dict]) -> int:
    return sum(1 for f in perf + sec if f.get("severity") == "high")


def _verify(
    optimized_code: str,
    before_time: str,
    before_perf: list[dict],
    before_sec: list[dict],
) -> tuple[bool, str, dict, dict, dict]:
    """
    Run AST analyzers on *optimized_code* and decide if it is an improvement.

    Returns
    -------
    (improved, reason, after_time, after_space, after_findings)
    """
    # 1. Syntax check
    try:
        ast.parse(optimized_code)
    except SyntaxError as exc:
        return False, f"syntax error in optimized code: {exc}", {}, {}, {}

    # 2. Re-analyze
    after_time  = analyze_time(optimized_code)
    after_space = analyze_space(optimized_code)
    after_perf  = analyze_performance(optimized_code)
    after_sec   = analyze_security(optimized_code)

    at = after_time.get("complexity", "unknown")
    bt = before_time

    # 3. Improvement criteria
    rank_improved  = _rank(at) < _rank(bt)
    same_rank      = _rank(at) == _rank(bt)
    fewer_high     = _count_high_findings(after_perf, after_sec) < _count_high_findings(before_perf, before_sec)
    improved       = rank_improved or (same_rank and fewer_high)

    if not improved:
        at_high = _count_high_findings(after_perf, after_sec)
        bt_high = _count_high_findings(before_perf, before_sec)
        reason = (
            f"still {at} (was {bt})"
            if not same_rank else
            f"same complexity {at} and high-severity count unchanged ({at_high} vs {bt_high} before)"
        )
        return False, reason, after_time, after_space, {"performance": after_perf, "security": after_sec}

    return True, "", after_time, after_space, {"performance": after_perf, "security": after_sec}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def optimize(code: str, analysis: dict) -> dict:
    """
    Optimize *code* using an LLM guided by the deterministic *analysis*.

    Returns a dict with keys:
        status          "verified" | "rejected" | "failed"
        optimized_code  str  (present unless status=="failed")
        explanation     str
        attempts        int
        before          {time, space}
        after           {time, space}   (from our analyzer, not the LLM)
        after_findings  {performance, security}
        validation      {syntax_ok, complexity_improved, behavior}
        note            str  (human-readable reason for rejected/failed)
    """
    before_time  = analysis.get("time",  {}).get("complexity", "unknown")
    before_space = analysis.get("space", {}).get("complexity", "unknown")
    before_perf  = analysis.get("performance", []) or []
    before_sec   = analysis.get("security",    []) or []

    fix_hints = _build_fix_hints(analysis)

    # We'll try up to 2 attempts
    last_code: str | None = None
    last_explanation: str = ""
    last_after_time: dict = {}
    last_after_space: dict = {}
    last_after_findings: dict = {}
    last_reason: str = ""

    for attempt in range(1, 3):
        feedback = ""
        if attempt == 2 and last_reason:
            # Build evidence reasons from last analysis
            evidence_reasons = "; ".join(
                e.get("reason", "")
                for e in (last_after_time.get("evidence") or [])[:2]
            )
            feedback = (
                f"Your previous answer is still {last_after_time.get('complexity','unknown')} "
                f"because {evidence_reasons or last_reason}. Fix exactly this."
            )

        prompt = _build_prompt(code, analysis, fix_hints, feedback)

        try:
            raw = await generate(prompt)
        except RuntimeError as exc:
            return {
                "status": "failed",
                "optimized_code": None,
                "explanation": "",
                "attempts": attempt,
                "before": {"time": before_time, "space": before_space},
                "after":  {},
                "after_findings": {},
                "validation": {"syntax_ok": False, "complexity_improved": False, "behavior": {}},
                "note": f"AI optimization unavailable — deterministic analysis shown. ({exc})",
            }

        opt_code, explanation = _parse_response(raw)
        if opt_code is None:
            last_reason = "no ```python block found in response"
            last_code = None
            continue

        last_code        = opt_code
        last_explanation = explanation

        improved, reason, after_time, after_space, after_findings = _verify(
            opt_code, before_time, before_perf, before_sec
        )
        last_after_time     = after_time
        last_after_space    = after_space
        last_after_findings = after_findings
        last_reason         = reason

        if improved:
            # Behavioral test
            behavior = check_behavior(code, opt_code)
            at = after_time.get("complexity", "unknown")
            as_ = after_space.get("complexity", "unknown")
            return {
                "status": "verified",
                "optimized_code": opt_code,
                "explanation": explanation,
                "attempts": attempt,
                "before": {"time": before_time, "space": before_space},
                "after":  {"time": at, "space": as_},
                "after_findings": after_findings,
                "validation": {
                    "syntax_ok": True,
                    "complexity_improved": True,
                    "behavior": behavior,
                },
                "note": "",
            }

    # Exhausted all attempts
    if last_code is not None:
        # LLM produced code but our verifier rejected it
        behavior = check_behavior(code, last_code)
        at  = last_after_time.get("complexity",  "unknown")
        as_ = last_after_space.get("complexity", "unknown")
        return {
            "status": "rejected",
            "optimized_code": last_code,
            "explanation": last_explanation,
            "attempts": 2,
            "before": {"time": before_time, "space": before_space},
            "after":  {"time": at, "space": as_},
            "after_findings": last_after_findings,
            "validation": {
                "syntax_ok": True,
                "complexity_improved": False,
                "behavior": behavior,
            },
            "note": f"AI suggestion not verified — our analyzer found it is still {last_reason}",
        }

    # LLM never returned parseable code
    return {
        "status": "failed",
        "optimized_code": None,
        "explanation": "",
        "attempts": 2,
        "before": {"time": before_time, "space": before_space},
        "after":  {},
        "after_findings": {},
        "validation": {"syntax_ok": False, "complexity_improved": False, "behavior": {}},
        "note": "AI optimization unavailable — deterministic analysis shown.",
    }
