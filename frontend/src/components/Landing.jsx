import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import { API_BASE } from '../config.js'
import LandingInfo from './LandingInfo.jsx'

const EDITOR_OPTIONS = {
  minimap: { enabled: false },
  fontSize: 13,
  lineHeight: 21,
  fontFamily: "'JetBrains Mono', monospace",
  scrollBeyondLastLine: false,
  padding: { top: 14, bottom: 14 },
  wordWrap: 'on',
  renderLineHighlight: 'line',
  overviewRulerLanes: 0,
  glyphMargin: false,
  folding: false,
  lineNumbersMinChars: 3,
}

export default function Landing({ code, setCode, onAnalyze, editorRef }) {
  const [fixtures, setFixtures] = useState([])
  const [editorKey, setEditorKey] = useState(0)  // bump to force remount on fixture load
  const localEditorRef = useRef(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/fixtures`)
      .then(r => r.json())
      .then(data => setFixtures(Array.isArray(data) ? data : []))
      .catch(() => {})
  }, [])

  function handleEditorMount(editor) {
    localEditorRef.current = editor
    if (editorRef) editorRef.current = editor
  }

  // Bug #1 fix: use editor.setValue() directly for instant, reliable replacement.
  // Also bump editorKey as a fallback for full remount if needed.
  function loadFixture(fixtureCode) {
    setCode(fixtureCode)
    // Directly set value on the Monaco instance — the safest way to
    // programmatically replace content without losing the model reference
    if (localEditorRef.current) {
      localEditorRef.current.setValue(fixtureCode)
    } else {
      // Editor not mounted yet — bump key to force a fresh mount with new value
      setEditorKey(k => k + 1)
    }
  }

  const isEmpty = !code.trim()

  return (
    <div style={{
      flex: 1,
      overflow: 'auto',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '60px 24px 80px',
    }}>
      {/* Hero headline */}
      <div style={{ textAlign: 'center', marginBottom: 48, maxWidth: 600 }}>
        <h1 style={{
          fontSize: 36,
          fontWeight: 600,
          color: 'var(--text)',
          letterSpacing: '-0.8px',
          lineHeight: 1.2,
          marginBottom: 14,
        }}>
          Will your code survive scale?
        </h1>
        <p style={{ fontSize: 15, color: 'var(--muted)', lineHeight: 1.6, maxWidth: 480, margin: '0 auto' }}>
          Deterministic complexity analysis + IBM Granite optimization,{' '}
          <span style={{ color: 'var(--text)' }}>verified before you see it.</span>
        </p>
      </div>

      {/* Editor card */}
      <div style={{
        width: '100%',
        maxWidth: 720,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        overflow: 'hidden',
        marginBottom: 16,
      }}>
        {/* Card header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          height: 40,
          borderBottom: '1px solid var(--border)',
          background: 'var(--elevated)',
          gap: 12,
        }}>
          {/* File tab */}
          <span style={{
            fontSize: 12,
            fontFamily: 'JetBrains Mono, monospace',
            color: 'var(--text)',
            padding: '0 12px',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            borderBottom: '2px solid var(--accent)',
            marginBottom: -1,
          }}>
            main.py
          </span>

          {/* Python badge */}
          <span style={{
            fontSize: 11,
            color: 'var(--accent)',
            background: 'var(--accent-dim)',
            border: '1px solid var(--accent-border)',
            padding: '2px 8px',
            borderRadius: 4,
            fontWeight: 500,
          }}>
            Python
          </span>

          {/* Analyze button */}
          <button
            onClick={onAnalyze}
            disabled={isEmpty}
            style={{
              marginLeft: 'auto',
              padding: '6px 18px',
              borderRadius: 6,
              border: 'none',
              background: isEmpty ? 'var(--elevated)' : 'var(--accent)',
              color: isEmpty ? 'var(--dim)' : '#fff',
              fontSize: 12,
              fontWeight: 600,
              cursor: isEmpty ? 'not-allowed' : 'pointer',
              letterSpacing: '-0.1px',
              transition: 'background 0.15s',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
            title={isEmpty ? 'Paste Python code first' : ''}
          >
            Analyze →
          </button>
        </div>

        {/* Monaco editor */}
        <Editor
          key={editorKey}
          height="378px"
          language="python"
          value={code}
          onChange={v => setCode(v ?? '')}
          onMount={handleEditorMount}
          options={EDITOR_OPTIONS}
          theme="vs-dark"
        />
      </div>

      {/* Examples row */}
      {fixtures.length > 0 && (
        <div style={{
          width: '100%',
          maxWidth: 720,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: 12, color: 'var(--muted)', marginRight: 4 }}>Examples:</span>
          {fixtures.map(f => (
            <button
              key={f.name}
              onClick={() => loadFixture(f.code)}
              style={{
                padding: '4px 12px',
                borderRadius: 5,
                border: '1px solid var(--border)',
                background: 'var(--elevated)',
                color: f.name === 'hero_endpoint' ? 'var(--accent)' : 'var(--text)',
                fontSize: 12,
                cursor: 'pointer',
                fontFamily: 'inherit',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                transition: 'border-color 0.12s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)' }}
            >
              {f.name === 'hero_endpoint' && (
                <span style={{ fontSize: 10, color: '#F5A524' }}>★</span>
              )}
              {f.name.replace(/_/g, ' ')}
              {f.name === 'hero_endpoint' && (
                <span style={{
                  fontSize: 10,
                  background: 'var(--accent-dim)',
                  color: 'var(--accent)',
                  padding: '1px 5px',
                  borderRadius: 3,
                }}>Demo</span>
              )}
            </button>
          ))}
        </div>
      )}
      <LandingInfo />
    </div>
  )
}
