const AGENT_META = {
  time_complexity:  { label: 'Time Complexity',  icon: '⏱' },
  space_complexity: { label: 'Space Complexity', icon: '🗄' },
  performance:      { label: 'Performance',       icon: '⚡' },
  security:         { label: 'Security',          icon: '🔒' },
  optimizer:        { label: 'Optimizer',         icon: '✨' },
}

const ORDER = ['time_complexity', 'space_complexity', 'performance', 'security', 'optimizer']

export default function AnalysisScreen({ agents }) {
  return (
    <div className="fade-in" style={{ marginTop: 32 }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Running analysis
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        {ORDER.map(key => (
          <AgentCard key={key} name={key} state={agents[key]} />
        ))}
      </div>
    </div>
  )
}

function AgentCard({ name, state }) {
  const meta = AGENT_META[name]
  const { status, message } = state

  const colors = {
    waiting: { bg: '#F8F9FA', border: '#E8EAED', dot: '#BDC1C6', text: '#5F6368' },
    running: { bg: '#EAF1FB', border: '#C5D9F7', dot: '#1A73E8', text: '#1A73E8' },
    done:    { bg: '#E6F4EA', border: '#CEEAD6', dot: '#1E8E3E', text: '#1E8E3E' },
    failed:  { bg: '#FEF7E0', border: '#FDE293', dot: '#F9AB00', text: '#E37400' },
  }
  const c = colors[status] || colors.waiting

  return (
    <div
      className={status === 'done' || status === 'running' ? 'fade-in' : ''}
      style={{
        background: c.bg,
        border: `1px solid ${c.border}`,
        borderRadius: 12,
        padding: '14px 12px',
        textAlign: 'center',
        transition: 'all 0.2s',
      }}
    >
      <div style={{ fontSize: 20, marginBottom: 8 }}>{meta.icon}</div>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>
        {meta.label}
      </div>
      <StatusIndicator status={status} color={c.dot} />
      {status === 'failed' && message && (
        <div style={{ fontSize: 10, color: '#E37400', marginTop: 6, lineHeight: 1.4 }}>
          {message.slice(0, 60)}{message.length > 60 ? '…' : ''}
        </div>
      )}
    </div>
  )
}

function StatusIndicator({ status, color }) {
  if (status === 'done') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{ margin: '0 auto', display: 'block' }}>
        <circle cx="12" cy="12" r="10" fill="#1E8E3E"/>
        <path d="M7 12.5l3.5 3.5 6.5-7" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    )
  }
  if (status === 'failed') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{ margin: '0 auto', display: 'block' }}>
        <circle cx="12" cy="12" r="10" fill="#F9AB00"/>
        <path d="M12 7v5M12 16v1" stroke="#fff" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    )
  }
  if (status === 'running') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', gap: 4 }}>
        {[0, 1, 2].map(i => (
          <div
            key={i}
            style={{
              width: 6, height: 6,
              borderRadius: '50%',
              background: color,
              animation: `pulse-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
        <style>{`
          @keyframes pulse-dot {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
            40% { transform: scale(1); opacity: 1; }
          }
        `}</style>
      </div>
    )
  }
  // waiting
  return (
    <div style={{
      width: 8, height: 8,
      borderRadius: '50%',
      background: color,
      margin: '0 auto',
    }} />
  )
}
