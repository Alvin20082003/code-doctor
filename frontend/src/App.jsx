import { useState, useRef, useCallback, useEffect } from 'react'
import Landing from './components/Landing.jsx'
import Workspace from './components/Workspace.jsx'
import { API_BASE } from './config.js'

// Agents in pipeline order
const AGENT_KEYS = ['time_complexity', 'space_complexity', 'performance', 'security', 'optimizer']

function makeInitialAgents() {
  return Object.fromEntries(
    AGENT_KEYS.map(k => [k, { status: 'waiting', message: '', duration_ms: null }])
  )
}

export default function App() {
  const [phase, setPhase] = useState('landing')   // 'landing' | 'analyzing' | 'report'
  const [code, setCode] = useState('')
  const [agents, setAgents] = useState(makeInitialAgents)
  const [report, setReport] = useState(null)
  const [backendError, setBackendError] = useState(false)
  const [elapsedMs, setElapsedMs] = useState(0)
  const [healthy, setHealthy] = useState(null)  // null=unknown, true, false
  const editorRef = useRef(null)
  const timerRef = useRef(null)
  const startTimeRef = useRef(null)

  // Health check
  useEffect(() => {
    const check = () => {
      fetch(`${API_BASE}/api/health`)
        .then(r => r.ok ? setHealthy(true) : setHealthy(false))
        .catch(() => setHealthy(false))
    }
    check()
    const id = setInterval(check, 15000)
    return () => clearInterval(id)
  }, [])

  const startTimer = useCallback(() => {
    startTimeRef.current = Date.now()
    setElapsedMs(0)
    timerRef.current = setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current)
    }, 100)
  }, [])

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const handleAnalyze = useCallback(async () => {
    if (!code.trim()) return

    setBackendError(false)
    setReport(null)
    setAgents(makeInitialAgents())
    setPhase('analyzing')
    startTimer()

    let jobId
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language: 'python' }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}))
        throw new Error(detail?.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      jobId = data.job_id
    } catch (err) {
      stopTimer()
      setBackendError(true)
      setPhase('landing')
      return
    }

    const es = new EventSource(`${API_BASE}/api/jobs/${jobId}/events`)

    es.onmessage = (e) => {
      let event
      try { event = JSON.parse(e.data) } catch { return }

      if (event.type === 'agent') {
        setAgents(prev => ({
          ...prev,
          [event.name]: {
            status: event.status,
            message: event.message || '',
            duration_ms: event.duration_ms ?? null,
          },
        }))
      } else if (event.type === 'final') {
        es.close()
        stopTimer()
        setReport(event.report)
        setPhase('report')
      }
    }

    es.onerror = () => {
      es.close()
      stopTimer()
    }
  }, [code, startTimer, stopTimer])

  const handleReset = useCallback(() => {
    stopTimer()
    setPhase('landing')
    setReport(null)
    setAgents(makeInitialAgents())
    setBackendError(false)
    setElapsedMs(0)
  }, [stopTimer])

  const handleHighlightLine = useCallback((lineNumber) => {
    const editor = editorRef.current
    if (!editor || !lineNumber) return
    editor.revealLineInCenter(lineNumber)
    editor.setSelection({
      startLineNumber: lineNumber,
      startColumn: 1,
      endLineNumber: lineNumber,
      endColumn: 999,
    })
    editor.focus()
  }, [])

  const isWorkspace = phase === 'analyzing' || phase === 'report'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}>
      {/* ── Top bar ─────────────────────────────────────────────────── */}
      <TopBar healthy={healthy} isWorkspace={isWorkspace} onReset={handleReset} />

      {/* ── Main ────────────────────────────────────────────────────── */}
      {backendError && (
        <div style={{
          background: 'var(--err-dim)',
          borderBottom: '1px solid var(--err-border)',
          padding: '10px 24px',
          fontSize: 13,
          color: 'var(--sev-high)',
          flexShrink: 0,
        }}>
          <strong>Backend offline</strong> — start with{' '}
          <code style={{ fontFamily: 'JetBrains Mono', fontSize: 11, color: 'var(--muted)' }}>
            uvicorn main:app --reload --port 8000
          </code>
        </div>
      )}

      {!isWorkspace ? (
        <Landing
          code={code}
          setCode={setCode}
          onAnalyze={handleAnalyze}
          editorRef={editorRef}
        />
      ) : (
        <Workspace
          code={code}
          agents={agents}
          report={report}
          phase={phase}
          elapsedMs={elapsedMs}
          onHighlightLine={handleHighlightLine}
          editorRef={editorRef}
        />
      )}
    </div>
  )
}

function TopBar({ healthy, isWorkspace, onReset }) {
  return (
    <header style={{
      height: 52,
      flexShrink: 0,
      display: 'flex',
      alignItems: 'center',
      padding: '0 20px',
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      zIndex: 200,
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ color: 'var(--accent)', fontSize: 16 }}>◆</span>
        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text)', letterSpacing: '-0.2px' }}>
          Code Doctor
        </span>
        <span style={{ color: 'var(--border-md)', userSelect: 'none' }}>·</span>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>Scale-aware code analysis</span>
      </div>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Health pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          borderRadius: 20,
          background: 'var(--elevated)',
          border: '1px solid var(--border)',
          fontSize: 11,
          color: 'var(--muted)',
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: healthy === true ? 'var(--success)' : healthy === false ? 'var(--sev-high)' : 'var(--muted)',
            flexShrink: 0,
          }} />
          IBM Granite 3.3 · {healthy === true ? 'online' : healthy === false ? 'offline' : 'checking…'}
        </div>

        {isWorkspace && (
          <button
            onClick={onReset}
            style={{
              padding: '5px 14px',
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: 'var(--elevated)',
              color: 'var(--text)',
              fontSize: 12,
              fontWeight: 500,
              cursor: 'pointer',
              letterSpacing: '-0.1px',
            }}
          >
            ← New analysis
          </button>
        )}
      </div>
    </header>
  )
}
