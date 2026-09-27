"""
backend/scripts/smoke_test.py

Manual smoke test: POST a fixture to /api/analyze, stream events, print summary.
Run from backend/ with:
    python scripts/smoke_test.py [fixture_name]

fixture_name defaults to "nested_loop". Use the stem of any .py file in fixtures/.
Example:
    python scripts/smoke_test.py hero_endpoint
"""
from __future__ import annotations

import json
import pathlib
import sys

import httpx

BASE_URL   = "http://localhost:8000"
_FIXTURES  = pathlib.Path(__file__).parent.parent / "fixtures"


def _load_fixture(name: str) -> str:
    path = _FIXTURES / f"{name}.py"
    if not path.exists():
        available = [p.stem for p in sorted(_FIXTURES.glob("*.py")) if p.name != "__init__.py"]
        print(f"ERROR: fixture '{name}' not found.")
        print(f"Available: {', '.join(available)}")
        sys.exit(1)
    return path.read_text(encoding="utf-8-sig")


def main() -> None:
    fixture_name = sys.argv[1] if len(sys.argv) > 1 else "nested_loop"
    code = _load_fixture(fixture_name)
    print(f"Fixture: {fixture_name}")

    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        resp = client.post("/api/analyze", json={"code": code, "language": "python"})
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        print(f"Job submitted: {job_id}")

        final_report: dict | None = None
        with client.stream("GET", f"/api/jobs/{job_id}/events",
                           timeout=300) as stream:
            for line in stream.iter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[len("data:"):].strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                etype = event.get("type", "")
                if etype == "result":
                    data_repr = json.dumps(event.get("data", {}))
                    if len(data_repr) > 120:
                        data_repr = data_repr[:120] + "…"
                    print(f"[{etype}] name={event.get('name')}  data={data_repr}")
                elif etype == "final":
                    print(f"[{etype}] (report received — see summary below)")
                    final_report = event.get("report", {})
                    break
                else:
                    print(f"[{etype}] name={event.get('name', '-')}  status={event.get('status', '-')}")

    if not final_report:
        print("No final report received.")
        return

    score_before = final_report.get("score", "?")
    score_after  = final_report.get("score_after")
    time_c       = final_report.get("time", {}).get("complexity", "?")
    opt          = final_report.get("optimizer", {}) or {}
    opt_status   = opt.get("status", "?")
    before_info  = opt.get("before", {})
    after_info   = opt.get("after", {})
    attempts     = opt.get("attempts", "?")

    print(f"\n{'='*50}")
    print(f"SUMMARY — {fixture_name}")
    print(f"{'='*50}")
    print(f"Score         : {score_before}/100", end="")
    if score_after is not None:
        arrow = "↑" if score_after > score_before else ("↓" if score_after < score_before else "=")
        print(f"  {arrow}  {score_after}/100 (after optimization)", end="")
    print()
    print(f"Time complexity: {time_c}")

    breakdown = final_report.get("breakdown", {})
    for k, v in breakdown.items():
        print(f"  {k:<12}: {v}")

    print(f"\nOptimizer     : {opt_status}  (attempts: {attempts})")
    if before_info and after_info:
        print(f"  Time   : {before_info.get('time','?')} → {after_info.get('time','?')}")
        print(f"  Space  : {before_info.get('space','?')} → {after_info.get('space','?')}")
    if opt_status == "rejected":
        print(f"  Note   : {opt.get('note','')}")
    elif opt_status == "failed":
        print(f"  Note   : {opt.get('note','')}")

    behavior = (opt.get("validation") or {}).get("behavior", {})
    if behavior.get("tested"):
        passed = "✓ passed" if behavior.get("passed") else "✗ FAILED"
        print(f"  Behavior test: {behavior.get('cases',0)} users × 200 orders — {passed}")
    else:
        print(f"  Behavior test: {behavior.get('reason','static verification only')}")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("ERROR: Could not connect. Start the server first:")
        print("  uvicorn main:app --reload --port 8000")
        sys.exit(1)
