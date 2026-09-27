import { useState, useRef, useCallback } from 'react'
import InputScreen from './components/InputScreen.jsx'
import AnalysisScreen from './components/AnalysisScreen.jsx'
import ReportScreen from './components/ReportScreen.jsx'
import { API_BASE } from './config.js'

// Phase: 'input' | 'analyzing' | 'report'
export default function App() {
  const [phase, setPhase] = useState('input')
  const [code, setCode] = useState('')
  const [agents, setAgents] = useState(initialAgents())
  const [report, setReport] = useState(null)
  const [backendError, setBackendError] = useState(false)
  const editorRef = useRef(null)

  function initialAgents() {
    return {
      time_complexity:  { status: 'waiting', message: '' },
      space_complexity: { status: 'waiting', message: '' },
      performance:      { status: 'waiting', message: '' },
      security:         { status: 'waiting', message: '' },
      optimizer:        { status: 'waiting', message: '' },
    }
  }

  const handleAnalyze = useCallback(async () => {
    if (!code.trim()) return

    setBackendError(false)
    setReport(null)
    setAgents(initialAgents())
    setPhase('analyzing')

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
      if (err.message.includes('fetch') || err.message.includes('Failed')) {
        setBackendError(true)
      }
      setPhase('input')
      return
    }

    // Open SSE stream
    const es = new EventSource(`${API_BASE}/api/jobs/${jobId}/events`)

    es.onmessage = (e) => {
      let event
      try { event = JSON.parse(e.data) } catch { return }

      if (event.type === 'agent') {
        setAgents(prev => ({
          ...prev,
          [event.name]: { status: event.status, message: event.message || '' },
        }))
      } else if (event.type === 'final') {
        es.close()
        setReport(event.report)
        setPhase('report')
      }
    }

    es.onerror = () => {
      es.close()
      // If still analyzing and we have no report, stay on analysis screen
      // with whatever partial state we have — don't blank the screen
    }
  }, [code])

  const handleReset = useCallback(() => {
    setPhase('input')
    setReport(null)
    setAgents(initialAgents())
    setBackendError(false)
  }, [])

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

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* Top bar */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        padding: '16px 32px',
        background: '#fff',
        borderBottom: '1px solid var(--border)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <span style={{ fontSize: 17, fontWeight: 700, color: 'var(--accent)', letterSpacing: '-0.3px' }}>
          Code Doctor
        </span>
        {phase !== 'input' && (
          <button
            onClick={handleReset}
            style={{
              marginLeft: 'auto',
              padding: '6px 16px',
              borderRadius: 20,
              border: '1px solid var(--border)',
              background: '#fff',
              color: 'var(--text)',
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            ← New analysis
          </button>
        )}
      </header>

      <main style={{ maxWidth: 900, margin: '0 auto', padding: '32px 16px 64px' }}>
        {backendError && (
          <div style={{
            background: '#FFF3F0',
            border: '1px solid #FFDAD4',
            borderRadius: 12,
            padding: '14px 20px',
            marginBottom: 24,
            color: '#D93025',
            fontSize: 14,
          }}>
            <strong>Backend offline</strong> — start the server with <code style={{ fontFamily: 'JetBrains Mono', fontSize: 12 }}>uvicorn backend.main:app --reload</code> then try again.
          </div>
        )}

        {(phase === 'input' || phase === 'analyzing' || phase === 'report') && (
          <InputScreen
            code={code}
            setCode={setCode}
            onAnalyze={handleAnalyze}
            isRunning={phase === 'analyzing'}
            editorRef={editorRef}
          />
        )}

        {(phase === 'analyzing' || phase === 'report') && (
          <AnalysisScreen agents={agents} />
        )}

        {phase === 'report' && report && (
          <ReportScreen
            report={report}
            originalCode={code}
            onHighlightLine={handleHighlightLine}
          />
        )}
      </main>
    </div>
  )
}
