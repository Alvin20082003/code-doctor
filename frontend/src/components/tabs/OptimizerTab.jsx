import { useState } from 'react'
import { DiffEditor } from '@monaco-editor/react'

const DIFF_OPTIONS = {
  renderSideBySide: true,
  minimap: { enabled: false },
  fontSize: 12,
  fontFamily: "'JetBrains Mono', monospace",
  scrollBeyondLastLine: false,
  padding: { top: 10, bottom: 10 },
  readOnly: true,
}

export default function OptimizerTab({ optimizer, originalCode }) {
  const [copied, setCopied] = useState(false)

  if (!optimizer) return <Grey note="No optimizer data received." />

  const { status, optimized_code, explanation, note, attempts, before, after, validation } = optimizer

  const behavior = validation?.behavior ?? {}
  const behaviorText = behavior.tested
    ? (behavior.passed
        ? `${behavior.cases ?? 50} users × 200 orders — outputs identical ✓`
        : `${behavior.cases ?? 50} users × 200 orders — outputs differ ✗`)
    : (behavior.reason ?? 'Static verification only')

  function handleCopy() {
    if (optimized_code) {
      navigator.clipboard.writeText(optimized_code).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      })
    }
  }

  // Already optimal
  if (status === 'not_needed') {
    return (
      <div className="anim-fade-slide" style={{
        padding: '24px 20px',
        background: 'var(--success-dim)',
        border: '1px solid var(--success-border)',
        borderRadius: 8,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="var(--success)" strokeWidth="1.5"/>
          <path d="M7 12.5l3.5 3.5 6.5-7" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--success)' }}>Already optimal ✓</div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3 }}>{note}</div>
        </div>
      </div>
    )
  }

  if (status === 'failed') return <Grey note={note} />

  if (optimized_code) {
    return (
      <div className="anim-fade-slide">
        {/* Status banner */}
        {status === 'verified' ? (
          <Banner
            color="success"
            icon={<CheckIcon />}
            text={
              <>
                Verified by Code Doctor&apos;s analyzer:{' '}
                <Mono>{before?.time ?? '?'}</Mono>
                {' → '}
                <Mono>{after?.time ?? '?'}</Mono>
              </>
            }
            sub={attempts > 1 ? `${attempts} attempts` : null}
          />
        ) : (
          <Banner
            color="warn"
            icon={<WarnIcon />}
            text={
              <>
                AI suggestion rejected — analyzer still sees{' '}
                <Mono>{after?.time ?? 'unknown'}</Mono>
              </>
            }
            sub={note}
            attempts={attempts}
          />
        )}

        {/* Diff editor header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, marginTop: 14 }}>
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>Original (left) vs. optimized (right)</span>
          <button
            onClick={handleCopy}
            style={{
              padding: '4px 12px',
              borderRadius: 5,
              border: '1px solid var(--border)',
              background: copied ? 'var(--success-dim)' : 'var(--elevated)',
              color: copied ? 'var(--success)' : 'var(--muted)',
              fontSize: 11,
              cursor: 'pointer',
              fontFamily: 'inherit',
              transition: 'all 0.15s',
            }}
          >
            {copied ? '✓ Copied' : 'Copy optimized code'}
          </button>
        </div>

        {/* DiffEditor */}
        <div style={{ borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border)', marginBottom: 12 }}>
          <DiffEditor
            height="360px"
            language="python"
            original={originalCode}
            modified={optimized_code}
            options={DIFF_OPTIONS}
            theme="vs-dark"
          />
        </div>

        {/* Explanation */}
        {explanation && (
          <blockquote style={{
            margin: '0 0 12px',
            padding: '10px 16px',
            borderLeft: '3px solid var(--accent)',
            background: 'var(--elevated)',
            borderRadius: '0 6px 6px 0',
            fontSize: 12,
            color: 'var(--muted)',
            lineHeight: 1.6,
          }}>
            {explanation}
          </blockquote>
        )}

        {/* Behavior check */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 12px', borderRadius: 5,
          background: 'var(--elevated)', border: '1px solid var(--border)',
          fontSize: 11, color: 'var(--dim)',
        }}>
          <span style={{ color: 'var(--muted)' }}>⊛</span>
          <span><strong style={{ color: 'var(--muted)' }}>Behavioral check:</strong> {behaviorText}</span>
        </div>
      </div>
    )
  }

  return <Grey note={note} />
}

function Mono({ children }) {
  return (
    <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{children}</span>
  )
}

function Banner({ color, icon, text, sub, attempts }) {
  const isSuccess = color === 'success'
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '9px 14px', borderRadius: 6, marginBottom: 2,
      background: isSuccess ? 'var(--success-dim)' : 'var(--warn-dim)',
      border: `1px solid ${isSuccess ? 'var(--success-border)' : 'var(--warn-border)'}`,
    }}>
      <span style={{ marginTop: 1, flexShrink: 0 }}>{icon}</span>
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: isSuccess ? 'var(--success)' : 'var(--sev-medium)' }}>
          {text}
        </span>
        {sub && (
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3, opacity: 0.8 }}>{sub}</div>
        )}
      </div>
      {attempts > 1 && (
        <span style={{ fontSize: 10, color: isSuccess ? 'var(--success)' : 'var(--sev-medium)', opacity: 0.7, flexShrink: 0, marginTop: 2 }}>
          {attempts} attempts
        </span>
      )}
    </div>
  )
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="var(--success)" strokeWidth="1.5"/>
      <path d="M7 12.5l3.5 3.5 6.5-7" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function WarnIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="var(--sev-medium)" strokeWidth="1.5"/>
      <path d="M12 7v5M12 16v1" stroke="var(--sev-medium)" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}

function Grey({ note }) {
  return (
    <div style={{
      padding: '32px 20px', borderRadius: 8, background: 'var(--elevated)',
      border: '1px solid var(--border)', textAlign: 'center',
    }}>
      <div style={{ fontSize: 28, marginBottom: 10 }}>🤖</div>
      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 5 }}>
        AI optimization unavailable
      </div>
      <div style={{ fontSize: 12, color: 'var(--muted)', maxWidth: 380, margin: '0 auto' }}>
        Showing deterministic analysis only.{note ? ` (${note})` : ''}
      </div>
    </div>
  )
}
