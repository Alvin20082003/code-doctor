"""
backend/main.py

FastAPI application for Code Doctor.
Provides async SSE-based analysis pipeline with per-job event queues.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import time
import uuid
from typing import Any, AsyncGenerator

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from analyzers.complexity import analyze_time, analyze_space
from analyzers.performance import analyze_performance
from analyzers.security import analyze_security
from agents.optimizer import optimize
from scoring import scale_score, growth_curve

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Code Doctor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory job store
# job_id -> {"queue": asyncio.Queue, "report": dict | None}
# ---------------------------------------------------------------------------
_jobs: dict[str, dict[str, Any]] = {}

_FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    code: str
    language: str = "python"


class AnalyzeResponse(BaseModel):
    job_id: str


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

async def _run_analyzer(
    name: str,
    fn,
    *args,
    queue: asyncio.Queue,
    timeout: float = 8.0,
) -> Any:
    """
    Run a synchronous analyzer in a thread with timeout.
    Emits running / done / failed events onto the queue.
    Returns the result or None on failure.
    """
    await queue.put({"type": "agent", "name": name, "status": "running"})
    t0 = time.monotonic()
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(fn, *args),
            timeout=timeout,
        )
        duration_ms = round((time.monotonic() - t0) * 1000)
        await queue.put({"type": "agent", "name": name, "status": "done", "duration_ms": duration_ms})
        await queue.put({"type": "result", "name": name, "data": result})
        return result
    except asyncio.TimeoutError:
        duration_ms = round((time.monotonic() - t0) * 1000)
        msg = f"timed out after {timeout}s"
        await queue.put({"type": "agent", "name": name, "status": "failed", "message": msg, "duration_ms": duration_ms})
        return None
    except Exception as exc:
        duration_ms = round((time.monotonic() - t0) * 1000)
        await queue.put({"type": "agent", "name": name, "status": "failed", "message": str(exc), "duration_ms": duration_ms})
        return None


async def _run_pipeline(job_id: str, code: str) -> None:
    """Full analysis pipeline for a single job."""
    queue: asyncio.Queue = _jobs[job_id]["queue"]
    pipeline_start = time.monotonic()

    # -----------------------------------------------------------------------
    # Step 1: run the 4 analyzers in parallel
    # -----------------------------------------------------------------------
    time_result, space_result, perf_result, sec_result = await asyncio.gather(
        _run_analyzer("time_complexity",  analyze_time,        code, queue=queue),
        _run_analyzer("space_complexity", analyze_space,       code, queue=queue),
        _run_analyzer("performance",      analyze_performance, code, queue=queue),
        _run_analyzer("security",         analyze_security,    code, queue=queue),
    )

    # Provide safe defaults if an analyzer failed
    time_result  = time_result  or {"complexity": "unknown", "confidence": "low", "evidence": []}
    space_result = space_result or {"complexity": "unknown", "confidence": "low", "evidence": []}
    perf_result  = perf_result  or []
    sec_result   = sec_result   or []

    # Compute preliminary score so optimizer can check for short-circuit
    score_data_pre = scale_score(
        time_result or {"complexity": "unknown", "confidence": "low", "evidence": []},
        space_result or {"complexity": "unknown", "confidence": "low", "evidence": []},
        perf_result or [],
        sec_result or [],
    )

    analysis = {
        "time":        time_result,
        "space":       space_result,
        "performance": perf_result,
        "security":    sec_result,
        "_score":      score_data_pre["score"],   # used by optimizer not_needed check
    }

    # -----------------------------------------------------------------------
    # Step 2: optimizer (async, runs in event loop directly)
    # -----------------------------------------------------------------------
    await queue.put({"type": "agent", "name": "optimizer", "status": "running"})
    opt_t0 = time.monotonic()
    try:
        opt_result = await asyncio.wait_for(optimize(code, analysis), timeout=180.0)
        opt_ms = round((time.monotonic() - opt_t0) * 1000)
        await queue.put({"type": "agent", "name": "optimizer", "status": "done", "duration_ms": opt_ms})
        await queue.put({"type": "result", "name": "optimizer", "data": opt_result})
    except asyncio.TimeoutError:
        opt_ms = round((time.monotonic() - opt_t0) * 1000)
        opt_result = {"status": "failed", "note": "optimizer timed out"}
        await queue.put({"type": "agent", "name": "optimizer", "status": "failed",
                         "message": "timed out after 180s", "duration_ms": opt_ms})
    except Exception as exc:
        opt_ms = round((time.monotonic() - opt_t0) * 1000)
        opt_result = {"status": "failed", "note": str(exc)}
        await queue.put({"type": "agent", "name": "optimizer", "status": "failed",
                         "message": str(exc), "duration_ms": opt_ms})

    # -----------------------------------------------------------------------
    # Step 3: scoring
    # -----------------------------------------------------------------------
    score_data = scale_score(time_result, space_result, perf_result, sec_result)
    curve_before = growth_curve(time_result.get("complexity", "unknown"))

    # If optimizer returned verified/rejected code with after complexity, use it for curve_after
    # The optimizer's verifier has already run analyze_time — use that result directly.
    curve_after: list[dict] = []
    score_after: int | None = None
    opt_after = opt_result.get("after") if isinstance(opt_result, dict) else None
    opt_after_findings = opt_result.get("after_findings") if isinstance(opt_result, dict) else None

    if opt_after and isinstance(opt_after, dict):
        after_time_complexity = opt_after.get("time", "unknown")
        curve_after = growth_curve(after_time_complexity)

        # Compute score_after using the optimizer's re-analysis findings
        after_perf = (opt_after_findings or {}).get("performance", []) if opt_after_findings else []
        after_sec  = (opt_after_findings or {}).get("security",    []) if opt_after_findings else []
        # We need a space result too — use the optimizer's after space if available
        after_space_complexity = opt_after.get("space", "unknown")
        after_time_dict  = {"complexity": after_time_complexity,  "confidence": "high", "evidence": []}
        after_space_dict = {"complexity": after_space_complexity, "confidence": "high", "evidence": []}
        score_after_data = scale_score(after_time_dict, after_space_dict, after_perf, after_sec)
        score_after = score_after_data["score"]

    # -----------------------------------------------------------------------
    # Step 4: speedup calculation
    # -----------------------------------------------------------------------
    speedup: float | None = None
    if curve_before and curve_after:
        # ops at n=100000 is the last point
        ops_b = curve_before[-1]["ops"] if curve_before else None
        ops_a = curve_after[-1]["ops"] if curve_after else None
        if ops_b and ops_a and ops_a > 0:
            speedup = round(ops_b / ops_a)

    total_ms = round((time.monotonic() - pipeline_start) * 1000)

    # -----------------------------------------------------------------------
    # Step 5: final report (strip internal _score key)
    # -----------------------------------------------------------------------
    clean_analysis = {k: v for k, v in analysis.items() if not k.startswith("_")}
    report = {
        **clean_analysis,
        "optimizer":    opt_result,
        "score":        score_data["score"],
        "breakdown":    score_data["breakdown"],
        "curve_before": curve_before,
        "curve_after":  curve_after,
        "score_after":  score_after,
        "speedup":      speedup,
        "total_ms":     total_ms,
    }
    _jobs[job_id]["report"] = report
    await queue.put({"type": "final", "report": report})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/api/fixtures")
async def list_fixtures() -> list[dict]:
    """Return all .py files in the fixtures directory."""
    results = []
    for path in sorted(_FIXTURES_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            code = path.read_text(encoding="utf-8-sig")
            results.append({"name": path.stem, "code": code})
        except Exception:
            pass
    return results


@app.post("/api/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze(req: AnalyzeRequest, background_tasks: BackgroundTasks) -> dict:
    """Submit code for analysis. Returns a job_id immediately."""
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="code must not be empty")
    if len(req.code) > 20_000:
        raise HTTPException(status_code=400, detail="code exceeds 20000 character limit")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"queue": asyncio.Queue(), "report": None}
    background_tasks.add_task(_run_pipeline, job_id, req.code)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> EventSourceResponse:
    """SSE stream of analysis events for a job. Closes after the 'final' event."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="job not found")

    async def _generator() -> AsyncGenerator[dict, None]:
        q: asyncio.Queue = _jobs[job_id]["queue"]
        while True:
            event = await q.get()
            yield {"data": json.dumps(event)}
            if event.get("type") == "final":
                break

    return EventSourceResponse(_generator())


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    """Return the final report, or {"status": "running"} if still in progress."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="job not found")
    report = _jobs[job_id].get("report")
    if report is None:
        return {"status": "running"}
    return report
