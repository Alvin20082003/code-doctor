"""
tests/test_api.py

FastAPI integration tests using TestClient.
Tests health, fixtures, validation, scoring, and growth curve caps.
"""
from __future__ import annotations

import json
import pathlib
import time

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# The TestClient must be able to import main.py from the backend/ root.
# pytest is run from backend/, so sys.path already includes it.
# ---------------------------------------------------------------------------
from main import app

client = TestClient(app)

_FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (_FIXTURES_DIR / name).read_text(encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Fixtures endpoint
# ---------------------------------------------------------------------------

def test_fixtures_returns_list():
    resp = client.get("/api/fixtures")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5, f"Expected ≥5 fixtures, got {len(data)}: {[f['name'] for f in data]}"


def test_fixtures_have_name_and_code():
    resp = client.get("/api/fixtures")
    for item in resp.json():
        assert "name" in item
        assert "code" in item
        assert len(item["code"]) > 0


# ---------------------------------------------------------------------------
# Analyze — validation
# ---------------------------------------------------------------------------

def test_analyze_rejects_empty_code():
    resp = client.post("/api/analyze", json={"code": "", "language": "python"})
    assert resp.status_code == 400


def test_analyze_rejects_whitespace_only_code():
    resp = client.post("/api/analyze", json={"code": "   \n  ", "language": "python"})
    assert resp.status_code == 400


def test_analyze_rejects_too_long_code():
    resp = client.post("/api/analyze", json={"code": "x" * 20_001, "language": "python"})
    assert resp.status_code == 400


def test_analyze_returns_job_id():
    resp = client.post("/api/analyze", json={"code": "def f(): pass", "language": "python"})
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert len(data["job_id"]) > 0


# ---------------------------------------------------------------------------
# Full pipeline — nested_loop.py must score below 60
# ---------------------------------------------------------------------------

def _wait_for_report(job_id: str, retries: int = 40, delay: float = 0.25) -> dict:
    """Poll GET /api/jobs/{job_id} until a final report is available."""
    for _ in range(retries):
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data.get("status") != "running":
            return data
        time.sleep(delay)
    raise TimeoutError(f"Job {job_id} did not complete in time")


def test_nested_loop_score_below_60():
    code = _read_fixture("nested_loop.py")
    resp = client.post("/api/analyze", json={"code": code, "language": "python"})
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    report = _wait_for_report(job_id)
    score = report.get("score")
    assert score is not None, f"No score in report: {report}"
    assert score < 60, f"Expected score < 60 for nested_loop, got {score}"


# ---------------------------------------------------------------------------
# scoring.py unit tests
# ---------------------------------------------------------------------------

def test_scale_score_nested_loop():
    """Directly test scale_score with nested_loop analysis."""
    from scoring import scale_score
    from analyzers.complexity import analyze_time, analyze_space
    from analyzers.performance import analyze_performance
    from analyzers.security import analyze_security

    code = _read_fixture("nested_loop.py")
    time_r = analyze_time(code)
    space_r = analyze_space(code)
    perf_r = analyze_performance(code)
    sec_r = analyze_security(code)

    result = scale_score(time_r, space_r, perf_r, sec_r)
    assert "score" in result
    assert "breakdown" in result
    assert result["score"] < 60, f"Expected < 60, got {result['score']}"
    bd = result["breakdown"]
    assert set(bd.keys()) == {"time", "space", "performance", "security"}
    assert sum(bd.values()) == result["score"]


# ---------------------------------------------------------------------------
# growth_curve — O(2^n) must never exceed 1e15
# ---------------------------------------------------------------------------

def test_growth_curve_exponential_capped():
    from scoring import growth_curve
    points = growth_curve("O(2^n)")
    assert len(points) == 5, f"Expected 5 points, got {len(points)}"
    for p in points:
        assert p["ops"] <= 1e15, (
            f"n={p['n']}: ops={p['ops']} exceeds cap 1e15"
        )


def test_growth_curve_unknown_returns_empty():
    from scoring import growth_curve
    assert growth_curve("unknown") == []


def test_growth_curve_n_values():
    from scoring import growth_curve
    points = growth_curve("O(n)")
    ns = [p["n"] for p in points]
    assert ns == [10, 100, 1_000, 10_000, 100_000]


def test_growth_curve_ops_monotonic_for_on():
    from scoring import growth_curve
    points = growth_curve("O(n)")
    ops = [p["ops"] for p in points]
    assert ops == sorted(ops), "O(n) ops should be monotonically increasing"


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id} — unknown job returns 404
# ---------------------------------------------------------------------------

def test_get_unknown_job_returns_404():
    resp = client.get("/api/jobs/does-not-exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SSE events endpoint — basic structure check
# ---------------------------------------------------------------------------

def test_events_unknown_job_returns_404():
    # SSE endpoint should 404 for unknown job
    resp = client.get("/api/jobs/does-not-exist/events")
    assert resp.status_code == 404
