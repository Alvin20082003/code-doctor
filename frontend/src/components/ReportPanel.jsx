import { useState, useEffect } from 'react'
import ComplexityTab from './tabs/ComplexityTab.jsx'
import PerformanceTab from './tabs/PerformanceTab.jsx'
import SecurityTab from './tabs/SecurityTab.jsx'
import OptimizerTab from './tabs/OptimizerTab.jsx'
import OverviewTab from './tabs/OverviewTab.jsx'

const TABS = [
  { id: 'overview',    label: 'Overview' },
  { id: 'complexity',  label: 'Complexity' },
  { id: 'performance', label: 'Performance' },
  { id: 'security',    label: 'Security' },
  { id: 'optimized',   label: 'Optimized Code' },
]

// ── Score Ring ──────────────────────────────────────────────────────────────
function ScoreRing({ score, size = 88 }) {
  const r = size * 0.38
  const circ = 2 * Math.PI * r
  const filled = (Math.max(0, Math.min(100, score)) / 100) * circ
  const color = score >= 70 ? 'var(--success)' : score >= 40 ? 'var(--sev-medium)' : 'var(--sev-high)'

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ animation: 'count-up 0.4s ease' }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border-md)" strokeWidth={size * 0.085} />
      <circle
        cx={size/2} cy={size/2} r={r}
        fill="none"
        stroke={color}
        strokeWidth={size * 0.085}
        strokeLinecap="round"
        strokeDasharray={`${filled} ${circ - filled}`}
        strokeDashoffset={circ * 0.25}
        style={{ transition: 'stroke-dasharray 0.8s ease' }}
      />
      <text x={size/2} y={size/2 - 4} textAnchor="middle"
        fontSize={size * 0.23} fontWeight="700" fill={color}
        fontFamily="JetBrains Mono, monospace">
        {score}
      </text>
      <text x={size/2} y={size/2 + size * 0.14} textAnchor="middle"
        fontSize={size * 0.1} fill="var(--dim)"
        fontFamily="Inter, sans-serif">
        /100
      </text>
    </svg>
  )
}

// ── Stat tile ───────────────────────────────────────────────────────────────
function StatTile({ label, value, sub }) {
  return (
    <div style={{
      flex: 1,
      padding: '10px 14px',
      background: 'var(--elevated)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      minWidth: 0,
    }}>
      <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 600, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 10, color: 'var(--dim)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

// ── Main ────────────────────────────────────────────────────────────────────
export default function ReportPanel({ report, originalCode, onHighlightLine }) {
  const [activeTab, setActiveTab] = useState('overview')

  const {
    score, score_after, time, space, performance, security,
    optimizer, curve_before, curve_after, speedup, total_ms,
    capped_reason,
  } = report

  // Bug #3: only show after ring when improvement is real (Y > X)
  const showAfterScore = score_after != null && score_after > score

  const timeLabel = time?.complexity ?? '?'
  const afterTimeLabel = optimizer?.after?.time
  const timeStr = afterTimeLabel && afterTimeLabel !== timeLabel
    ? `${timeLabel} → ${afterTimeLabel}`
    : timeLabel

  const totalIssues = (performance?.length ?? 0) + (security?.length ?? 0)
  const afterIssues = (optimizer?.after_findings?.performance?.length ?? 0)
    + (optimizer?.after_findings?.security?.length ?? 0)
  const issuesStr = (optimizer?.status === 'verified' || optimizer?.status === 'rejected')
    ? `${totalIssues} → ${afterIssues}`
    : String(totalIssues)

  const speedupStr = speedup != null && speedup > 1
    ? `${speedup.toLocaleString()}×`
    : '—'

  return (
    <div className="anim-fade-slide" style={{ padding: '0 0 40px' }}>
      {/* ── Summary header ──────────────────────────────────── */}
      <div style={{
        padding: '16px 20px',
        background: 'var(--surface)',
        borderBottom: '1px solid var(--border)',
      }}>
        {/* Rings + stat tiles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14 }}>
          {/* Rings */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
            <div style={{ textAlign: 'center' }}>
              <ScoreRing score={score ?? 0} />
              <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 4 }}>Before</div>
              {capped_reason && (
                <div style={{
                  fontSize: 9,
                  color: 'var(--sev-high)',
                  marginTop: 3,
                  maxWidth: 90,
                  lineHeight: 1.3,
                  fontFamily: 'Inter, sans-serif',
                }}>
                  {capped_reason}
                </div>
              )}
            </div>
            {showAfterScore && (
              <>
                <span style={{ color: 'var(--border-md)', fontSize: 16 }}>→</span>
                <div style={{ textAlign: 'center' }} className="anim-fade">
                  <ScoreRing score={score_after} />
                  <div style={{ fontSize: 10, color: 'var(--success)', marginTop: 4 }}>After opt.</div>
                </div>
              </>
            )}
          </div>

          {/* Stat tiles */}
          <div style={{ flex: 1, display: 'flex', gap: 8, minWidth: 0 }}>
            <StatTile label="Time" value={timeStr} />
            <StatTile label="Issues" value={issuesStr} />
            <StatTile label="Speedup @ 100k" value={speedupStr} sub="ops ratio" />
          </div>
        </div>

        {total_ms != null && (
          <div style={{ fontSize: 11, color: 'var(--dim)', fontFamily: 'JetBrains Mono, monospace' }}>
            Analysis completed in {total_ms}ms
          </div>
        )}
      </div>

      {/* ── Tabs ────────────────────────────────────────────── */}
      <div>
        {/* Tab bar */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border)',
          padding: '0 20px',
          background: 'var(--surface)',
          overflowX: 'auto',
        }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                padding: '10px 14px',
                border: 'none',
                background: 'none',
                fontSize: 12,
                fontWeight: activeTab === t.id ? 600 : 400,
                color: activeTab === t.id ? 'var(--accent)' : 'var(--muted)',
                cursor: 'pointer',
                borderBottom: activeTab === t.id ? '2px solid var(--accent)' : '2px solid transparent',
                marginBottom: -1,
                transition: 'color 0.12s',
                fontFamily: 'inherit',
                whiteSpace: 'nowrap',
              }}
            >
              {t.label}
              {t.id === 'performance' && performance?.length > 0 && (
                <span style={{ marginLeft: 5, fontSize: 10, background: 'var(--sev-medium)', color: '#fff', borderRadius: 8, padding: '1px 5px', fontWeight: 700 }}>
                  {performance.length}
                </span>
              )}
              {t.id === 'security' && security?.length > 0 && (
                <span style={{ marginLeft: 5, fontSize: 10, background: 'var(--sev-high)', color: '#fff', borderRadius: 8, padding: '1px 5px', fontWeight: 700 }}>
                  {security.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ padding: '20px' }}>
          {activeTab === 'overview' && (
            <OverviewTab
              performance={performance}
              security={security}
              time={time}
              space={space}
              onHighlightLine={onHighlightLine}
            />
          )}
          {activeTab === 'complexity' && (
            <ComplexityTab
              time={time}
              space={space}
              curveBefore={curve_before}
              curveAfter={curve_after}
              onHighlightLine={onHighlightLine}
            />
          )}
          {activeTab === 'performance' && (
            <PerformanceTab findings={performance} onHighlightLine={onHighlightLine} />
          )}
          {activeTab === 'security' && (
            <SecurityTab findings={security} onHighlightLine={onHighlightLine} />
          )}
          {activeTab === 'optimized' && (
            <OptimizerTab
              optimizer={optimizer}
              originalCode={originalCode}
            />
          )}
        </div>
      </div>
    </div>
  )
}
