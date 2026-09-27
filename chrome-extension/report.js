const API = 'http://127.0.0.1:8000';
const out = document.getElementById('out');
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const color = s => s >= 70 ? '#2FBF71' : s >= 40 ? '#F5A524' : '#F2555A';
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const { cd_code, cd_source } = await chrome.storage.local.get(['cd_code', 'cd_source']);
  document.getElementById('src').textContent = cd_source && cd_source !== 'popup' ? `Selected from: ${cd_source}` : 'Pasted code';
  if (!cd_code || !cd_code.trim()) { out.innerHTML = '<div class="card">No code selected.</div>'; return; }
  let job;
  try {
    const r = await fetch(`${API}/api/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: cd_code, language: 'python' }) });
    if (!r.ok) throw new Error(await r.text());
    job = await r.json();
  } catch (e) {
    out.innerHTML = `<div class="card" style="border-color:#F2555A"><b style="color:#F2555A">Code Doctor backend is offline.</b><br><span class="muted" style="text-transform:none">Start it: cd backend → python -m uvicorn main:app --reload</span><br><span class="muted" style="text-transform:none">${esc(e.message)}</span></div>`;
    return;
  }
  const t0 = Date.now(); let report;
  while (Date.now() - t0 < 240000) {
    await sleep(1500);
    const s = Math.round((Date.now() - t0) / 1000);
    document.getElementById('status').textContent = s < 3 ? 'Running time, space, performance and security analyzers…' : `IBM Granite is optimizing · our analyzer is verifying… ${s}s`;
    const r = await fetch(`${API}/api/jobs/${job.job_id}`).then(x => x.json()).catch(() => null);
    if (r && r.status !== 'running') { report = r; break; }
  }
  if (!report) { out.innerHTML = '<div class="card">Analysis timed out.</div>'; return; }
  render(cd_code, report);
})();

const MEANING = {
  'O(1)': ['Constant', 'Same speed no matter how much data you have. Ideal.', '#2FBF71'],
  'O(log n)': ['Logarithmic', 'Barely slows down as data grows (like binary search). Excellent.', '#2FBF71'],
  'O(n)': ['Linear', '10× more data = 10× more work. Scales well.', '#2FBF71'],
  'O(n+m)': ['Linear (two inputs)', 'Each collection is scanned once. Scales well.', '#2FBF71'],
  'O(n log n)': ['Linearithmic', 'Typical for sorting. Fine for most workloads.', '#F5A524'],
  'O(n^2)': ['Quadratic', '10× more data = 100× more work. Will slow down badly in production.', '#F2555A'],
  'O(n*m)': ['Quadratic (two inputs)', 'Every item is compared with every other item. 10k users × 10k orders = 100 million checks.', '#F2555A'],
  'O(n^3)': ['Cubic', '10× more data = 1,000× more work. Will not scale.', '#F2555A'],
  'O(2^n)': ['Exponential', 'Each extra item doubles the work. Unusable beyond small inputs.', '#F2555A'],
};
const MAX = { time: 35, space: 15, performance: 25, security: 25 };
const fmt = n => n >= 1e12 ? (n / 1e12).toFixed(1) + 'T' : n >= 1e9 ? (n / 1e9).toFixed(1) + 'B' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'K' : String(Math.round(n));

function hints(report) {
  const h = [];
  const t = (report.time || {}).complexity || '';
  if (/n\*m|n\^2/.test(t)) h.push(['Replace the nested loop with a dictionary lookup', 'Build a dict keyed by the join field (e.g. user_id) in ONE pass, then look items up in O(1). Turns O(n×m) into O(n+m).']);
  if (/2\^n/.test(t)) h.push(['Cache repeated recursive calls', 'Use functools.lru_cache or an iterative loop. Turns O(2ⁿ) into O(n).']);
  if (/n\^3/.test(t)) h.push(['Remove a loop level', 'Pre-index one collection in a dict or set so the innermost loop disappears.']);
  (report.performance || []).forEach(f => { if (f.type === 'n_plus_one') h.push(['Batch the database calls (N+1)', 'Fetch all rows in ONE query with WHERE id IN (...), then group them in a dict.']); });
  (report.security || []).forEach(f => {
    const c = (f.category || '').toLowerCase();
    if (c.includes('sql')) h.push(['Use parameterized queries', 'db.execute("... WHERE name = %s", (username,)) — never build SQL with f-strings.']);
    else if (c.includes('eval') || c.includes('b307')) h.push(['Remove eval()', 'Use json.loads or ast.literal_eval for data. eval runs any code an attacker sends.']);
    else if (c.includes('secret') || c.includes('b105')) h.push(['Move secrets to environment variables', 'API_KEY = os.environ["API_KEY"] — never commit keys in code.']);
  });
  const seen = new Set();
  return h.filter(([t]) => !seen.has(t) && seen.add(t));
}

function render(code, report) {
  const opt = report.optimizer || {};
  const before = (opt.before && opt.before.time) || (report.time || {}).complexity;
  const after = opt.after && opt.after.time;
  const findings = [...(report.performance || []), ...(report.security || [])];
  const high = findings.filter(f => (f.severity || '').toLowerCase() === 'high').length;
  const banner = {
    verified: ['#2FBF71', `✓ Verified by Code Doctor's analyzer: ${esc(before)} → ${esc(after)}`],
    rejected: ['#F5A524', `AI suggestion rejected — our analyzer found it is still ${esc(after)}`],
    not_needed: ['#2FBF71', '✓ Already scales well — no optimization needed'],
    failed: ['#8A93A6', 'IBM Granite optimization unavailable — deterministic analysis shown'],
  }[opt.status] || ['#8A93A6', esc(opt.status || '')];
  const b = opt.validation && opt.validation.behavior;
  const bt = b ? (b.tested ? (b.passed ? `Behavior test: ${b.cases || ''} generated cases — outputs identical ✓` : 'Behavior test: outputs differ ✗') : (b.reason || 'Static verification only')) : '';
  const tEv = ((report.time || {}).evidence || []);
  const sEv = ((report.space || {}).evidence || []);
  const m = MEANING[before] || ['Estimated', 'Complexity estimated from the code structure.', '#8A93A6'];
  const mA = after ? MEANING[after] : null;
  const cb = report.curve_before || [], ca = report.curve_after || [];
  const bd = report.breakdown || {};
  const verdict = report.score >= 70 ? ['Ready to scale', '#2FBF71'] : report.score >= 40 ? ['Needs work before scaling', '#F5A524'] : ['Will break at scale — fix before shipping', '#F2555A'];
  const hs = hints(report);

  out.innerHTML = `
<div class="card" style="border-color:${verdict[1]};display:flex;align-items:center;gap:14px">
  <div class="big mono" style="color:${verdict[1]};font-size:34px">${report.score}</div>
  <div><div style="font-weight:600;color:${verdict[1]}">${verdict[0]}</div>
  <div class="muted" style="text-transform:none">${findings.length} issue(s) · ${high} high severity · ${esc(before)} time · ${esc((report.space || {}).complexity)} space · analyzed in ${((report.total_ms || 0) / 1000).toFixed(1)}s</div></div>
</div>

<div class="row">
 <div class="card tile"><div class="muted">Scale Score</div><div class="big mono" style="color:${color(report.score)}">${report.score}${report.score_after && report.score_after > report.score ? ` <span style="color:#8A93A6">→</span> <span style="color:${color(report.score_after)}">${report.score_after}</span>` : ''}</div>${report.capped_reason ? `<div style="color:#F2555A;font-size:12px">${esc(report.capped_reason)}</div>` : ''}</div>
 <div class="card tile"><div class="muted">Time</div><div class="big mono">${esc(before)}${after && after !== before ? ` → <span style="color:#2FBF71">${esc(after)}</span>` : ''}</div></div>
 <div class="card tile"><div class="muted">Space</div><div class="big mono">${esc((report.space || {}).complexity)}${opt.after && opt.after.space && opt.after.space !== (report.space||{}).complexity ? ` → <span style="color:#2FBF71">${esc(opt.after.space)}</span>` : ''}</div></div>
 <div class="card tile"><div class="muted">Speedup @ 100k</div><div class="big mono">${report.speedup ? report.speedup.toLocaleString() + '×' : '—'}</div></div>
</div>

<div class="grid2">
 <div class="card"><div class="muted" style="margin-bottom:8px">What ${esc(before)} means</div>
  <div style="font-weight:600;color:${m[2]}">${m[0]}</div><div style="color:#C9CFDB;margin-top:4px;line-height:1.5">${m[1]}</div>
  ${mA && after !== before ? `<div style="margin-top:10px;font-weight:600;color:${mA[2]}">After fix: ${esc(after)} · ${mA[0]}</div><div style="color:#C9CFDB;margin-top:4px;line-height:1.5">${mA[1]}</div>` : ''}
 </div>
 <div class="card"><div class="muted" style="margin-bottom:8px">Score breakdown</div>
  ${Object.keys(MAX).map(k => { const v = bd[k] ?? 0, pct = Math.max(0, Math.min(100, v / MAX[k] * 100)); return `<div style="margin:7px 0"><div style="display:flex;justify-content:space-between;font-size:12px"><span style="text-transform:capitalize">${k}</span><span class="mono">${v}/${MAX[k]}</span></div><div style="height:6px;background:#181C25;border-radius:3px;margin-top:3px"><div style="height:6px;width:${pct}%;background:${color(pct)};border-radius:3px"></div></div></div>`; }).join('')}
 </div>
</div>

${cb.length ? `<div class="card"><div class="muted" style="margin-bottom:8px">Scalability simulation — estimated operations as data grows</div>
<table style="width:100%;border-collapse:collapse;font-size:13px" class="mono">
<tr style="color:#8A93A6;text-align:left"><th style="padding:6px 4px">Input size (n)</th><th>Current code</th>${ca.length ? '<th>Optimized</th><th>Saved</th>' : ''}</tr>
${cb.map((p, i) => { const a = ca[i]; return `<tr style="border-top:1px solid #232836"><td style="padding:6px 4px">${p.n.toLocaleString()}</td><td style="color:${/n\^2|n\*m|n\^3|2\^n/.test(before) ? '#F2555A' : '#E6E8EE'}">${fmt(p.ops)} ops</td>${a ? `<td style="color:#2FBF71">${fmt(a.ops)} ops</td><td>${a.ops ? Math.round(p.ops / a.ops).toLocaleString() + '×' : '—'}</td>` : ''}</tr>`; }).join('')}
</table></div>` : ''}

<div class="grid2">
 <div class="card"><div class="muted" style="margin-bottom:6px">Why this time complexity</div>${tEv.length ? tEv.map(e => `<div class="mono" style="font-size:12px;margin:4px 0"><span style="color:#8A93A6">L${e.line}</span> ${esc(e.reason)}</div>`).join('') : '<div class="muted" style="text-transform:none">No loops or recursion found.</div>'}</div>
 <div class="card"><div class="muted" style="margin-bottom:6px">Why this space complexity</div>${sEv.length ? sEv.map(e => `<div class="mono" style="font-size:12px;margin:4px 0"><span style="color:#8A93A6">L${e.line}</span> ${esc(e.reason)}</div>`).join('') : '<div class="muted" style="text-transform:none">No growing data structures found.</div>'}</div>
</div>

<div class="card"><div class="muted" style="margin-bottom:6px">Performance & security issues (${findings.length})</div>
${findings.length ? findings.map(f => `<div style="margin:10px 0;padding-bottom:10px;border-bottom:1px solid #232836"><span class="pill" style="${(f.severity||'').toLowerCase()==='high'?'background:#F2555A33;color:#F2555A':'background:#F5A52433;color:#F5A524'}">${esc((f.severity||'').toUpperCase())}</span> <b>${esc(f.category || f.type)}</b> <span class="mono muted">L${f.line}</span><div class="mono" style="color:#C9CFDB;font-size:12px;margin-top:4px">${esc(f.evidence)}</div>${f.fix ? `<div style="color:#2FBF71;font-size:12px;margin-top:3px">→ ${esc(f.fix)}</div>` : ''}</div>`).join('') : '<div style="color:#2FBF71">No N+1 queries, SQL injection, eval or hardcoded secrets found ✓</div>'}
</div>

${hs.length ? `<div class="card" style="border-color:#4F8CFF55"><div class="muted" style="margin-bottom:8px">Prescription — what to change</div>${hs.map(([t, d], i) => `<div style="margin:8px 0"><b><span class="mono" style="color:#4F8CFF">${i + 1}.</span> ${esc(t)}</b><div style="color:#C9CFDB;font-size:13px;margin-top:2px">${esc(d)}</div></div>`).join('')}</div>` : ''}

<div class="card" style="border-color:${banner[0]}"><b style="color:${banner[0]}">${banner[1]}</b>${bt ? `<div class="muted" style="text-transform:none;margin-top:4px">${esc(bt)}</div>` : ''}${opt.status === 'failed' && opt.note ? `<div class="muted" style="text-transform:none;margin-top:4px">${esc(opt.note)} · Check that the Ollama terminal is running, then analyze again.</div>` : ''}${opt.attempts ? `<div class="muted" style="text-transform:none;margin-top:4px">Granite attempts: ${opt.attempts}</div>` : ''}</div>
${opt.explanation ? `<div class="card"><div class="muted">Why (IBM Granite)</div><p style="margin:6px 0 0;line-height:1.55">${esc(opt.explanation)}</p></div>` : ''}
${opt.optimized_code ? `<div class="grid2"><div><div class="muted" style="margin-bottom:6px">Original</div><pre class="mono">${esc(code)}</pre></div><div><div class="muted" style="margin-bottom:6px">Optimized (${esc(opt.status)})</div><pre class="mono">${esc(opt.optimized_code)}</pre></div></div>
<div style="margin-top:12px"><button id="copy">Copy optimized code</button></div>` : `<div class="card"><div class="muted" style="margin-bottom:6px">Analyzed code</div><pre class="mono">${esc(code)}</pre></div>`}
<p class="muted" style="text-transform:none;margin-top:18px">Big-O computed from the Python AST (not guessed by AI) · Security: Bandit + custom rules · Optimizer: IBM Granite 3.3, verified before display · <a href="http://localhost:5173" target="_blank">Open full dashboard →</a></p>`;
  const c = document.getElementById('copy');
  if (c) c.onclick = async () => { await navigator.clipboard.writeText(opt.optimized_code); c.textContent = 'Copied ✓'; };
}
