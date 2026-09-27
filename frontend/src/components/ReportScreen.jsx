import { useState } from 'react'
import ComplexityTab from './tabs/ComplexityTab.jsx'
import PerformanceTab from './tabs/PerformanceTab.jsx'
import SecurityTab from './tabs/SecurityTab.jsx'
import OptimizerTab from './tabs/OptimizerTab.jsx'

const TABS = [
  { id: 'complexity',  label: 'Complexity' },
  { id: 'performance', label: 'Performance' },
  { id: 'security',    label: 'Security' },
  { id: 'optimized',   label: 'Optimized Code' },
]

function ScoreRing({ score }) {
  const r = 54
  const circ = 2 * Math.PI * r
  const filled = (score / 100) * circ
  const color = score >= 70 ? '#1E8E3E' : score >= 40 ? '#F9AB00' : '#D93025'

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <svg width="132" height="132" viewBox="0 0 132 132">
        {/* track */}
        <circle cx="66" cy="66" r={r} fill="none" stroke="#E8EAED" strokeWidth="10"/>
        {/* progress */}
        <circle
          cx="66" cy="66" r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circ - filled}`}
          strokeDashoffset={circ * 0.25}
          style={{ transition: 'stroke-dasharray 0.8s ease' }}
        />
        <text x="66" y="62" textAnchor="middle" fontSize="28" fontWeight="700" fill={color} fontFamily="Inter, sans-serif">
          {score}
        </text>
        <text x="66" y="80" textAnchor="middle" fontSize="11" fill="#5F6368" fontFamily="Inter, sans-serif">
          / 100
        </text>
      </svg>
      <span style={{ fontSize: 13, fontWeight: 600, color: '#5F6368', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
        Scale Score
      </span>
    </div>
  )
}

export default function ReportScreen({ report, originalCode, onHighlightLine }) {
  const [activeTab, setActiveTab] = useState('complexity')

  const { score, score_after, time, space, performance, security, optimizer, curve_before, curve_after } = report

  return (
    <div className="fade-in" style={{ marginTop: 32 }}>
      {/* Score + header row */}
      <div style={{
        background: '#fff',
        borderRadius: 16,
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        padding: '28px 32px',
        display: 'flex',
        alignItems: 'center',
        gap: 40,
        marginBottom: 24,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: score_after != null ? 20 : 0 }}>
          <ScoreRing score={score ?? 0} />
          {score_after != null && (
            <>
              <div style={{ fontSize: 22, color: 'var(--muted)', fontWeight: 300 }}>→</div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                <ScoreRing score={score_after} />
                <span style={{ fontSize: 11, color: 'var(--muted)', marginTop: -4 }}>after opt.</span>
              </div>
            </>
          )}
        </div>
        <div>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, marginBottom: 6 }}>Analysis Complete</h2>
          <p style={{ margin: 0, fontSize: 14, color: 'var(--muted)' }}>
            {score >= 70
              ? 'Your code scales well. A few opportunities for improvement below.'
              : score >= 40
              ? 'Moderate scale issues detected. Review the findings below.'
              : 'Significant scale concerns found. See recommendations below.'}
          </p>
          {score_after != null && (
            <p style={{ margin: '6px 0 0', fontSize: 13, color: score_after > score ? 'var(--green)' : '#B06000', fontWeight: 500 }}>
              Score improved {score} → {score_after} after optimization
            </p>
          )}
        </div>
      </div>

      {/* Tabs container */}
      <div style={{
        background: '#fff',
        borderRadius: 16,
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        overflow: 'hidden',
      }}>
        {/* Tab bar */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border)',
          padding: '0 24px',
        }}>
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                padding: '14px 16px',
                border: 'none',
                background: 'none',
                fontSize: 14,
                fontWeight: activeTab === t.id ? 600 : 400,
                color: activeTab === t.id ? 'var(--accent)' : 'var(--muted)',
                cursor: 'pointer',
                borderBottom: activeTab === t.id ? '2px solid var(--accent)' : '2px solid transparent',
                marginBottom: -1,
                transition: 'color 0.15s',
                fontFamily: 'inherit',
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ padding: '24px' }}>
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
