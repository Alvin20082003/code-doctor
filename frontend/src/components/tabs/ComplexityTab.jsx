import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'

const COMPLEXITY_COLORS = {
  'O(1)':       '#1E8E3E',
  'O(log n)':   '#1E8E3E',
  'O(n)':       '#F9AB00',
  'O(n log n)': '#F9AB00',
  'O(n^2)':     '#D93025',
  'O(n^3)':     '#D93025',
  'O(2^n)':     '#D93025',
  'unknown':    '#9AA0A6',
}

function BigOBadge({ label, sublabel }) {
  const color = COMPLEXITY_COLORS[label] || '#9AA0A6'
  return (
    <div style={{
      display: 'inline-flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '10px 20px',
      borderRadius: 10,
      background: color + '18',
      border: `1.5px solid ${color}40`,
      minWidth: 100,
    }}>
      <span style={{ fontSize: 18, fontWeight: 700, color, fontFamily: 'JetBrains Mono, monospace' }}>
        {label || '?'}
      </span>
      {sublabel && (
        <span style={{ fontSize: 11, color: 'var(--muted)', marginTop: 3 }}>{sublabel}</span>
      )}
    </div>
  )
}

function EvidenceList({ evidence = [], onHighlightLine }) {
  if (!evidence.length) return null
  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: '12px 0 0', display: 'flex', flexDirection: 'column', gap: 6 }}>
      {evidence.map((e, i) => (
        <li key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13 }}>
          {e.line != null && (
            <button
              onClick={() => onHighlightLine && onHighlightLine(e.line)}
              style={{
                padding: '1px 7px',
                borderRadius: 6,
                border: '1px solid var(--border)',
                background: '#F8F9FA',
                fontSize: 11,
                fontFamily: 'JetBrains Mono, monospace',
                color: 'var(--accent)',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
            >
              L{e.line}
            </button>
          )}
          <span style={{ color: 'var(--muted)', lineHeight: 1.5 }}>{e.reason}</span>
        </li>
      ))}
    </ul>
  )
}

function GrowthChart({ curveBefore, curveAfter }) {
  if (!curveBefore || curveBefore.length === 0) return null

  const data = curveBefore.map((pt, i) => ({
    n: pt.n,
    Before: pt.ops,
    ...(curveAfter && curveAfter[i] ? { After: curveAfter[i].ops } : {}),
  }))

  return (
    <div style={{ marginTop: 24 }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: 'var(--text)' }}>
        Growth curve{curveAfter && curveAfter.length > 0 ? ' (before vs. after optimization)' : ''}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8EAED" />
          <XAxis
            dataKey="n"
            tick={{ fontSize: 11, fill: '#9AA0A6' }}
            label={{ value: 'Input size (n)', position: 'insideBottom', offset: -2, fontSize: 11, fill: '#9AA0A6' }}
          />
          <YAxis
            scale="log"
            domain={['auto', 'auto']}
            tick={{ fontSize: 11, fill: '#9AA0A6' }}
            tickFormatter={v => v >= 1e9 ? `${(v/1e9).toFixed(0)}B` : v >= 1e6 ? `${(v/1e6).toFixed(0)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}k` : String(v)}
            label={{ value: 'Operations (log)', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#9AA0A6' }}
            allowDataKey={false}
          />
          <Tooltip
            formatter={(v) => v.toLocaleString()}
            labelFormatter={(l) => `n = ${l}`}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid var(--border)' }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey="Before" stroke="#D93025" strokeWidth={2} dot={false} name="Before" />
          {curveAfter && curveAfter.length > 0 && (
            <Line type="monotone" dataKey="After" stroke="#1E8E3E" strokeWidth={2} dot={false} name="After" />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function ComplexityTab({ time, space, curveBefore, curveAfter, onHighlightLine }) {
  return (
    <div>
      <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
        {/* Time */}
        <div style={{ flex: '1 1 220px' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)', marginBottom: 10 }}>
            TIME COMPLEXITY
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <BigOBadge label={time?.complexity} sublabel="before" />
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
            Confidence: <strong>{time?.confidence || '—'}</strong>
          </div>
          <EvidenceList evidence={time?.evidence} onHighlightLine={onHighlightLine} />
        </div>

        {/* Space */}
        <div style={{ flex: '1 1 220px' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--muted)', marginBottom: 10 }}>
            SPACE COMPLEXITY
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <BigOBadge label={space?.complexity} sublabel="before" />
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
            Confidence: <strong>{space?.confidence || '—'}</strong>
          </div>
          <EvidenceList evidence={space?.evidence} onHighlightLine={onHighlightLine} />
        </div>
      </div>

      <GrowthChart curveBefore={curveBefore} curveAfter={curveAfter} />
    </div>
  )
}
