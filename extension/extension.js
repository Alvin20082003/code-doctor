// Code Doctor — IBM Bob / VS Code extension
// Sends the current Python file to the Code Doctor backend, shows findings as
// squiggles in the editor, and opens a report panel with a verified
// IBM Granite fix that can be applied with one click.
const vscode = require('vscode');
const http = require('http');
const { URL } = require('url');

let diagnostics;
let statusItem;

function request(method, urlStr, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(urlStr);
    const data = body ? JSON.stringify(body) : null;
    const req = http.request({
      hostname: u.hostname, port: u.port, path: u.pathname, method,
      headers: data ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } : {}
    }, res => {
      let raw = '';
      res.on('data', c => (raw += c));
      res.on('end', () => {
        if (res.statusCode >= 400) return reject(new Error(`HTTP ${res.statusCode}: ${raw}`));
        try { resolve(JSON.parse(raw)); } catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function activate(context) {
  diagnostics = vscode.languages.createDiagnosticCollection('codeDoctor');
  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusItem.text = '$(pulse) Code Doctor';
  statusItem.command = 'codeDoctor.analyze';
  statusItem.tooltip = 'Analyze this file for scale, performance and security';
  statusItem.show();
  context.subscriptions.push(diagnostics, statusItem,
    vscode.commands.registerCommand('codeDoctor.analyze', () => analyze(context)));
}

async function analyze(context) {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return vscode.window.showWarningMessage('Code Doctor: open a Python file first.');
  const doc = editor.document;
  const code = doc.getText();
  if (!code.trim()) return vscode.window.showWarningMessage('Code Doctor: the file is empty.');
  const api = vscode.workspace.getConfiguration('codeDoctor').get('apiUrl');

  await vscode.window.withProgress({
    location: vscode.ProgressLocation.Notification,
    title: 'Code Doctor', cancellable: false
  }, async progress => {
    let job;
    try {
      progress.report({ message: 'Running time, space, performance and security analyzers…' });
      job = await request('POST', `${api}/api/analyze`, { code, language: 'python' });
    } catch (e) {
      vscode.window.showErrorMessage(`Code Doctor backend not reachable at ${api}. Start it with: python -m uvicorn main:app --reload`);
      return;
    }
    const started = Date.now();
    let report;
    while (Date.now() - started < 240000) {
      await sleep(1500);
      const r = await request('GET', `${api}/api/jobs/${job.job_id}`).catch(() => null);
      if (r && r.status !== 'running') { report = r; break; }
      const s = Math.round((Date.now() - started) / 1000);
      progress.report({ message: s < 3 ? 'Analyzing…' : `IBM Granite is optimizing and our analyzer is verifying… ${s}s` });
    }
    if (!report) return vscode.window.showErrorMessage('Code Doctor: analysis timed out.');
    showDiagnostics(doc, report);
    showPanel(context, editor, report);
    statusItem.text = `$(pulse) Scale Score ${report.score}${report.score_after ? ' → ' + report.score_after : ''}`;
  });
}

function showDiagnostics(doc, report) {
  const items = [];
  const add = (f, source) => {
    const line = Math.max(0, Math.min((f.line || 1) - 1, doc.lineCount - 1));
    const sev = (f.severity || '').toLowerCase() === 'high'
      ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning;
    const d = new vscode.Diagnostic(doc.lineAt(line).range,
      `${f.evidence || f.category || f.type}${f.fix ? ' → ' + f.fix : ''}`, sev);
    d.source = `Code Doctor (${source})`;
    items.push(d);
  };
  (report.performance || []).forEach(f => add(f, 'performance'));
  (report.security || []).forEach(f => add(f, 'security'));
  const t = report.time || {};
  if (/n\^2|n\*m|n\^3|2\^n/.test(t.complexity || '')) {
    const ev = (t.evidence || []).find(e => /nested|2\^n|O\(n\^2\)|n\*m/.test(e.reason)) || (t.evidence || [])[0];
    if (ev) {
      const line = Math.max(0, Math.min(ev.line - 1, doc.lineCount - 1));
      const d = new vscode.Diagnostic(doc.lineAt(line).range,
        `Time complexity ${t.complexity}: ${ev.reason}. This will slow down as data grows.`, vscode.DiagnosticSeverity.Warning);
      d.source = 'Code Doctor (scalability)';
      items.push(d);
    }
  }
  diagnostics.set(doc.uri, items);
}

function showPanel(context, editor, report) {
  const panel = vscode.window.createWebviewPanel('codeDoctor', 'Code Doctor Report',
    vscode.ViewColumn.Beside, { enableScripts: true });
  const opt = report.optimizer || {};
  const before = (opt.before && opt.before.time) || (report.time || {}).complexity;
  const after = opt.after && opt.after.time;
  const findings = [...(report.performance || []), ...(report.security || [])];
  const scoreColor = s => s >= 70 ? '#2FBF71' : s >= 40 ? '#F5A524' : '#F2555A';
  const banner = {
    verified: ['#2FBF71', `✓ Verified by Code Doctor's analyzer: ${esc(before)} → ${esc(after)}`],
    rejected: ['#F5A524', `AI suggestion rejected — our analyzer found it is still ${esc(after)}`],
    not_needed: ['#2FBF71', '✓ Already scales well — no optimization needed'],
    failed: ['#8A93A6', 'AI optimization unavailable — deterministic analysis shown'],
  }[opt.status] || ['#8A93A6', esc(opt.status || '')];
  const behavior = opt.validation && opt.validation.behavior;
  const behaviorText = behavior ? (behavior.tested ? (behavior.passed ? `Behavior test: ${behavior.cases || ''} cases — outputs identical ✓` : 'Behavior test: outputs differ ✗') : (behavior.reason || 'Static verification only')) : '';
  const canApply = opt.optimized_code && opt.status === 'verified';

  panel.webview.html = `<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{background:#0B0D12;color:#E6E8EE;font-family:Inter,Segoe UI,sans-serif;padding:16px;font-size:13px}
.card{background:#12151C;border:1px solid #232836;border-radius:8px;padding:12px;margin-bottom:12px}
.row{display:flex;gap:12px;flex-wrap:wrap}.tile{flex:1;min-width:110px}
.muted{color:#8A93A6;font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.mono{font-family:'JetBrains Mono',Consolas,monospace}.big{font-size:26px;font-weight:600}
.pill{font-size:10px;padding:2px 6px;border-radius:4px;font-weight:600}
pre{background:#181C25;border:1px solid #232836;border-radius:6px;padding:10px;overflow:auto;max-height:320px}
button{background:#4F8CFF;color:white;border:0;border-radius:6px;padding:8px 14px;font-weight:600;cursor:pointer}
h2{font-size:15px;margin:0 0 8px}
</style></head><body>
<h2>◆ Code Doctor <span class="muted">· powered by IBM Granite</span></h2>
<div class="row">
 <div class="card tile"><div class="muted">Scale Score</div><div class="big mono" style="color:${scoreColor(report.score)}">${report.score}${report.score_after && report.score_after > report.score ? ` <span style="color:#8A93A6">→</span> <span style="color:${scoreColor(report.score_after)}">${report.score_after}</span>` : ''}</div>${report.capped_reason ? `<div style="color:#F2555A;font-size:11px">${esc(report.capped_reason)}</div>` : ''}</div>
 <div class="card tile"><div class="muted">Time</div><div class="big mono">${esc(before)}${after && after !== before ? ` → ${esc(after)}` : ''}</div></div>
 <div class="card tile"><div class="muted">Space</div><div class="big mono">${esc((report.space || {}).complexity)}${opt.after && opt.after.space ? ` → ${esc(opt.after.space)}` : ''}</div></div>
 <div class="card tile"><div class="muted">Speedup @ 100k</div><div class="big mono">${report.speedup ? report.speedup.toLocaleString() + '×' : '—'}</div></div>
</div>
<div class="card"><div class="muted" style="margin-bottom:6px">Issues (${findings.length})</div>
${findings.length ? findings.map(f => `<div style="margin:6px 0"><span class="pill" style="background:${(f.severity||'').toLowerCase()==='high'?'#F2555A33;color:#F2555A':'#F5A52433;color:#F5A524'}">${esc((f.severity||'').toUpperCase())}</span> <b>${esc(f.category || f.type)}</b> <span class="mono muted">L${f.line}</span><div style="color:#8A93A6">${esc(f.fix || f.evidence)}</div></div>`).join('') : '<div style="color:#2FBF71">No performance or security issues found ✓</div>'}
</div>
<div class="card" style="border-color:${banner[0]}"><div style="color:${banner[0]};font-weight:600">${banner[1]}</div>${behaviorText ? `<div class="muted" style="margin-top:4px;text-transform:none">${esc(behaviorText)}</div>` : ''}</div>
${opt.explanation ? `<div class="card"><div class="muted">Why (IBM Granite)</div><p>${esc(opt.explanation)}</p></div>` : ''}
${opt.optimized_code ? `<div class="card"><div class="muted" style="margin-bottom:6px">Optimized code</div><pre class="mono">${esc(opt.optimized_code)}</pre>${canApply ? '<button onclick="apply()">Apply verified fix</button>' : ''}</div>` : ''}
<div class="muted" style="text-transform:none">Analyzed in ${report.total_ms || '?'} ms · Big-O computed from the AST, AI output verified before display</div>
<script>const vscode=acquireVsCodeApi();function apply(){vscode.postMessage({cmd:'apply'})}</script>
</body></html>`;

  panel.webview.onDidReceiveMessage(async msg => {
    if (msg.cmd !== 'apply' || !canApply) return;
    const doc = editor.document;
    const full = new vscode.Range(doc.positionAt(0), doc.positionAt(doc.getText().length));
    const ok = await vscode.window.showWarningMessage('Replace this file with the verified optimized code?', { modal: true }, 'Apply');
    if (ok !== 'Apply') return;
    const edit = new vscode.WorkspaceEdit();
    edit.replace(doc.uri, full, opt.optimized_code);
    await vscode.workspace.applyEdit(edit);
    diagnostics.delete(doc.uri);
    vscode.window.showInformationMessage('Code Doctor: verified fix applied. Undo with Ctrl+Z.');
  }, undefined, context.subscriptions);
}

function deactivate() {}
module.exports = { activate, deactivate };
