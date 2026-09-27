// Pipeline stepper: Parse → Time → Space → Performance → Security → Optimizer → Verify
// Shows step status, duration_ms when done, live elapsed timer while running.

const STEPS = [
  { key: 'parse',           label: 'Parse',           icon: '⬡' },
  { key: 'time_complexity', label: 'Time',             icon: 'τ' },
  { key: 'space_complexity',label: 'Space',            icon: '∑' },
  { key: 'performance',     label: 'Perf',             icon: '⚡' },
  { key: 'security',        label: 'Security',         icon: '⊛' },
  { key: 'optimizer',       label: 'Granite',          icon: '◈' },
  { key: 'verify',          label: 'Verify',           icon: '✓' },
]

function fmtMs(ms) {
  if (ms == null) return ''
  if (ms < 1) return '<1ms'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function fmtElapsed(ms) {
  const s = Math.floor(ms / 1000)
  const tenths = Math.floor((ms % 1000) / 100)
  return `${s}.${tenths}s`
}

function getStepStatus(key, agents, phase, optimizerStatus) {
  // Synthetic steps
  if (key === 'parse') {
    const any = Object.values(agents).some(a => a.status !== 'waiting')
    if (any) return { status: 'done', duration_ms: null }
    return { status: phase === 'analyzing' || phase === 'report' ? 'done' : 'waiting', duration_ms: null }
  }
  if (key === 'verify') {
    if (phase === 'report') return { status: 'done', duration_ms: null }
    const optDone = agents.optimizer?.status === 'done'
    if (optDone) return { status: 'running', duration_ms: null }
    return { status: 'waiting', duration_ms: null }
  }
  // Granite step — show 'skipped' when optimizer decided not_needed
  if (key === 'optimizer' && optimizerStatus === 'not_needed') {
    const a = agents[key]
    return { status: 'skipped', duration_ms: a?.duration_ms ?? null, message: '' }
  }
  const a = agents[key]
  if (!a) return { status: 'waiting', duration_ms: null }
  return { status: a.status, duration_ms: a.duration_ms, message: a.message }
}

export default function PipelinePanel({ agents, elapsedMs, phase, optimizerStatus }) {
  const isRunning = phase === 'analyzing'
  const isDone = phase === 'report'

  return (
    <div style={{
      padding: '16px 20px 0',
      borderBottom: '1px solid var(--border)',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 12,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Pipeline
        </span>
        {isRunning && (
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            color: 'var(--accent)',
          }}>
            ● {fmtElapsed(elapsedMs)}
          </span>
        )}
        {isDone && (
          <span style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            color: 'var(--success)',
          }}>
            ✓ done
          </span>
        )}
      </div>

      {/* Steps */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 0,
        marginBottom: 16,
        overflowX: 'auto',
      }}>
        {STEPS.map((step, idx) => {
          const { status, duration_ms, message } = getStepStatus(step.key, agents, phase, optimizerStatus)
          return (
            <div key={step.key} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
              <StepNode label={step.label} icon={step.icon} status={status} durationMs={duration_ms} message={message} />
              {idx < STEPS.length - 1 && (
                <div style={{
                  width: 20,
                  height: 1,
                  background: status === 'done' ? 'var(--border-md)' : 'var(--border)',
                  flexShrink: 0,
                  margin: '0 -1px',
                  marginTop: -8,
                }} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function StepNode({ label, icon, status, durationMs, message }) {
  const colors = {
    waiting: { ring: 'var(--border)',    icon: 'var(--dim)',    text: 'var(--dim)' },
    running: { ring: 'var(--accent)',    icon: 'var(--accent)', text: 'var(--accent)' },
    done:    { ring: 'var(--success)',   icon: 'var(--success)', text: 'var(--muted)' },
    failed:  { ring: 'var(--sev-high)',  icon: 'var(--sev-medium)', text: 'var(--sev-medium)' },
    skipped: { ring: 'var(--border)',    icon: 'var(--dim)',    text: 'var(--dim)' },
  }
  const c = colors[status] || colors.waiting

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 4,
      minWidth: 56,
    }}>
      {/* Circle */}
      <div style={{
        width: 32,
        height: 32,
        borderRadius: '50%',
        border: `1.5px solid ${c.ring}`,
        background: status === 'running' ? 'var(--accent-dim)' : status === 'done' ? 'var(--success-dim)' : 'var(--elevated)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 13,
        color: c.icon,
        transition: 'all 0.2s',
        animation: status === 'done' ? 'fade-slide-in 0.2s ease forwards' : 'none',
      }}>
        {status === 'running' ? (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
            style={{ animation: 'spin 0.9s linear infinite' }}>
            <circle cx="12" cy="12" r="10" strokeOpacity="0.2"/>
            <path d="M12 2 A10 10 0 0 1 22 12" />
          </svg>
        ) : status === 'done' ? (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M5 12l5 5L20 7" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        ) : status === 'failed' ? (
          <span style={{ fontSize: 11 }}>!</span>
        ) : status === 'skipped' ? (
          <svg width="10" height="2" viewBox="0 0 10 2" fill="none">
            <line x1="0" y1="1" x2="10" y2="1" stroke="var(--dim)" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        ) : (
          <span style={{ fontSize: 12 }}>{icon}</span>
        )}
      </div>

      {/* Label */}
      <span style={{ fontSize: 10, color: c.text, fontWeight: 500, textAlign: 'center' }}>
        {status === 'skipped' ? 'skipped' : label}
      </span>

      {/* Duration */}
      {durationMs != null && (
        <span style={{ fontSize: 9, color: 'var(--dim)', fontFamily: 'JetBrains Mono, monospace' }}>
          {fmtMs(durationMs)}
        </span>
      )}
    </div>
  )
}
