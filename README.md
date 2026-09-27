# ◆ Code Doctor

**Will your code survive scale?**

AI tools write code fast, but nobody tells developers how that code behaves when users, data and traffic grow. Code Doctor analyzes backend Python code for **time and space complexity, performance bottlenecks, N+1 queries and security issues**. **IBM Granite** then proposes an optimized version, and Code Doctor **re-verifies it with its own analyzer** before showing it to you.

> The AI suggests. Our analyzer proves it.

Built with **IBM Bob** for the IBM Bob 2.0 Hackathon (lablab.ai, Sept 2026).

---

## What it does

| Step | What happens | How |
|---|---|---|
| 1. Time complexity | Detects nested loops, recursion, sorting, hidden O(n) built-ins (`sum`, `max`, `in list`…) | Python `ast`: deterministic, not guessed by an LLM |
| 2. Space complexity | Tracks auxiliary structures and recursion stack depth | Python `ast` |
| 3. Performance | N+1 queries (DB calls inside loops), list lookups in loops, repeated calls | Python `ast` |
| 4. Security | SQL injection, `eval`/`exec`, hardcoded secrets | Bandit + custom AST rules |
| 5. Optimize | Generates an optimized rewrite + plain-English explanation | **IBM Granite 3.3 (8B)** via Ollama |
| 6. Verify | Re-runs every analyzer on the AI's code; retries once with feedback; rejects unverified claims | Deterministic verifier |
| 7. Behavior check | Runs original vs optimized on generated data and compares outputs (where possible) | Sandboxed subprocess |

Every result streams live to the UI with per-stage timings, a **Scale Score (0–100)**, before/after complexity, a growth chart up to n = 100,000, and a side-by-side diff.

### Example: `get_dashboard(db, users, orders)`

| | Before | After (Granite, verified) |
|---|---|---|
| Time | `O(n*m)` | `O(n+m)` |
| Space | `O(n^2)` | `O(n+m)` |
| Scale Score | 13 / 100 | improved |
| Hardcoded secret | ✗ | `os.getenv` ✓ |

### Why "verified" matters
During development, a small LLM rewrote an O(n×m) function into code that was **still O(n×m)**, and claimed it was O(n+m). Code Doctor never trusts an LLM's complexity claim: the number shown is always computed by our analyzer. If the AI's rewrite isn't actually better, the UI shows **"AI suggestion rejected"**.

---

## Architecture

```
React + Vite UI (Monaco editor, live pipeline, Recharts)
        │  REST + Server-Sent Events
        ▼
FastAPI backend
        │
        ├── Time Complexity   ─┐
        ├── Space Complexity   │  run in parallel (asyncio.gather, 8s timeout each)
        ├── Performance / N+1  │
        └── Security (Bandit) ─┘
                 │
                 ▼
        IBM Granite optimizer (Ollama, local)
                 │
                 ▼
        Deterministic verifier + behavior test
                 │
                 ▼
        Scale Score · before/after · diff · report
```

**Resilience:** each agent has its own timeout, one failing agent never fails the scan, and if the LLM is unavailable the deterministic analysis is still shown.

---

## Tech stack

- **Backend:** Python 3.12, FastAPI, sse-starlette, `ast`, Bandit, httpx
- **AI:** IBM Granite 3.3 8B Instruct (local via Ollama); watsonx.ai provider supported via `LLM_PROVIDER=watsonx`
- **Frontend:** React, Vite, Tailwind CSS v4, Monaco Editor, Recharts
- **Built with:** IBM Bob (Agent mode) for scaffolding, analyzers, API, UI and tests
- **Tests:** pytest (LLM mocked in all tests)

---

## Run locally (Windows)

**1. Start IBM Granite (Ollama)**
```powershell
ollama pull granite3.3:8b
$env:CUDA_VISIBLE_DEVICES="-1"   # optional: use Vulkan/CPU if CUDA fails
ollama serve
```

**2. Backend**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn main:app --reload
```

**3. Frontend**
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173, then pick **★ hero endpoint** and click **Analyze**.

**Tests**
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest
```

---

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/analyze` | `{code, language}` → `{job_id}` |
| `GET /api/jobs/{id}/events` | Live SSE stream of agent progress and results |
| `GET /api/jobs/{id}` | Final report |
| `GET /api/fixtures` | Example code samples |
| `GET /api/health` | Health check |

---

## Honest limits

- Python only (the parser layer is designed to add JS/TS later).
- Big-O is **estimated from static structure**; the analyzer reports a confidence level and says "unknown" when it can't parse.
- Behavior tests run only where inputs can be generated safely; otherwise results are labeled **"static verification only"**.
- Code Doctor focuses on scale, performance and security, not on general logic bugs.

## Roadmap
- JS/TS support via Tree-sitter
- GitHub PR mode (analyze only changed functions)
- CI "complexity regression guard": fail a PR if it makes code slower at scale
- MCP server so IBM Bob can call Code Doctor directly while coding

## SDG alignment
**SDG 9** (resilient, scalable digital infrastructure) · **SDG 12** (efficient software means less compute and energy waste) · **SDG 8** (developer productivity)
