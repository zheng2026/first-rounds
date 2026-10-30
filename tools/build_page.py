#!/usr/bin/env python3
"""Build tests/results.html (self-contained review page) from tests/results.json + tests/notes.json."""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
res = json.load(open(os.path.join(ROOT, "tests", "results.json"), encoding="utf-8"))
nd = json.load(open(os.path.join(ROOT, "tests", "notes.json"), encoding="utf-8"))
data = {"results": res, "notes": nd["notes"], "coverage": nd.get("coverage", {})}
blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

TEMPLATE = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>First Rounds - eval review</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}
body{margin:0;font:14.5px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#f6f6f3;color:#222}
#bar{position:sticky;top:0;z-index:10;background:#fff;border-bottom:1px solid #ccc;padding:6px 12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
#bar b{margin-right:8px}
button,select{font:inherit;padding:2px 8px;cursor:pointer}
main{padding:12px 16px}
h2{margin:22px 0 6px;font-size:16px}
table{border-collapse:collapse;background:#fff}
th,td{border:1px solid #d5d5d0;padding:3px 8px;text-align:center;vertical-align:top}
th{background:#eeeee9;font-weight:600}
td.l,th.l{text-align:left}
tr.click{cursor:pointer}tr.click:hover td{outline:2px solid #88a}
.best{font-weight:700;text-decoration:underline}
.bad{color:#b00;font-weight:700}.ok{color:#080;font-weight:700}
.sep td{background:#eee;font-weight:600;text-align:left}
.small{font-size:12px;color:#555}
#detail{margin-top:8px}
.exp{background:#fff;border:1px solid #ccc;padding:8px 12px;margin-bottom:10px}
.cols{display:flex;gap:10px;overflow-x:auto;align-items:flex-start}
.col{min-width:340px;width:340px;background:#fff;border:1px solid #ccc;padding:8px;flex:none}
.col.best{outline:3px solid #4a4;text-decoration:none;font-weight:400}
.chip{display:inline-block;background:#eef;border-radius:8px;padding:0 6px;margin:1px;font-size:12px}
.flag{display:inline-block;background:#fed;border-radius:8px;padding:0 6px;margin:1px;font-size:12px;color:#840}
.emerg{background:#fdd;border:2px solid #c00;padding:4px 8px;margin:4px 0}
.emerg0{background:#efe;padding:2px 8px;margin:4px 0;font-size:12px}
.lbl{font-weight:600;margin-top:6px;color:#446}
ul{margin:2px 0;padding-left:18px}
pre{white-space:pre-wrap;word-break:break-word;background:#f3f3f3;padding:6px;font-size:12px;max-height:400px;overflow:auto}
.mustnot{color:#a40}
.judge{border-top:1px dashed #aaa;margin-top:8px;padding-top:4px}
.tl{border-left:3px solid #99b;padding-left:6px;margin:4px 0}
</style></head><body>
<div id="bar"><b>First Rounds eval</b>
<button onclick="show('summary')">Summary</button>
<button onclick="show('emerg')">Emergency</button>
<button onclick="show('grid')">Per-note grid</button>
<label>Grouping <select id="grp" onchange="renderGrid()"><option value="note">by note</option><option value="case">by case</option></select></label>
<button onclick="exportJ()">Export judgments</button>
<button onclick="clearJ()">Clear judgments</button>
<span class="small" id="ran"></span></div>
<main>
<section id="s-summary"></section>
<section id="s-emerg"></section>
<section id="s-grid"></section>
<section id="detail" style="display:none"></section>
</main>
<script>
"use strict";
const D = __DATA__;
const R = D.results, NOTES = D.notes, DIMS = R.meta.dimensions;
const NBY = {}; NOTES.forEach(n => NBY[n.id] = n);
const COMBOS = []; R.meta.variants.forEach(v => Object.keys(R.meta.models).forEach(m => COMBOS.push({v, m, key: v + "__" + m})));
const RUN = {}; R.runs.forEach(r => RUN[r.note_id + "|" + r.variant + "|" + r.model] = r);
const run = (nid, c) => RUN[nid + "|" + c.v + "|" + c.m];
function esc(s) { return String(s == null ? "" : s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function shade(x) { if (x == null) return ""; const h = Math.round(120 * Math.max(0, Math.min(1, x))); return 'style="background:hsl(' + h + ',65%,82%)"'; }
function mean(a) { a = a.filter(x => x != null); return a.length ? a.reduce((p, q) => p + q, 0) / a.length : null; }
function f2(x) { return x == null ? "-" : x.toFixed(2); }
function runsOf(c) { return R.runs.filter(r => r.variant === c.v && r.model === c.m); }
function runMean(r) { if (!r) return null; return mean(DIMS.map(d => (r.scores || {})[d[0]]).filter(x => typeof x === "number")); }
document.getElementById("ran").textContent = "ran " + (R.meta.ran_at || "") + " - " + R.runs.length + " runs";

function show(w) { document.getElementById("detail").style.display = "none";
  ["summary","emerg","grid"].forEach(k => document.getElementById("s-" + k).style.display = "");
  if (w) document.getElementById("s-" + w).scrollIntoView(); }

function bestRow(vals, hi) { const ok = vals.filter(x => x != null); if (!ok.length) return -1; const b = hi ? Math.max(...ok) : Math.min(...ok); return vals.indexOf(b); }
function renderSummary() {
  let h = '<h2>Summary</h2><table><tr><th class="l">dimension</th>' + COMBOS.map(c => "<th>" + esc(c.v) + "<br>" + esc(c.m) + "</th>").join("") + "</tr>";
  const row = (label, title, vals, fmt, shadeIt, hi) => {
    const b = bestRow(vals, hi);
    h += '<tr><td class="l" title="' + esc(title) + '">' + esc(label) + "</td>" + vals.map((x, i) =>
      "<td " + (shadeIt ? shade(x) : "") + (i === b ? ' class="best"' : "") + ">" + fmt(x) + "</td>").join("") + "</tr>";
  };
  DIMS.forEach(d => row(d[1], d[2], COMBOS.map(c => mean(runsOf(c).map(r => (r.scores || {})[d[0]]))), f2, true, true));
  row("json_valid", "fraction of runs whose output parsed", COMBOS.map(c => { const rs = runsOf(c); return rs.length ? rs.filter(r => r.output).length / rs.length : null; }), f2, true, true);
  row("mean latency (s)", "total over all steps", COMBOS.map(c => mean(runsOf(c).map(r => r.latency_ms_total / 1000))), x => x == null ? "-" : x.toFixed(1), false, false);
  row("mean tokens", "prompt + completion, all steps", COMBOS.map(c => mean(runsOf(c).map(r => (r.prompt_tokens || 0) + (r.completion_tokens || 0)))), x => x == null ? "-" : Math.round(x), false, false);
  document.getElementById("s-summary").innerHTML = h + "</table>";
}
function emOK(r, n) { return !!(r && r.output && r.output.emergency && r.output.emergency.warning === !!n.expected.emergency_warning); }
function renderEmerg() {
  const pos = NOTES.filter(n => n.expected.emergency_warning);
  const posIds = new Set(pos.map(n => n.id));
  const neg = NOTES.filter(n => !posIds.has(n.id) && ((n.covers || []).includes("emergency-false-control") || n.id === "n18" || n.id === "n08"));
  const caught = COMBOS.map(c => pos.filter(n => { const r = run(n.id, c); return r && r.output && r.output.emergency && r.output.emergency.warning === true; }).length);
  let h = "<h2>Emergency</h2><p><b>positives caught:</b> " + COMBOS.map((c, i) => esc(c.key) + " " + caught[i] + "/" + pos.length).join(" &nbsp;|&nbsp; ") + "</p>";
  h += '<table><tr><th class="l">note</th>' + COMBOS.map(c => "<th>" + esc(c.v) + "<br>" + esc(c.m) + "</th>").join("") + "</tr>";
  const rowf = (n, isPos) => {
    h += '<tr class="click" onclick="openNote(\'' + n.id + '\')"><td class="l">' + esc(n.id) + " " + esc(n.problem) + "</td>" + COMBOS.map(c => {
      const r = run(n.id, c), ok = emOK(r, n), sign = r && r.output && r.output.emergency && r.output.emergency.sign;
      return "<td title=\"" + esc(isPos && sign ? sign.toString().slice(0, 200) : "") + "\">" + (ok ? '<span class="ok">&#10003;</span>' : '<span class="bad">&#10007;</span>') +
        (isPos && sign ? ' <span class="small">' + esc(String(sign).slice(0, 25)) + "</span>" : "") + "</td>";
    }).join("") + "</tr>";
  };
  pos.forEach(n => rowf(n, true));
  h += '<tr class="sep"><td colspan="' + (COMBOS.length + 1) + '">negative controls (must NOT trigger)</td></tr>';
  neg.forEach(n => rowf(n, false));
  document.getElementById("s-emerg").innerHTML = h + "</table>";
}
function gridRow(n) {
  return '<tr class="click" onclick="openNote(\'' + n.id + '\')"><td class="l">' + esc(n.id) + "</td><td>" + esc(n.note_date) + "</td><td>" + esc(n.language) + "</td><td class=\"l\">" + esc(n.problem) + '</td><td class="l small">' + esc(n.note.slice(0, 50)) + "</td>" +
    COMBOS.map(c => { const r = run(n.id, c), m = runMean(r); return "<td " + shade(m) + ">" + (r ? (r.output ? f2(m) : "parse err " + f2(m)) : "-") + "</td>"; }).join("") + "</tr>";
}
function renderGrid() {
  const head = '<tr><th>id</th><th>date</th><th>lang</th><th class="l">problem</th><th class="l">note</th>' + COMBOS.map(c => "<th>" + esc(c.v) + "<br>" + esc(c.m) + "</th>").join("") + "</tr>";
  let h = "<h2>Per-note grid</h2><table>" + head;
  if (document.getElementById("grp").value === "case") {
    const mc = (D.coverage || {}).mandatory_cases || {};
    Object.keys(mc).forEach(k => { h += '<tr class="sep"><td colspan="' + (5 + COMBOS.length) + '">' + esc(k) + "</td></tr>"; mc[k].forEach(id => { if (NBY[id]) h += gridRow(NBY[id]); }); });
  } else NOTES.forEach(n => h += gridRow(n));
  document.getElementById("s-grid").innerHTML = h + "</table>";
}

// ---- detail
let cur = null;
function ul(a) { return a && a.length ? "<ul>" + a.map(x => "<li>" + esc(typeof x === "string" ? x : JSON.stringify(x)) + "</li>").join("") + "</ul>" : '<span class="small">(none)</span>'; }
function timeline(tl) {
  if (!tl || !tl.length) return '<span class="small">(empty)</span>';
  return tl.map(e => {
    if (typeof e !== "object" || !e) return '<div class="tl">' + esc(e) + "</div>";
    let s = '<div class="tl"><b>' + esc(e.date == null ? "no date" : e.date) + "</b>" + (e.date_precision ? " (" + esc(e.date_precision) + ")" : "") + " &mdash; " + esc(e.what);
    const bits = [];
    if (e.department) bits.push("dept: " + e.department);
    if (e.test) bits.push("test: " + e.test);
    if (e.test_where) bits.push("where: " + e.test_where);
    if (e.result) bits.push("result: " + e.result);
    if (bits.length) s += "<br>" + bits.map(esc).join(" &middot; ");
    const me = e.medicine_event;
    if (me && typeof me === "object") s += "<br><i>medicine:</i> " + esc([me.name, me.event, me.date && ("on " + me.date), me.dose && ("dose " + me.dose), me.stopping_rule && ("rule: " + me.stopping_rule), me.reason && ("reason: " + me.reason), me.detail, me.note].filter(Boolean).join(" | "));
    if (e.helps && e.helps.length) s += "<br>helps: " + esc(e.helps.join("; "));
    if (e.worsens && e.worsens.length) s += "<br>worsens: " + esc(e.worsens.join("; "));
    if (e.date_note) s += '<br><span class="small">' + esc(e.date_note) + "</span>";
    return s + "</div>";
  }).join("");
}
function body(o, isExp) {
  let h = "";
  const warn = isExp ? o.emergency_warning : (o.emergency && o.emergency.warning);
  if (isExp) h += warn ? '<div class="emerg"><b>EMERGENCY expected.</b> ' + esc(o.emergency_reason || "") + "</div>" : '<div class="emerg0">no emergency expected</div>';
  else h += warn ? '<div class="emerg"><b>EMERGENCY</b> sign: ' + esc(o.emergency.sign) + " &middot; source: " + esc(o.emergency.source) + "</div>" : '<div class="emerg0">emergency: false</div>';
  if (o.nothing_medical) h += "<div><b>nothing_medical: true</b></div>";
  h += '<div class="lbl">Timeline</div>' + timeline(o.timeline);
  h += '<div class="lbl">Open questions</div>' + ul(o.open_questions);
  h += '<div class="lbl">Todos</div>' + ul(o.todos);
  h += '<div class="lbl">Ask the doctor</div>' + ul(o.ask_the_doctor);
  h += '<div class="lbl">Current medicines</div>' + ul(o.current_medicines);
  h += '<div class="lbl">History question</div><div>' + (o.history_question ? esc(o.history_question) : '<span class="small">(none)</span>') + "</div>";
  if (isExp && o.must_not) h += '<div class="lbl">Must not</div><ul class="mustnot">' + o.must_not.map(x => "<li>" + esc(x) + "</li>").join("") + "</ul>";
  return h;
}
const JK = "fr_judgments_v1";
function getJ() { try { return JSON.parse(localStorage.getItem(JK) || "{}"); } catch (e) { return {}; } }
function setJ(nid, c, field, val) { const j = getJ(); const k = nid + "|" + c.v + "|" + c.m; j[k] = j[k] || {}; j[k][field] = val; localStorage.setItem(JK, JSON.stringify(j)); }
function setBest(nid, ck) { const j = getJ(); COMBOS.forEach(c => { const k = nid + "|" + c.v + "|" + c.m; if (j[k]) delete j[k].best; }); if (ck) { const k = nid + "|" + ck; j[k] = j[k] || {}; j[k].best = true; } localStorage.setItem(JK, JSON.stringify(j)); }
function toggleRaw(i) { const e = document.getElementById("raw" + i); e.style.display = e.style.display === "none" ? "" : "none"; }
function openNote(id) {
  cur = NOTES.findIndex(n => n.id === id);
  ["summary","emerg","grid"].forEach(k => document.getElementById("s-" + k).style.display = "none");
  renderDetail(); window.scrollTo(0, 0);
}
function step(d) { if (cur == null) return; cur = (cur + d + NOTES.length) % NOTES.length; renderDetail(); window.scrollTo(0, 0); }
function renderDetail() {
  const n = NOTES[cur], J = getJ();
  const sel = (nid, c, f, v) => '<select onchange="setJ(\'' + nid + '\',COMBOS[' + COMBOS.indexOf(c) + '],\'' + f + '\',this.value)">' + ["0", "1", "2"].map(x => '<option value="' + x + '"' + (String(v) === x ? " selected" : "") + ">" + x + "</option>").join("") + "</select>";
  let h = '<div><button onclick="show()">&larr; back</button> <button onclick="step(-1)">&larr; prev</button> <button onclick="step(1)">next &rarr;</button> <b>' + esc(n.id) + "</b> (" + (cur + 1) + "/" + NOTES.length + ") " + esc(n.note_date) + " &middot; " + esc(n.language) + " &middot; " + esc(n.problem) + "</div>";
  h += '<div class="exp"><div class="lbl">Note</div><div style="font-size:16px;white-space:pre-wrap">' + esc(n.note) + '</div><div class="small">note date: ' + esc(n.note_date) + " &middot; covers: " + esc((n.covers || []).join(", ")) + "</div>";
  h += '<div class="lbl" style="font-size:15px">EXPECTED</div>' + body(n.expected, true) + "</div>";
  h += '<div class="cols">';
  COMBOS.forEach((c, i) => {
    const r = run(n.id, c), k = n.id + "|" + c.v + "|" + c.m, jj = J[k] || {};
    h += '<div class="col"><b>' + esc(c.v) + "<br>" + esc(c.m) + "</b><br>";
    if (!r) { h += "no run</div>"; return; }
    DIMS.forEach(d => { const x = (r.scores || {})[d[0]]; h += '<span class="chip" title="' + esc(d[2]) + '" ' + shade(x) + ">" + esc(d[0]) + ": " + (x == null ? "n/a" : x.toFixed(2)) + "</span>"; });
    ((r.scores || {}).flags || []).forEach(f => h += '<span class="flag">' + esc(f) + "</span>");
    h += '<div class="small">' + (r.latency_ms_total / 1000).toFixed(1) + "s &middot; " + (r.prompt_tokens || 0) + "+" + (r.completion_tokens || 0) + " tok</div>";
    if (r.output) h += body(r.output, false);
    else h += '<div class="emerg"><b>PARSE ERROR:</b> ' + esc(r.parse_error) + "</div><pre>" + esc((r.steps_raw || []).slice(-1)[0]) + "</pre>";
    h += '<div><button onclick="toggleRaw(' + i + ')">raw JSON</button><pre id="raw' + i + '" style="display:none">' + esc(r.output ? JSON.stringify(r.output, null, 1) : "") + (r.steps_raw && r.steps_raw.length > 1 ? "\n\n--- all steps raw ---\n" + esc(r.steps_raw.join("\n\n=====\n\n")) : "") + "</pre></div>";
    h += '<div class="judge">invented ' + sel(n.id, c, "invented", jj.invented || 0) + " advice " + sel(n.id, c, "advice", jj.advice || 0) +
      '<br><label><input type="radio" name="best" ' + (jj.best ? "checked" : "") + " onchange=\"setBest('" + n.id + "','" + c.key + "')\"> best for this note</label></div></div>";
  });
  document.getElementById("detail").innerHTML = h + "</div>";
  document.getElementById("detail").style.display = "";
}
document.addEventListener("keydown", e => { if (cur == null || document.getElementById("detail").style.display === "none") return; if (/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
  if (e.key === "ArrowLeft") step(-1); else if (e.key === "ArrowRight") step(1); });
function exportJ() { const b = new Blob([JSON.stringify(getJ(), null, 1)], {type: "application/json"}); const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = "fr_judgments.json"; a.click(); }
function clearJ() { if (confirm("Clear all manual judgments?")) { localStorage.removeItem(JK); if (cur != null && document.getElementById("detail").style.display !== "none") renderDetail(); } }
renderSummary(); renderEmerg(); renderGrid();
</script></body></html>
'''
out = TEMPLATE.replace("__DATA__", blob)
p = os.path.join(ROOT, "tests", "results.html")
open(p, "w", encoding="utf-8").write(out)
print("wrote %s (%d bytes)" % (p, len(out.encode("utf-8"))))
