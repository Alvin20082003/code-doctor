import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'

const COMPLEXITY_COLORS = {
  'O(1)':        'var(--success)',
  'O(log n)':    'var(--success)',
  'O(n)':        '#8A93A6',
  'O(n+m)':      '#8A93A6',
  'O(n log n)':  'var(--sev-medium)',
  'O(n*m)':      'var(--sev-high)',
  'O(n^2)':      'var(--sev-high)',
  'O(n^3)':      'var(--sev-high)',
  'O(2^n)':      'var(--sev-critical)',
  'unknown':     '#555E72',
}

function BigOBadge({ label, sublabel }) {
  const raw = label || '?'
  return (
    <div style={{
      display: 'inline-flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '8px 16px',
      borderRadius: 6,
      background: 'var(--elevated)',
      border: '1px solid var(--border-md)',
      minWidth: 90,
    }}>
      <span style={{
        fontSize: 16,
        fontWeight: 700,
        fontFamily: 'JetBrains Mono, monospace',
        color: COMPLEXITY_COLORS[raw] ?? '#8A93A6',
      }}>
        {raw}
      </span>
      {sublabel && <span style={{ fontSize: 10, color: 'var(--dim)', marginTop: 3 }}>{sublabel}</span>}
    </div>
  )
}

function EvidenceList({ evidence = [], onHighlightLine }) {
  if (!evidence.length) return null
  return (
    <ul style={{ listStyle: 'none', margin: '10px 0 0', display: 'flex', flexDirection: 'column', gap: 5 }}>
      {evidence.map((e, i) => (
        <li key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 11 }}>
          {e.line != null && (
            <button
              onClick={() => onHighlightLine && onHighlightLine(e.line)}
              style={{
                padding: '1px 6px',
                borderRadius: 3,
                border: '1px solid var(--border)',
                background: 'var(--bg)',
                fontSize: 10,
                fontFamily: 'JetBrains Mono, monospace',
                color: 'var(--accent)',
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >L{e.line}</button>
          )}
          <span style={{ color: 'var(--muted)', lineHeight: 1.5 }}>{e.reason}</span>
        </li>
      ))}
    </ul>
  )
}

function fmtOps(v) {
  if (v >= 1e12) return `${(v/1e12).toFixed(1)}T`
  if (v >= 1e9)  return `${(v/1e9).toFixed(1)}B`
  if (v >= 1e6)  return `${(v/1e6).toFixed(1)}M`
  if (v >= 1e3)  return `${(v/1e3).toFixed(1)}k`
  return String(Math.round(v))
}

function GrowthChart({ curveBefore, curveAfter }) {
  if (!curveBefore || curveBefore.length === 0) return null

  const data = curveBefore.map((pt, i) => ({
    n: pt.n,
    Before: pt.ops,
    ...(curveAfter?.[i] ? { After: curveAfter[i].ops } : {}),
  }))

  const hasAfter = curveAfter && curveAfter.length > 0

  // Caption at n=100000
  const last = data[data.length - 1]
  const caption = last
    ? (hasAfter
        ? `At n = 100,000: ${fmtOps(last.Before)} ops → ${fmtOps(last.After ?? 0)} ops`
        : `At n = 100,000: ${fmtOps(last.Before)} operations`)
    : ''

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Growth curve
        </span>
        {caption && (
          <span style={{ fontSize: 10, color: 'var(--dim)', fontFamily: 'JetBrains Mono, monospace' }}>
            {caption}
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 4 }}>
          <defs>
            <linearGradient id="gbefore" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#F2555A" stopOpacity={0.25}/>
              <stop offset="95%" stopColor="#F2555A" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="gafter" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#2FBF71" stopOpacity={0.25}/>
              <stop offset="95%" stopColor="#2FBF71" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="2 4" stroke="var(--border)" />
          <XAxis
            dataKey="n"
            tick={{ fontSize: 10, fill: 'var(--dim)', fontFamily: 'JetBrains Mono' }}
            tickFormatter={v => v >= 1000 ? `${v/1000}k` : String(v)}
          />
          <YAxis
            scale="log"
            domain={['auto', 'auto']}
            tick={{ fontSize: 10, fill: 'var(--dim)', fontFamily: 'JetBrains Mono' }}
            tickFormatter={fmtOps}
            width={42}
          />
          <Tooltip
            formatter={(v, name) => [fmtOps(v) + ' ops', name]}
            labelFormatter={l => `n = ${Number(l).toLocaleString()}`}
            contentStyle={{
              fontSize: 11,
              background: 'var(--elevated)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--text)',
              fontFamily: 'JetBrains Mono, monospace',
            }}
          />
          {hasAfter && <Legend wrapperStyle={{ fontSize: 11, color: 'var(--muted)' }} />}
          <Area type="monotone" dataKey="Before" stroke="#F2555A" strokeWidth={2} fill="url(#gbefore)" dot={false} name="Before" />
          {hasAfter && (
            <Area type="monotone" dataKey="After" stroke="#2FBF71" strokeWidth={2} fill="url(#gafter)" dot={false} name="After" />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function ComplexityTab({ time, space, curveBefore, curveAfter, onHighlightLine }) {
  return (
    <div>
      <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 180px' }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
            Time Complexity
          </div>
          <BigOBadge label={time?.complexity} sublabel="measured" />
          <div style={{ fontSize: 11, color: 'var(--dim)', marginTop: 6 }}>
            Confidence: <span style={{ color: 'var(--muted)', fontWeight: 500 }}>{time?.confidence ?? '—'}</span>
          </div>
          <EvidenceList evidence={time?.evidence} onHighlightLine={onHighlightLine} />
        </div>
        <div style={{ flex: '1 1 180px' }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
            Space Complexity
          </div>
          <BigOBadge label={space?.complexity} sublabel="measured" />
          <div style={{ fontSize: 11, color: 'var(--dim)', marginTop: 6 }}>
            Confidence: <span style={{ color: 'var(--muted)', fontWeight: 500 }}>{space?.confidence ?? '—'}</span>
          </div>
          <EvidenceList evidence={space?.evidence} onHighlightLine={onHighlightLine} />
        </div>
      </div>
      <GrowthChart curveBefore={curveBefore} curveAfter={curveAfter} />
    </div>
  )
}
