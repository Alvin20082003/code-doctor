const SEV = {
  critical: { bg: 'var(--err-dim)',  border: 'var(--err-border)',  text: 'var(--sev-critical)' },
  high:     { bg: 'var(--err-dim)',  border: 'var(--err-border)',  text: 'var(--sev-high)'     },
  medium:   { bg: 'var(--warn-dim)', border: 'var(--warn-border)', text: 'var(--sev-medium)'   },
  low:      { bg: 'var(--elevated)', border: 'var(--border)',      text: 'var(--muted)'        },
}

const TYPE_LABEL = {
  n_plus_one:               'N+1 Query',
  list_membership_in_loop:  'O(n) Membership',
  repeated_call_in_loop:    'Repeated Call',
}

function SevPill({ sev }) {
  const c = SEV[sev] || SEV.low
  return (
    <span style={{
      padding: '2px 7px', borderRadius: 4, fontSize: 10, fontWeight: 700,
      textTransform: 'uppercase', letterSpacing: '0.04em', flexShrink: 0,
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
    }}>{sev}</span>
  )
}

function FindingRow({ finding, onHighlightLine, showType }) {
  return (
    <div style={{
      padding: '10px 12px',
      background: 'var(--elevated)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <SevPill sev={finding.severity} />
        {showType && finding.type && (
          <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 500 }}>
            {TYPE_LABEL[finding.type] ?? finding.type.replace(/_/g, ' ')}
          </span>
        )}
        {!showType && finding.category && (
          <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 500 }}>
            {finding.category.replace(/_/g, ' ')}
          </span>
        )}
        {finding.line > 0 && (
          <button
            onClick={() => onHighlightLine?.(finding.line)}
            style={{
              marginLeft: 'auto', padding: '2px 8px', borderRadius: 4,
              border: '1px solid var(--border)', background: 'var(--bg)',
              color: 'var(--accent)', fontSize: 10,
              fontFamily: 'JetBrains Mono, monospace', cursor: 'pointer',
            }}
          >L{finding.line}</button>
        )}
      </div>
      <p style={{ margin: 0, fontSize: 12, color: 'var(--text)', lineHeight: 1.5, fontFamily: 'JetBrains Mono, monospace' }}>
        {finding.evidence}
      </p>
      {finding.fix && (
        <div style={{
          padding: '6px 10px', borderRadius: 5,
          background: 'var(--accent-dim)', border: '1px solid var(--accent-border)',
          fontSize: 11, color: 'var(--accent)', lineHeight: 1.5,
        }}>
          <strong>Fix: </strong>{finding.fix}
        </div>
      )}
    </div>
  )
}

function Empty({ label }) {
  return (
    <div style={{ padding: '32px 0', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" fill="var(--success-dim)" stroke="var(--success)" strokeWidth="1.5"/>
        <path d="M7 12.5l3.5 3.5 6.5-7" stroke="var(--success)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--success)' }}>No {label} issues found</span>
    </div>
  )
}

export function PerformanceTab({ findings, onHighlightLine }) {
  if (!findings?.length) return <Empty label="performance" />
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 2 }}>
        {findings.length} issue{findings.length !== 1 ? 's' : ''} detected
      </div>
      {findings.map((f, i) => <FindingRow key={i} finding={f} onHighlightLine={onHighlightLine} showType />)}
    </div>
  )
}

export function SecurityTab({ findings, onHighlightLine }) {
  if (!findings?.length) return <Empty label="security" />
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 2 }}>
        {findings.length} issue{findings.length !== 1 ? 's' : ''} detected
      </div>
      {findings.map((f, i) => <FindingRow key={i} finding={f} onHighlightLine={onHighlightLine} showType={false} />)}
    </div>
  )
}

export default PerformanceTab
