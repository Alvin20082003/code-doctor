import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import PipelinePanel from './PipelinePanel.jsx'
import ReportPanel from './ReportPanel.jsx'

const EDITOR_OPTIONS = {
  minimap: { enabled: false },
  fontSize: 13,
  lineHeight: 21,
  fontFamily: "'JetBrains Mono', monospace",
  scrollBeyondLastLine: false,
  padding: { top: 12, bottom: 12 },
  wordWrap: 'on',
  renderLineHighlight: 'line',
  overviewRulerLanes: 0,
  readOnly: true,
  glyphMargin: true,
  folding: false,
}

export default function Workspace({ code, agents, report, phase, elapsedMs, onHighlightLine, editorRef }) {
  const decorationsRef = useRef([])
  const monacoRef = useRef(null)
  const localEditorRef = useRef(null)

  function handleEditorMount(editor, monaco) {
    localEditorRef.current = editor
    monacoRef.current = monaco
    if (editorRef) editorRef.current = editor
    applyDecorations(editor, monaco)
  }

  // Gather all findings from the report for line decorations
  const allFindings = report
    ? [...(report.performance || []), ...(report.security || [])]
    : []

  function applyDecorations(editor, monaco) {
    if (!editor || !monaco || !report) return

    const newDecorations = allFindings
      .filter(f => f.line && f.line > 0)
      .map(f => {
        const isHigh = f.severity === 'high' || f.severity === 'critical'
        const lineColor = isHigh ? 'rgba(242,85,90,0.08)' : 'rgba(245,165,36,0.07)'
        const glyphColor = isHigh ? '#F2555A' : '#F5A524'
        return {
          range: new monaco.Range(f.line, 1, f.line, 1),
          options: {
            isWholeLine: true,
            className: '',
            // Inline style: subtle full-line background
            lineNumberClassName: '',
            glyphMarginClassName: '',
            // Use minimap color to indicate severity
            minimap: { color: glyphColor, darkColor: glyphColor },
            overviewRuler: { color: glyphColor, darkColor: glyphColor, position: 1 },
            // Hover message
            hoverMessage: {
              value: `**${(f.severity || '').toUpperCase()}**: ${f.evidence || f.category || ''}`,
            },
          },
        }
      })

    const ids = editor.deltaDecorations(decorationsRef.current, newDecorations)
    decorationsRef.current = ids
  }

  // Re-apply when report arrives
  useEffect(() => {
    if (localEditorRef.current && monacoRef.current) {
      applyDecorations(localEditorRef.current, monacoRef.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report])

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      overflow: 'hidden',
      // Responsive: stack below 1100px
    }}>
      {/* ── LEFT: editor (55%) ──────────────────────────────── */}
      <div style={{
        flex: '0 0 55%',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid var(--border)',
        overflow: 'hidden',
      }}>
        {/* Editor header */}
        <div style={{
          height: 36,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          background: 'var(--elevated)',
          borderBottom: '1px solid var(--border)',
          gap: 12,
        }}>
          <span style={{
            fontSize: 12,
            fontFamily: 'JetBrains Mono, monospace',
            color: 'var(--text)',
          }}>
            main.py
          </span>
          <span style={{
            fontSize: 11,
            color: 'var(--accent)',
            background: 'var(--accent-dim)',
            border: '1px solid var(--accent-border)',
            padding: '1px 7px',
            borderRadius: 4,
            fontWeight: 500,
          }}>Python</span>
          {allFindings.length > 0 && (
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--muted)' }}>
              <span style={{ color: 'var(--sev-high)', fontWeight: 600 }}>
                {allFindings.filter(f => f.severity === 'high' || f.severity === 'critical').length}
              </span>
              {' high · '}
              <span style={{ color: 'var(--sev-medium)', fontWeight: 600 }}>
                {allFindings.filter(f => f.severity === 'medium').length}
              </span>
              {' medium · '}
              {allFindings.length} total
            </span>
          )}
        </div>

        <Editor
          height="100%"
          language="python"
          value={code}
          onMount={handleEditorMount}
          options={EDITOR_OPTIONS}
          theme="vs-dark"
        />
      </div>

      {/* ── RIGHT: report panel (45%) ────────────────────────── */}
      <div style={{
        flex: '0 0 45%',
        minWidth: 0,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--bg)',
      }}>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <PipelinePanel
            agents={agents}
            elapsedMs={elapsedMs}
            phase={phase}
            optimizerStatus={report?.optimizer?.status ?? null}
          />
          {phase === 'report' && report && (
            <ReportPanel
              report={report}
              originalCode={code}
              onHighlightLine={onHighlightLine}
            />
          )}
        </div>
      </div>
    </div>
  )
}
