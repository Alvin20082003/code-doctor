// Overview tab — prioritized issue list, critical/high first

const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
const SEV_COLORS = {
  critical: { bg: 'var(--err-dim)',  border: 'var(--err-border)',  text: 'var(--sev-critical)' },
  high:     { bg: 'var(--err-dim)',  border: 'var(--err-border)',  text: 'var(--sev-high)' },
  medium:   { bg: 'var(--warn-dim)', border: 'var(--warn-border)', text: 'var(--sev-medium)' },
  low:      { bg: 'var(--elevated)', border: 'var(--border)',      text: 'var(--muted)' },
  info:     { bg: 'var(--elevated)', border: 'var(--border)',      text: 'var(--muted)' },
}

function SevPill({ sev }) {
  const c = SEV_COLORS[sev] || SEV_COLORS.info
  return (
    <span style={{
      padding: '2px 7px',
      borderRadius: 4,
      background: c.bg,
      border: `1px solid ${c.border}`,
      color: c.text,
      fontSize: 10,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      flexShrink: 0,
    }}>
      {sev}
    </span>
  )
}

export default function OverviewTab({ performance = [], security = [], time, space, onHighlightLine }) {
  const issues = [
    ...performance.map(f => ({ ...f, _src: 'perf', title: f.type?.replace(/_/g, ' ') ?? 'Performance issue' })),
    ...security.map(f => ({ ...f, _src: 'sec',  title: f.category?.replace(/_/g, ' ') ?? 'Security issue' })),
  ].sort((a, b) => (SEV_ORDER[a.severity] ?? 99) - (SEV_ORDER[b.severity] ?? 99))

  const timeC = time?.complexity ?? '?'
  const spaceC = space?.complexity ?? '?'

  if (issues.length === 0) {
    return (
      <div style={{
        padding: '32px 0',
        textAlign: 'center',
        color: 'var(--success)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 10,
      }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" fill="var(--success-dim)" stroke="var(--success)" strokeWidth="1.5"/>
          <path d="M7 12.5l3.5 3.5 6.5-7" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span style={{ fontSize: 14, fontWeight: 600 }}>No issues found</span>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>
          Time {timeC} · Space {spaceC}
        </span>
      </div>
    )
  }

  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 10 }}>
        {issues.length} issue{issues.length !== 1 ? 's' : ''} sorted by severity
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {issues.map((f, i) => (
          <div key={i} style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 10,
            padding: '8px 12px',
            background: 'var(--elevated)',
            border: '1px solid var(--border)',
            borderRadius: 6,
          }}>
            <SevPill sev={f.severity} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 2 }}>
                {f.title}
              </div>
              <div style={{
                fontSize: 11,
                color: 'var(--muted)',
                fontFamily: 'JetBrains Mono, monospace',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {(f.evidence || '').slice(0, 80)}{(f.evidence || '').length > 80 ? '…' : ''}
              </div>
              {f.fix && (
                <div style={{ fontSize: 11, color: 'var(--dim)', marginTop: 2 }}>
                  → {f.fix.slice(0, 70)}{f.fix.length > 70 ? '…' : ''}
                </div>
              )}
            </div>
            {f.line != null && f.line > 0 && (
              <button
                onClick={() => onHighlightLine && onHighlightLine(f.line)}
                style={{
                  padding: '2px 8px',
                  borderRadius: 4,
                  border: '1px solid var(--border)',
                  background: 'var(--bg)',
                  color: 'var(--accent)',
                  fontSize: 11,
                  fontFamily: 'JetBrains Mono, monospace',
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                L{f.line}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
