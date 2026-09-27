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

function render(code, report) {
  const opt = report.optimizer || {};
  const before = (opt.before && opt.before.time) || (report.time || {}).complexity;
  const after = opt.after && opt.after.time;
  const findings = [...(report.performance || []), ...(report.security || [])];
  const banner = {
    verified: ['#2FBF71', `✓ Verified by Code Doctor's analyzer: ${esc(before)} → ${esc(after)}`],
    rejected: ['#F5A524', `AI suggestion rejected — our analyzer found it is still ${esc(after)}`],
    not_needed: ['#2FBF71', '✓ Already scales well — no optimization needed'],
    failed: ['#8A93A6', 'AI optimization unavailable — deterministic analysis shown'],
  }[opt.status] || ['#8A93A6', esc(opt.status || '')];
  const b = opt.validation && opt.validation.behavior;
  const bt = b ? (b.tested ? (b.passed ? `Behavior test: ${b.cases || ''} cases — outputs identical ✓` : 'Behavior test: outputs differ ✗') : (b.reason || 'Static verification only')) : '';
  const evidence = ((report.time || {}).evidence || []).slice(0, 4);

  out.innerHTML = `
<div class="row">
 <div class="card tile"><div class="muted">Scale Score</div><div class="big mono" style="color:${color(report.score)}">${report.score}${report.score_after && report.score_after > report.score ? ` <span style="color:#8A93A6">→</span> <span style="color:${color(report.score_after)}">${report.score_after}</span>` : ''}</div>${report.capped_reason ? `<div style="color:#F2555A;font-size:12px">${esc(report.capped_reason)}</div>` : ''}</div>
 <div class="card tile"><div class="muted">Time</div><div class="big mono">${esc(before)}${after && after !== before ? ` → <span style="color:#2FBF71">${esc(after)}</span>` : ''}</div></div>
 <div class="card tile"><div class="muted">Space</div><div class="big mono">${esc((report.space || {}).complexity)}${opt.after && opt.after.space && opt.after.space !== (report.space||{}).complexity ? ` → <span style="color:#2FBF71">${esc(opt.after.space)}</span>` : ''}</div></div>
 <div class="card tile"><div class="muted">Speedup @ 100k</div><div class="big mono">${report.speedup ? report.speedup.toLocaleString() + '×' : '—'}</div></div>
</div>
${evidence.length ? `<div class="card"><div class="muted" style="margin-bottom:6px">Why this complexity</div>${evidence.map(e => `<div class="mono" style="font-size:12px;margin:3px 0"><span style="color:#8A93A6">L${e.line}</span> ${esc(e.reason)}</div>`).join('')}</div>` : ''}
<div class="card"><div class="muted" style="margin-bottom:6px">Issues (${findings.length})</div>
${findings.length ? findings.map(f => `<div style="margin:8px 0"><span class="pill" style="${(f.severity||'').toLowerCase()==='high'?'background:#F2555A33;color:#F2555A':'background:#F5A52433;color:#F5A524'}">${esc((f.severity||'').toUpperCase())}</span> <b>${esc(f.category || f.type)}</b> <span class="mono muted">L${f.line}</span><div style="color:#8A93A6;font-size:13px">${esc(f.fix || f.evidence)}</div></div>`).join('') : '<div style="color:#2FBF71">No performance or security issues ✓</div>'}
</div>
<div class="card" style="border-color:${banner[0]}"><b style="color:${banner[0]}">${banner[1]}</b>${bt ? `<div class="muted" style="text-transform:none;margin-top:4px">${esc(bt)}</div>` : ''}</div>
${opt.explanation ? `<div class="card"><div class="muted">Why (IBM Granite)</div><p style="margin:6px 0 0;line-height:1.55">${esc(opt.explanation)}</p></div>` : ''}
${opt.optimized_code ? `<div class="grid2"><div><div class="muted" style="margin-bottom:6px">Original</div><pre class="mono">${esc(code)}</pre></div><div><div class="muted" style="margin-bottom:6px">Optimized (verified)</div><pre class="mono">${esc(opt.optimized_code)}</pre></div></div>
<div style="margin-top:12px"><button id="copy">Copy optimized code</button> <a href="http://localhost:5173" target="_blank" style="margin-left:12px">Open full dashboard →</a></div>` : ''}
<p class="muted" style="text-transform:none;margin-top:18px">Analyzed in ${report.total_ms || '?'} ms · Big-O computed from the AST · AI output verified before display</p>`;
  const c = document.getElementById('copy');
  if (c) c.onclick = async () => { await navigator.clipboard.writeText(opt.optimized_code); c.textContent = 'Copied ✓'; };
}
