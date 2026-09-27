# How to run Code Doctor (copy-paste)

Open 4 terminals and run them **in this order**:
1 AI → 2 Backend → 3 Frontend → 4 Warm-up → 5 Browser

## Terminal 1: IBM Granite (AI)
```powershell
Get-Process -Name "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force
$env:CUDA_VISIBLE_DEVICES="-1"
ollama serve
```
Wait for: `Listening on 127.0.0.1:11434`. Keep this window open.

## Terminal 2: Backend
```powershell
cd J:\IBM\code-doctor\backend
.\venv\Scripts\activate
python -m uvicorn main:app --reload
```
Wait for: `Application startup complete`. Keep this window open.

## Terminal 3: Frontend
```powershell
cd J:\IBM\code-doctor\frontend
npm run dev
```
Wait for: `Local: http://localhost:5173`. Keep this window open.

## Terminal 4: Warm up Granite (before any demo)
```powershell
cd J:\IBM\code-doctor\backend
.\venv\Scripts\activate
python scripts\smoke_test.py hero_endpoint
```
Wait for: `Optimizer : verified` (1–2 min the first time).

## Browser
Open http://localhost:5173, click **★ hero endpoint**, then **Analyze**.

## Troubleshooting
| Problem | Fix |
|---|---|
| `Ollama unreachable` | Terminal 1 is not running: start it again |
| `bind: Only one usage of each socket address` | An old Ollama is running: run Terminal 1's first line again |
| `CUDA error` | You forgot `$env:CUDA_VISIBLE_DEVICES="-1"` |
| Browser shows "Backend offline" | Terminal 2 is not running |
| http://localhost:8000 shows 404 | Normal: that's the API. The website is http://localhost:5173 |

Shortcut: double-click `START-DEMO.bat` to open all 3 servers automatically.
