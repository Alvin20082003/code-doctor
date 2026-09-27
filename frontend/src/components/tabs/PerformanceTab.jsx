const SEVERITY_COLORS = {
  high:   { bg: '#FCE8E6', border: '#F5C6C2', text: '#C5221F', label: 'High' },
  medium: { bg: '#FEF7E0', border: '#FAE48D', text: '#B06000', label: 'Medium' },
  low:    { bg: '#E6F4EA', border: '#CEEAD6', text: '#137333', label: 'Low' },
}

const TYPE_LABELS = {
  n_plus_one:           'N+1 Query',
  list_membership_in_loop: 'O(n) Membership',
  repeated_call_in_loop:   'Repeated Call',
}

function SeverityPill({ severity }) {
  const c = SEVERITY_COLORS[severity] || SEVERITY_COLORS.medium
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px 9px',
      borderRadius: 12,
      background: c.bg,
      border: `1px solid ${c.border}`,
      color: c.text,
      fontSize: 11,
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
    }}>
      {c.label}
    </span>
  )
}

function FindingCard({ finding, onHighlightLine, typeKey }) {
  const typeLabel = typeKey ? (TYPE_LABELS[finding.type] || finding.type?.replace(/_/g, ' ')) : null
  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: 10,
      padding: '14px 16px',
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <SeverityPill severity={finding.severity} />
        {typeLabel && (
          <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 500 }}>
            {typeLabel}
          </span>
        )}
        {finding.line != null && finding.line > 0 && (
          <button
            onClick={() => onHighlightLine && onHighlightLine(finding.line)}
            style={{
              marginLeft: 'auto',
              padding: '2px 9px',
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: '#F8F9FA',
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              color: 'var(--accent)',
              cursor: 'pointer',
            }}
          >
            Line {finding.line}
          </button>
        )}
      </div>
      <p style={{ margin: 0, fontSize: 13, color: 'var(--text)', lineHeight: 1.5 }}>
        {finding.evidence}
      </p>
      {finding.fix && (
        <div style={{
          padding: '8px 12px',
          borderRadius: 8,
          background: '#F0F7FF',
          border: '1px solid #C5D9F7',
          fontSize: 12,
          color: '#1A5CA8',
          lineHeight: 1.5,
        }}>
          <strong>Fix: </strong>{finding.fix}
        </div>
      )}
    </div>
  )
}

export default function PerformanceTab({ findings, onHighlightLine }) {
  if (!findings || findings.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '40px 0',
        color: 'var(--green)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 10,
      }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" fill="#E6F4EA"/>
          <path d="M7 12.5l3.5 3.5 6.5-7" stroke="#1E8E3E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span style={{ fontSize: 14, fontWeight: 500 }}>No performance issues found</span>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 4 }}>
        {findings.length} issue{findings.length !== 1 ? 's' : ''} detected
      </div>
      {findings.map((f, i) => (
        <FindingCard key={i} finding={f} onHighlightLine={onHighlightLine} typeKey />
      ))}
    </div>
  )
}
