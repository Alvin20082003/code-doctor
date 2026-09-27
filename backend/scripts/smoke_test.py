"""
backend/scripts/smoke_test.py

Manual smoke test: POST nested_loop.py to /api/analyze, stream events, print summary.
Run from backend/ with:
    python scripts/smoke_test.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import httpx

BASE_URL = "http://localhost:8000"
FIXTURE = pathlib.Path(__file__).parent.parent / "fixtures" / "nested_loop.py"


def main() -> None:
    code = FIXTURE.read_text(encoding="utf-8-sig")

    # POST to /api/analyze
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        resp = client.post("/api/analyze", json={"code": code, "language": "python"})
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        print(f"Job submitted: {job_id}")

        # Stream SSE events
        final_report: dict | None = None
        with client.stream("GET", f"/api/jobs/{job_id}/events") as stream:
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

                # Pretty-print: truncate result data to 120 chars
                event_type = event.get("type", "")
                if event_type == "result":
                    data_repr = json.dumps(event.get("data", {}))
                    if len(data_repr) > 120:
                        data_repr = data_repr[:120] + "…"
                    print(f"[{event_type}] name={event.get('name')}  data={data_repr}")
                elif event_type == "final":
                    print(f"[{event_type}] (report omitted — see summary below)")
                    final_report = event.get("report", {})
                    break
                else:
                    print(f"[{event_type}] name={event.get('name', '-')}  status={event.get('status', '-')}")

        # Summary
        if final_report:
            score = final_report.get("score", "?")
            time_c = final_report.get("time", {}).get("complexity", "?")
            print(f"\n=== SUMMARY ===")
            print(f"Score         : {score}/100")
            print(f"Time complexity: {time_c}")
            breakdown = final_report.get("breakdown", {})
            for k, v in breakdown.items():
                print(f"  {k:<12}: {v}")
        else:
            print("No final report received.")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("ERROR: Could not connect. Start the server first:")
        print("  uvicorn main:app --reload --port 8000")
        sys.exit(1)
