"""
backend/main.py

FastAPI application for Code Doctor.
Provides async SSE-based analysis pipeline with per-job event queues.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
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
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(fn, *args),
            timeout=timeout,
        )
        await queue.put({"type": "agent", "name": name, "status": "done"})
        await queue.put({"type": "result", "name": name, "data": result})
        return result
    except asyncio.TimeoutError:
        msg = f"timed out after {timeout}s"
        await queue.put({"type": "agent", "name": name, "status": "failed", "message": msg})
        return None
    except Exception as exc:
        await queue.put({"type": "agent", "name": name, "status": "failed", "message": str(exc)})
        return None


async def _run_pipeline(job_id: str, code: str) -> None:
    """Full analysis pipeline for a single job."""
    queue: asyncio.Queue = _jobs[job_id]["queue"]

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

    analysis = {
        "time":        time_result,
        "space":       space_result,
        "performance": perf_result,
        "security":    sec_result,
    }

    # -----------------------------------------------------------------------
    # Step 2: optimizer (async, runs in event loop directly)
    # -----------------------------------------------------------------------
    await queue.put({"type": "agent", "name": "optimizer", "status": "running"})
    try:
        opt_result = await asyncio.wait_for(optimize(code, analysis), timeout=8.0)
        await queue.put({"type": "agent", "name": "optimizer", "status": "done"})
        await queue.put({"type": "result", "name": "optimizer", "data": opt_result})
    except asyncio.TimeoutError:
        opt_result = {"status": "failed", "note": "optimizer timed out"}
        await queue.put({"type": "agent", "name": "optimizer", "status": "failed",
                         "message": "timed out after 8s"})
    except Exception as exc:
        opt_result = {"status": "failed", "note": str(exc)}
        await queue.put({"type": "agent", "name": "optimizer", "status": "failed",
                         "message": str(exc)})

    # -----------------------------------------------------------------------
    # Step 3: scoring
    # -----------------------------------------------------------------------
    score_data = scale_score(time_result, space_result, perf_result, sec_result)
    curve_before = growth_curve(time_result.get("complexity", "unknown"))

    # If optimizer returned optimised code, re-analyse for curve_after
    curve_after: list[dict] = []
    optimized_code = opt_result.get("optimized_code") if isinstance(opt_result, dict) else None
    if optimized_code:
        try:
            opt_time = await asyncio.to_thread(analyze_time, optimized_code)
            curve_after = growth_curve(opt_time.get("complexity", "unknown"))
        except Exception:
            curve_after = []

    # -----------------------------------------------------------------------
    # Step 4: final report
    # -----------------------------------------------------------------------
    report = {
        **analysis,
        "optimizer": opt_result,
        "score":       score_data["score"],
        "breakdown":   score_data["breakdown"],
        "curve_before": curve_before,
        "curve_after":  curve_after,
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
