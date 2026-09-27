import { useEffect, useState } from 'react'
import Editor from '@monaco-editor/react'
import { API_BASE } from '../config.js'

const EDITOR_OPTIONS = {
  minimap: { enabled: false },
  fontSize: 13,
  lineHeight: 20,
  fontFamily: "'JetBrains Mono', monospace",
  scrollBeyondLastLine: false,
  padding: { top: 12, bottom: 12 },
  wordWrap: 'on',
  renderLineHighlight: 'gutter',
  overviewRulerLanes: 0,
}

export default function InputScreen({ code, setCode, onAnalyze, isRunning, editorRef }) {
  const [fixtures, setFixtures] = useState([])
  const [fixturesError, setFixturesError] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/api/fixtures`)
      .then(r => r.json())
      .then(data => setFixtures(Array.isArray(data) ? data : []))
      .catch(() => setFixturesError(true))
  }, [])

  const isEmpty = !code.trim()

  function handleEditorMount(editor) {
    if (editorRef) editorRef.current = editor
  }

  return (
    <div>
      {/* Tagline */}
      <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 20, marginTop: 0 }}>
        How will your code behave at scale?
      </p>

      {/* Editor card */}
      <div style={{
        background: '#fff',
        borderRadius: 16,
        boxShadow: '0 1px 3px rgba(0,0,0,0.10)',
        overflow: 'hidden',
        marginBottom: 16,
      }}>
        <Editor
          height="320px"
          defaultLanguage="python"
          language="python"
          value={code}
          onChange={v => setCode(v ?? '')}
          onMount={handleEditorMount}
          options={EDITOR_OPTIONS}
          theme="vs"
        />
      </div>

      {/* Controls row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        {/* Language pill */}
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '5px 12px',
          borderRadius: 20,
          background: '#E8F0FE',
          color: 'var(--accent)',
          fontSize: 13,
          fontWeight: 500,
        }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
          </svg>
          Python
        </span>

        {/* Analyze button */}
        <button
          onClick={onAnalyze}
          disabled={isRunning || isEmpty}
          title={isEmpty ? 'Paste some Python code first' : ''}
          style={{
            padding: '8px 22px',
            borderRadius: 20,
            border: 'none',
            background: isRunning || isEmpty ? '#BDC1C6' : 'var(--accent)',
            color: '#fff',
            fontSize: 14,
            fontWeight: 600,
            cursor: isRunning || isEmpty ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            transition: 'background 0.15s',
          }}
        >
          {isRunning ? (
            <>
              <Spinner />
              Analyzing…
            </>
          ) : 'Analyze'}
        </button>

        {isEmpty && !isRunning && (
          <span style={{ color: 'var(--muted)', fontSize: 13 }}>
            Paste Python code above to get started
          </span>
        )}
      </div>

      {/* Fixtures chips */}
      {!fixturesError && fixtures.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <span style={{ fontSize: 13, color: 'var(--muted)', marginRight: 10 }}>Try:</span>
          <div style={{ display: 'inline-flex', flexWrap: 'wrap', gap: 8 }}>
            {fixtures.map(f => (
              <button
                key={f.name}
                onClick={() => setCode(f.code)}
                disabled={isRunning}
                style={{
                  padding: '4px 14px',
                  borderRadius: 16,
                  border: '1px solid var(--border)',
                  background: '#fff',
                  color: 'var(--text)',
                  fontSize: 13,
                  cursor: isRunning ? 'not-allowed' : 'pointer',
                  fontFamily: 'inherit',
                  transition: 'border-color 0.15s',
                }}
                onMouseEnter={e => { if (!isRunning) e.target.style.borderColor = 'var(--accent)' }}
                onMouseLeave={e => { e.target.style.borderColor = 'var(--border)' }}
              >
                {f.name.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Spinner() {
  return (
    <svg
      width="14" height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      style={{ animation: 'spin 0.8s linear infinite' }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25"/>
      <path d="M12 2 A10 10 0 0 1 22 12" />
    </svg>
  )
}
