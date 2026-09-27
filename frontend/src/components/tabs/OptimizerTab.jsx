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

  const { status, optimized_code, explanation, note, attempts, before, after, validation } = optimizer

  const behavior = validation?.behavior ?? {}
  const behaviorText = behavior.tested
    ? (behavior.passed
        ? `${behavior.cases ?? 50} users × 200 orders — outputs identical ✓`
        : `${behavior.cases ?? 50} users × 200 orders — outputs differ ✗`)
    : (behavior.reason ?? 'Static verification only')

  if (status === 'failed') {
    return <Unavailable note={note} />
  }

  if (optimized_code) {
    return (
      <div className="fade-in">
        {/* Status banner */}
        {status === 'verified' ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 16px',
            borderRadius: 10,
            background: '#E6F4EA',
            border: '1px solid #CEEAD6',
            marginBottom: 16,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" fill="#1E8E3E"/>
              <path d="M7 12.5l3.5 3.5 6.5-7" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span style={{ fontSize: 13, fontWeight: 600, color: '#1E8E3E' }}>
              Verified by Code Doctor&apos;s analyzer:{' '}
              <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{before?.time ?? '?'}</span>
              {' → '}
              <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{after?.time ?? '?'}</span>
            </span>
            {attempts > 1 && (
              <span style={{ marginLeft: 'auto', fontSize: 11, color: '#1E8E3E', opacity: 0.7 }}>
                {attempts} attempt{attempts !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        ) : (
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 10,
            padding: '10px 16px',
            borderRadius: 10,
            background: '#FEF7E0',
            border: '1px solid #FDE293',
            marginBottom: 16,
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
              <circle cx="12" cy="12" r="10" fill="#F9AB00"/>
              <path d="M12 7v5M12 16v1" stroke="#fff" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <div>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#B06000' }}>
                AI suggestion rejected — our analyzer found it is still{' '}
                <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  {after?.time ?? 'unknown'}
                </span>
              </span>
              {note && (
                <div style={{ fontSize: 12, color: '#B06000', marginTop: 3, opacity: 0.8 }}>
                  {note}
                </div>
              )}
            </div>
            {attempts > 1 && (
              <span style={{ marginLeft: 'auto', fontSize: 11, color: '#B06000', opacity: 0.7, flexShrink: 0 }}>
                {attempts} attempt{attempts !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}

        {/* Diff editor */}
        <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 12 }}>
          Diff view — original (left) vs. optimized (right)
        </div>
        <div style={{
          borderRadius: 12,
          overflow: 'hidden',
          border: '1px solid var(--border)',
          marginBottom: 16,
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

        {/* Explanation */}
        {explanation && (
          <div style={{
            padding: '14px 16px',
            borderRadius: 10,
            background: '#F0F7FF',
            border: '1px solid #C5D9F7',
            fontSize: 13,
            color: '#1A5CA8',
            lineHeight: 1.6,
            marginBottom: 12,
          }}>
            <strong>Explanation: </strong>{explanation}
          </div>
        )}

        {/* Behavior test result */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 14px',
          borderRadius: 8,
          background: '#F8F9FA',
          border: '1px solid var(--border)',
          fontSize: 12,
          color: 'var(--muted)',
        }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
          </svg>
          <span><strong>Behavioral check:</strong> {behaviorText}</span>
        </div>
      </div>
    )
  }

  // No code at all (status skipped/failed)
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
      <div style={{ fontSize: 13, color: 'var(--muted)', maxWidth: 440, margin: '0 auto' }}>
        Showing deterministic analysis only.{note ? ` (${note})` : ''}
      </div>
    </div>
  )
}
