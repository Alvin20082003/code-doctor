// Landing page detail sections: what Code Doctor checks, what code it supports,
// how the pipeline works, and what makes it different.

const mono = "'JetBrains Mono', Consolas, monospace"

const CHECKS = [
  {
    icon: '⏱', title: 'Time complexity', tag: 'AST · deterministic',
    what: 'Computes Big-O from the code structure: nested loops, recursion, sorting, and hidden loops inside built-ins.',
    ex: 'for u in users: for o in orders  →  O(n×m)',
  },
  {
    icon: '🧠', title: 'Space complexity', tag: 'AST · deterministic',
    what: 'Tracks extra memory: lists/dicts built inside loops, 2-D structures, and recursion stack depth.',
    ex: 'result.append() inside nested loop  →  O(n²)',
  },
  {
    icon: '📈', title: 'Scalability simulation', tag: 'n = 10 → 100,000',
    what: 'Projects operations as input grows and shows the speedup of the fix at 100k records.',
    ex: 'O(n×m) → O(n+m)  =  100,000× fewer ops',
  },
  {
    icon: '🗄', title: 'N+1 & DB inefficiency', tag: 'Performance agent',
    what: 'Finds database or HTTP calls inside loops, list lookups inside loops, and repeated identical calls.',
    ex: 'db.query(...) inside for-loop  →  N+1',
  },
  {
    icon: '🔒', title: 'Security agent', tag: 'Bandit + custom AST rules',
    what: 'SQL injection from f-strings, eval/exec, hardcoded API keys and passwords. Critical issues cap the score at 40.',
    ex: 'db.execute(f"... {username}")  →  SQL injection',
  },
  {
    icon: '✨', title: 'IBM Granite + verifier', tag: 'AI suggests · analyzer proves',
    what: 'Granite 3.3 rewrites the code with targeted hints. Our analyzer re-checks it; unproven claims are rejected.',
    ex: 'Verified: O(n×m) → O(n+m), outputs identical ✓',
  },
]

const SUPPORTED = [
  'Python 3 backend functions and modules (up to 20,000 characters)',
  'Loops over collections: users, orders, records, rows, items',
  'ORM / DB calls: db.query, execute, filter, find, get, all, first',
  'HTTP calls in loops: requests.get / requests.post',
  'SQL built as strings, eval / exec, hardcoded secrets',
  'Recursion, sorting, sum / max / min / sorted / in-list lookups',
]
const NOT_SUPPORTED = [
  'Other languages yet (JS/TS planned via Tree-sitter)',
  'Whole repositories: paste one file or function at a time',
  'General logic bugs (e.g. wrong formula): use tests for those',
  'Runtime profiling: Big-O is estimated statically, with a confidence level',
]

const STEPS = [
  ['1', 'Parse', 'Code → Python AST'],
  ['2', '4 agents in parallel', 'Time · Space · Performance · Security'],
  ['3', 'IBM Granite', 'Optimized rewrite + explanation'],
  ['4', 'Verify', 'Re-analyze + behavior test'],
  ['5', 'Report', 'Scale Score · before→after · diff'],
]

const DIFF = [
  ['Computed, not guessed', 'Big-O comes from the AST, not from an LLM prompt. Copilot-style tools only reason about complexity when asked.'],
  ['Before → after proof', 'Every fix shows old vs new complexity, both computed by the same analyzer, plus a growth chart.'],
  ['AI output is verified', 'In testing a small model claimed O(n+m) for code that was still O(n×m). Code Doctor rejects that.'],
  ['Private by design', 'IBM Granite runs locally. Your code never leaves the machine — built for banks, healthcare and government.'],
]

function Section({ title, sub, children }) {
  return (
    <section style={{ width: '100%', maxWidth: 1040, marginTop: 64 }}>
      <div style={{ marginBottom: 18 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: 'var(--text)', margin: 0, letterSpacing: '-0.3px' }}>{title}</h2>
        {sub && <p style={{ fontSize: 13, color: 'var(--muted)', margin: '6px 0 0' }}>{sub}</p>}
      </div>
      {children}
    </section>
  )
}

const card = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 16,
}

export default function LandingInfo() {
  return (
    <>
      <Section title="What Code Doctor checks" sub="Six analyses on every run. Numbers are computed from your code, not guessed.">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
          {CHECKS.map(c => (
            <div key={c.title} style={card}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 16 }}>{c.icon}</span>
                <span style={{ fontWeight: 600, color: 'var(--text)', fontSize: 14 }}>{c.title}</span>
              </div>
              <div style={{ fontSize: 10, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>{c.tag}</div>
              <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.55, margin: '0 0 10px' }}>{c.what}</p>
              <div style={{ fontFamily: mono, fontSize: 11.5, color: 'var(--text)', background: 'var(--elevated)', border: '1px solid var(--border)', borderRadius: 5, padding: '6px 8px' }}>{c.ex}</div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="What code can I paste?" sub="Code Doctor is built for Python backend code — API endpoints, services, data-processing functions.">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 12 }}>
          <div style={{ ...card, borderColor: 'var(--success-border, #1f5e3d)' }}>
            <div style={{ fontWeight: 600, color: 'var(--success)', fontSize: 13, marginBottom: 10 }}>✓ Supported</div>
            {SUPPORTED.map(s => <div key={s} style={{ fontSize: 13, color: 'var(--text)', padding: '4px 0', lineHeight: 1.5 }}>• {s}</div>)}
          </div>
          <div style={card}>
            <div style={{ fontWeight: 600, color: 'var(--muted)', fontSize: 13, marginBottom: 10 }}>○ Not in scope (yet)</div>
            {NOT_SUPPORTED.map(s => <div key={s} style={{ fontSize: 13, color: 'var(--muted)', padding: '4px 0', lineHeight: 1.5 }}>• {s}</div>)}
          </div>
        </div>
      </Section>

      <Section title="How it works" sub="A live pipeline — each stage streams its result to the UI as soon as it finishes.">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
          {STEPS.map(([n, t, d]) => (
            <div key={n} style={card}>
              <div style={{ fontFamily: mono, fontSize: 12, color: 'var(--accent)', marginBottom: 6 }}>0{n}</div>
              <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: 13, marginBottom: 4 }}>{t}</div>
              <div style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>{d}</div>
            </div>
          ))}
        </div>
        <div style={{ ...card, marginTop: 10, fontFamily: mono, fontSize: 11.5, color: 'var(--muted)', lineHeight: 1.7 }}>
          React + Monaco ⟶ FastAPI (SSE) ⟶ asyncio.gather[ time · space · perf · security ] ⟶ IBM Granite 3.3 (local) ⟶ AST verifier + sandboxed behavior test ⟶ Scale Score
        </div>
      </Section>

      <Section title="Why it's different" sub="Other AI tools help you write code. Code Doctor proves whether that code survives growth.">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
          {DIFF.map(([t, d]) => (
            <div key={t} style={card}>
              <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: 14, marginBottom: 6 }}>{t}</div>
              <div style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.55 }}>{d}</div>
            </div>
          ))}
        </div>
        <p style={{ textAlign: 'center', fontSize: 13, color: 'var(--muted)', marginTop: 28 }}>
          Built with <span style={{ color: 'var(--text)' }}>IBM Bob</span> · Powered by <span style={{ color: 'var(--text)' }}>IBM Granite</span> · Also available as an IBM Bob / VS Code extension
        </p>
      </Section>
    </>
  )
}
