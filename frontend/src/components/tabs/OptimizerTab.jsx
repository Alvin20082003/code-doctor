import { DiffEditor } from '@monaco-editor/react'

const DIFF_OPTIONS = {
  renderSideBySide: true,
  minimap: { enabled: false },
  fontSize: 13,
  fontFamily: "'JetBrains Mono', monospace",
  scrollBeyondLastLine: false,
  padding: { top: 12, bottom: 12 },
  readOnly: true,
}

export default function OptimizerTab({ optimizer, originalCode }) {
  if (!optimizer) {
    return <Unavailable note="No optimizer data received." />
  }

  const { status, optimized_code, explanation, note } = optimizer

  if (optimized_code) {
    return (
      <div className="fade-in">
        <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>
          Diff view — original (left) vs. optimized (right)
        </div>
        <div style={{
          borderRadius: 12,
          overflow: 'hidden',
          border: '1px solid var(--border)',
        }}>
          <DiffEditor
            height="400px"
            language="python"
            original={originalCode}
            modified={optimized_code}
            options={DIFF_OPTIONS}
            theme="vs"
          />
        </div>
        {explanation && (
          <div style={{
            marginTop: 16,
            padding: '14px 16px',
            borderRadius: 10,
            background: '#F0F7FF',
            border: '1px solid #C5D9F7',
            fontSize: 13,
            color: '#1A5CA8',
            lineHeight: 1.6,
          }}>
            <strong>Explanation: </strong>{explanation}
          </div>
        )}
      </div>
    )
  }

  // Status is skipped or failed
  return <Unavailable note={note} />
}

function Unavailable({ note }) {
  return (
    <div style={{
      padding: '40px 24px',
      borderRadius: 12,
      background: '#F8F9FA',
      border: '1px solid var(--border)',
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>🤖</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>
        AI optimization unavailable
      </div>
      <div style={{ fontSize: 13, color: 'var(--muted)', maxWidth: 400, margin: '0 auto' }}>
        Showing deterministic analysis only.{note ? ` (${note})` : ''}
      </div>
    </div>
  )
}
