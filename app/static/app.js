"use strict";
/* ===== MOCK (only when the URL has ?mock=1) — same shapes as the HTTP API in app/CONTRACT.md ===== */
const MOCK = (function () {
  const iso = (off) => { const d = new Date(); d.setDate(d.getDate() + off); return d.toISOString().slice(0, 10); };
  const T = (off) => iso(off);
  const stopTodo = { id: 11, note_id: 4, kind: "stopcheck", text: 'Tell Mom: the doctor said "finish all 7 days" (antibiotic Y)', detail: "antibiotic Y stopped " + T(-9) + "; reason: teeth feel better", done_at: null, created_at: T(-9), note_date: T(-9) };
  const entries = [
    { id: 1, note_id: 5, problem: "teeth", date: "2024", date_precision: "rough", sort_key: "2024-07-01", what: "Crowns on three teeth.", source: "crowns in 2024, I don't know which teeth", note_date: T(-1), stopcheck: null, chips: [{ kind: "question", text: "which teeth?" }] },
    { id: 2, note_id: 1, problem: "teeth", date: T(-20), date_precision: "about", sort_key: T(-20), what: "Molars started hurting. Toothpaste X made it worse.", source: "her molars have been hurting for a week. She tried toothpaste X but it only made it worse", note_date: T(-19), stopcheck: null, chips: [{ kind: "worse", text: "worse: toothpaste X" }, { kind: "question", text: "which molars?" }] },
    { id: 3, note_id: 1, problem: "teeth", date: T(-19), date_precision: "exact", sort_key: T(-19), what: "Asked me to buy brand A instead. Trying to book a dentist for next week.", source: "She asked me to buy brand A instead. She is trying to book an appointment for next week", note_date: T(-19), stopcheck: null, chips: [] },
    { id: 4, note_id: 2, problem: "teeth", date: T(-12), date_precision: "exact", sort_key: T(-12), what: "Dentist. Antibiotic Y prescribed, 3x a day.", source: "dentist gave her antibiotic Y, three times a day, said finish all 7 days", note_date: T(-12), stopcheck: null, chips: [{ kind: "med", text: "started · antibiotic Y" }, { kind: "rule", text: "rule: finish all 7 days" }] },
    { id: 5, note_id: 4, problem: "teeth", date: T(-9), date_precision: "exact", sort_key: T(-9), what: "Teeth feel better. She stopped antibiotic Y.", source: "teeth feel better, she stopped Y", note_date: T(-9), stopcheck: stopTodo, chips: [{ kind: "med-stop", text: "stopped · antibiotic Y" }] },
    { id: 6, note_id: 3, problem: "teeth", date: "next week", date_precision: "rough", sort_key: T(7), what: "Dentist appointment.", source: "She is trying to book an appointment for next week", note_date: T(-19), stopcheck: null, chips: [{ kind: "question", text: "date confirmed?" }] }
  ];
  const todos = [
    { id: 21, note_id: 1, kind: "reminder", text: "Buy brand A toothpaste for Mom", detail: null, done_at: null, created_at: T(-19), note_date: T(-19) },
    { id: 22, note_id: 3, kind: "appointment", text: "Dentist appointment — has the date been confirmed?", detail: null, done_at: null, created_at: T(-19), note_date: T(-19) },
    stopTodo
  ];
  const notes = [
    { id: 5, note_date: T(-1), text: "Answer to \"Any big dental work before?\": crowns in 2024, I don't know which teeth", kind: "answer", created_at: T(-1), problem: "teeth", entry_count: 1, emergency: false },
    { id: 4, note_date: T(-9), text: "teeth feel better, she stopped Y", kind: "call", created_at: T(-9), problem: "teeth", entry_count: 1, emergency: false },
    { id: 1, note_date: T(-19), text: "her molars have been hurting for a week. She tried toothpaste X but it only made it worse. She asked me to buy brand A instead. She is trying to book an appointment for next week", kind: "call", created_at: T(-19), problem: "teeth", entry_count: 3, emergency: false }
  ];
  return {
    timeline: { problems: [{ problem: "teeth", since: "2024", note_count: 5, entries: entries }] },
    today: {
      emergencies: [],
      todos: todos,
      questions: [{ id: 31, note_id: 1, text: "Has Mom had any big dental work before?", answered_at: null, note_date: T(-19) }],
      appointments: [entries[5]]
    },
    notes: notes,
    result: function (text) {
      const emerg = /胸口|chest/i.test(text);
      return {
        note: { id: 90, note_date: iso(0), text: text, kind: "call" },
        problem: emerg ? "chest" : "teeth", nothing_medical: false,
        emergency: emerg ? { warning: true, sign: "chest pain", source: "NHS",
          text_en: "This note describes a possible warning sign: chest pain. NHS guidance on when to call an ambulance advises calling emergency services (120 in China) immediately, even if symptoms have passed. Call Mom now. If signs are present, she or someone near her should call 120.",
          text_zh: "这条记录提到了可能的预警信号：胸痛。英国NHS急救指南建议：即使症状已经消失，也应立即拨打120。请现在给妈妈打电话；如果症状仍在，请她或身边的人拨打120。" } : null,
        entries: [{ id: 91, note_id: 90, problem: "teeth", date: iso(0), date_precision: "exact", sort_key: iso(0), what: "Mentioned in this note (mock).", source: text.slice(0, 80), note_date: iso(0), stopcheck: null, chips: [] }],
        questions: [{ id: 92, note_id: 90, text: "Which tooth is it?", answered_at: null, note_date: iso(0) }],
        todos: [{ id: 93, note_id: 90, kind: "reminder", text: "Ask Mom for the dentist's phone number", detail: null, done_at: null, created_at: iso(0), note_date: iso(0) }],
        ask_doctor: [], current_medicines: [], history_question: null, extraction_error: null
      };
    }
  };
})();

/* ===== API layer ===== */
const IS_MOCK = new URLSearchParams(location.search).get("mock") === "1";

async function mockApi(method, path, body) {
  await new Promise((r) => setTimeout(r, 120));
  let m;
  if (path === "/api/timeline") return MOCK.timeline;
  if (path === "/api/today") return MOCK.today;
  if (path === "/api/notes" && method === "GET") return MOCK.notes;
  if (path === "/api/notes" && method === "POST") return MOCK.result(body.text);
  if ((m = path.match(/^\/api\/notes\/(\d+)$/))) {
    const id = +m[1];
    if (method === "DELETE") { MOCK.notes = MOCK.notes.filter((n) => n.id !== id); return { ok: true }; }
    const n = MOCK.notes.find((x) => x.id === id) || MOCK.notes[0];
    const es = MOCK.timeline.problems[0].entries.filter((e) => e.note_id === id);
    const qs = MOCK.today.questions.filter((q) => q.note_id === id);
    const ts = MOCK.today.todos.filter((t) => t.note_id === id);
    return { note: { id: n.id, note_date: n.note_date, text: n.text, kind: n.kind }, problem: n.problem, nothing_medical: false, emergency: null, entries: es, questions: qs, todos: ts, ask_doctor: [], current_medicines: [], history_question: null, extraction_error: null };
  }
  if ((m = path.match(/^\/api\/todos\/(\d+)\/(done|undone)$/))) {
    const t = MOCK.today.todos.find((x) => x.id === +m[1]);
    if (t) t.done_at = m[2] === "done" ? new Date().toISOString() : null;
    return { ok: true };
  }
  if ((m = path.match(/^\/api\/questions\/(\d+)\/answer$/))) {
    MOCK.today.questions = MOCK.today.questions.filter((q) => q.id !== +m[1]);
    const r = MOCK.result(body.text); r.questions = []; r.todos = []; return r;
  }
  throw new Error("mock: no route " + method + " " + path);
}

async function api(method, path, body) {
  if (IS_MOCK) return mockApi(method, path, body);
  const opt = { method: method, headers: {} };
  if (body !== undefined) { opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const res = await fetch(path, opt);
  let data = null;
  try { data = await res.json(); } catch (e) { /* non-JSON body */ }
  if (!res.ok) throw new Error((data && data.error) || ("HTTP " + res.status));
  if (data === null) throw new Error("Bad response");
  return data;
}

/* ===== tiny DOM helpers (textContent only: no innerHTML with data) ===== */
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const k in attrs || {}) {
    const v = attrs[k];
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "text") el.textContent = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
const $main = () => document.getElementById("main");
function show(...nodes) { const m = $main(); m.replaceChildren(...nodes.flat().filter(Boolean)); }
function errBlock() { return h("div", { class: "errblock bad", role: "alert" }, "Couldn't reach the app. Check it's running."); }
function todayISO() { const d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
function fmtDate(s) {
  if (!s) return "date unknown";
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return s;
  const md = +m[2] + "/" + +m[3];
  return +m[1] === new Date().getFullYear() ? md : md + "/" + m[1];
}
const isExact = (p) => !p || p === "exact" || p === "day";

/* ===== shared components ===== */
function chip(c) {
  const k = c.kind;
  const cls = { med: "chip med", "med-stop": "chip med stop", question: "chip q", worse: "chip worse", help: "chip help" }[k] || "chip";
  return h("span", { class: cls }, c.text);
}

function entryNode(e) {
  const iso = /^\d{4}-\d{2}-\d{2}$/.test(e.sort_key || "") ? e.sort_key : "";
  const future = iso && iso > todayISO();
  const rough = !isExact(e.date_precision);
  const cls = "e" + (future ? " future" : rough ? " rough" : "");
  const card = h("div", { class: "card" + (e.stopcheck ? " stopcheck" : "") });
  card.append(h("div", { class: "date" }, h("b", null, fmtDate(e.date)), !isExact(e.date_precision) ? e.date_precision : null));
  card.append(h("div", { class: "what" }, e.what));
  if (e.chips && e.chips.length) card.append(h("div", { class: "chips" }, e.chips.map(chip)));
  if (e.stopcheck) card.append(stopcheckNode(e.stopcheck));
  if (e.source) {
    const btn = h("button", { class: "src", type: "button", "aria-expanded": "false", onclick: () => btn.setAttribute("aria-expanded", btn.getAttribute("aria-expanded") !== "true") },
      "from note " + fmtDate(e.note_date));
    card.append(btn, h("p", { class: "quote" }, "“" + e.source + "”"));
  }
  return h("li", { class: cls }, card);
}

function stopcheckNode(t) {
  const noRule = /^Mom stopped/.test(t.text);
  const wrap = h("div");
  wrap.append(h("div", { class: "h" }, "Stop-check"), h("div", { class: "rule" }, t.text));
  if (t.detail) wrap.append(h("div", { class: "detail" }, t.detail));
  const btn = h("button", { class: "act", type: "button" }, noRule ? "Ask doctor" : "Tell Mom");
  const markDone = () => { btn.className = "act done"; btn.disabled = true; btn.textContent = "Marked done"; };
  if (t.done_at) markDone();
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    try { await api("POST", "/api/todos/" + t.id + "/done"); t.done_at = "now"; markDone(); }
    catch (e) { btn.disabled = false; btn.after(h("span", { class: "muted", role: "alert" }, " Couldn't reach the app. Check it's running.")); }
  });
  wrap.append(btn);
  return wrap;
}

function emergencyNode(en, zh, source) {
  return h("section", { class: "emergency", role: "alert" },
    h("div", { class: "t" }, "Possible warning sign"),
    en ? h("p", { lang: "en" }, en) : null,
    zh ? h("p", { lang: "zh" }, zh) : null,
    source ? h("div", { class: "srcs" }, "Source: " + source) : null);
}

function answerBox(q, onSaved) {
  const ta = h("textarea", { id: "ans-" + q.id, "aria-label": "Your answer", placeholder: "Your answer" });
  const msg = h("div", { class: "muted", role: "status" });
  const btn = h("button", { class: "btn", type: "button" }, "Save answer");
  btn.addEventListener("click", async () => {
    const text = ta.value.trim();
    if (!text) { msg.textContent = "Type an answer first."; return; }
    btn.disabled = true; btn.textContent = "Saving…"; msg.textContent = "";
    try {
      const r = await api("POST", "/api/questions/" + q.id + "/answer", { text: text });
      const n = (r.entries || []).length;
      box.replaceChildren(h("div", { class: "muted", role: "status" }, "Saved." + (n ? " " + n + (n === 1 ? " entry" : " entries") + " added to the timeline." : "")));
      if (onSaved) onSaved(r);
    } catch (e) { btn.disabled = false; btn.textContent = "Save answer"; msg.replaceChildren(errBlock()); }
  });
  const box = h("div", { class: "answer" }, ta, btn, msg);
  return box;
}

function questionNode(q, onSaved) {
  return h("li", { class: "item" }, h("div", null, q.text), q.note_date ? h("div", { class: "muted" }, "from note " + fmtDate(q.note_date)) : null, answerBox(q, onSaved));
}

function todoNode(t, onChange) {
  const cb = h("input", { type: "checkbox", id: "todo-" + t.id });
  cb.checked = !!t.done_at;
  const row = h("li", { class: "item todo" + (t.done_at ? " done" : "") });
  cb.addEventListener("change", async () => {
    const want = cb.checked;
    try {
      await api("POST", "/api/todos/" + t.id + (want ? "/done" : "/undone"));
      t.done_at = want ? "now" : null; row.classList.toggle("done", want);
      if (onChange) onChange();
    } catch (e) { cb.checked = !want; row.append(errBlock()); }
  });
  row.append(cb, h("div", { class: "box" },
    h("label", { for: "todo-" + t.id }, t.text),
    t.detail ? h("div", { class: "detail" }, t.detail) : null,
    t.note_date ? h("div", { class: "muted" }, "from note " + fmtDate(t.note_date)) : null));
  return row;
}

function emergencyTodoNode(t) {
  return h("section", { class: "emergency", role: "alert" },
    h("div", { class: "t" }, "Possible warning sign"),
    h("p", { lang: "en" }, t.text),
    t.detail ? h("p", { lang: "zh" }, t.detail) : null,
    t.note_date ? h("div", { class: "srcs" }, "From note " + fmtDate(t.note_date)) : null);
}

/* ===== screens ===== */
async function viewTimeline() {
  show(h("div", { class: "muted" }, "Loading…"));
  try {
    const [tl, td] = await Promise.all([api("GET", "/api/timeline"), api("GET", "/api/today")]);
    const out = [];
    const items = (td.todos || []).filter((t) => !t.done_at);
    if (items.length) {
      out.push(h("a", { class: "today", href: "#today" },
        h("div", { class: "h" }, "Today · " + items.length + " to do"),
        h("ul", null, items.slice(0, 3).map((t) => h("li", null, t.text)))));
    }
    const ps = tl.problems || [];
    if (!ps.length) out.push(h("div", { class: "empty" }, "No notes yet. Tap + After the call."));
    for (const p of ps) {
      const cap = p.problem ? p.problem.charAt(0).toUpperCase() + p.problem.slice(1) : "Other";
      out.push(h("div", { class: "problem" }, h("h2", null, cap),
        h("span", { class: "since" }, (p.since ? "since " + fmtDate(p.since) + " · " : "") + p.note_count + (p.note_count === 1 ? " note" : " notes"))));
      out.push(h("ol", { class: "tl" }, (p.entries || []).map(entryNode)));
    }
    show(out);
  } catch (e) { show(errBlock()); }
}

async function viewToday() {
  show(h("div", { class: "muted" }, "Loading…"));
  try {
    const d = await api("GET", "/api/today");
    const out = [h("h1", { class: "title" }, "Today")];
    const em = d.emergencies || [], todos = d.todos || [], qs = d.questions || [], ap = d.appointments || [];
    em.forEach((t) => out.push(emergencyTodoNode(t)));
    if (!em.length && !todos.length && !qs.length && !ap.length) { out.push(h("div", { class: "empty" }, "Nothing for today.")); show(out); return; }
    if (todos.length) out.push(h("h3", { class: "sec" }, "To do"), h("ul", { class: "list" }, todos.map((t) => todoNode(t))));
    if (qs.length) out.push(h("h3", { class: "sec" }, "Questions for you"), h("ul", { class: "list" }, qs.map((q) => questionNode(q, () => setTimeout(viewToday, 900)))));
    if (ap.length) out.push(h("h3", { class: "sec" }, "Coming up"), h("ul", { class: "list" }, ap.map((e) =>
      h("li", { class: "item" }, h("div", { class: "date" }, h("b", null, fmtDate(e.date))), h("div", null, e.what)))));
    show(out);
  } catch (e) { show(errBlock()); }
}

function viewCard() {
  show(h("h1", { class: "title" }, "Doctor card"), h("div", { class: "item" }, "Doctor card comes in the next step."));
}

async function viewNotes() {
  show(h("div", { class: "muted" }, "Loading…"));
  try {
    const list = await api("GET", "/api/notes");
    const out = [h("h1", { class: "title" }, "Notes")];
    if (!list.length) { out.push(h("div", { class: "empty" }, "No notes yet. Tap + After the call.")); show(out); return; }
    const ul = h("ul", { class: "list" });
    for (const n of list) ul.append(noteItem(n));
    out.push(ul); show(out);
  } catch (e) { show(errBlock()); }
}

function noteItem(n) {
  const li = h("li", { class: "item" });
  const chips = h("div", { class: "chips" });
  if (n.emergency) chips.append(h("span", { class: "chip danger" }, "emergency"));
  if (n.entry_count) chips.append(h("span", { class: "chip" }, n.entry_count + (n.entry_count === 1 ? " entry" : " entries")));
  else if (!n.emergency) chips.append(h("span", { class: "chip" }, "nothing medical"));
  const preview = (n.text || "").length > 80 ? n.text.slice(0, 80) + "…" : n.text;
  const head = h("button", { class: "note-head", type: "button", "aria-expanded": "false" },
    h("div", { class: "d" }, fmtDate(n.note_date) + (n.kind === "answer" ? " · answer" : "")), h("div", null, preview), chips);
  const body = h("div", { class: "note-body", hidden: true });
  let loaded = false;
  head.addEventListener("click", async () => {
    const open = head.getAttribute("aria-expanded") !== "true";
    head.setAttribute("aria-expanded", open);
    body.hidden = !open;
    if (open && !loaded) {
      body.replaceChildren(h("div", { class: "muted" }, "Loading…"));
      try {
        const r = await api("GET", "/api/notes/" + n.id);
        loaded = true;
        body.replaceChildren(noteDetail(r, n, li));
      } catch (e) { body.replaceChildren(errBlock()); }
    }
  });
  li.append(head, body);
  return li;
}

function noteDetail(r, n, li) {
  const out = h("div");
  out.append(h("p", { class: "note-text" }, (r.note && r.note.text) || n.text));
  if (r.extraction_error) out.append(h("div", { class: "errblock bad" }, "Couldn't read this note. It's saved; try again from Notes."));
  if (r.emergency) out.append(emergencyNode(r.emergency.text_en, r.emergency.text_zh, r.emergency.source));
  const mini = (title, arr, f) => { if (arr && arr.length) out.append(h("h3", { class: "sec" }, title), h("ul", { class: "mini" }, arr.map((x) => h("li", null, f(x))))); };
  mini("Entries", r.entries, (e) => fmtDate(e.date) + ": " + e.what);
  mini("Questions", r.questions, (q) => q.text + (q.answered_at ? " (answered)" : ""));
  mini("To do", r.todos, (t) => t.text + (t.done_at ? " (done)" : ""));
  const del = h("button", { class: "btn danger", type: "button" }, "Delete");
  del.addEventListener("click", async () => {
    if (!window.confirm("Delete this note and everything added from it?")) return;
    del.disabled = true;
    try { await api("DELETE", "/api/notes/" + n.id); li.remove(); }
    catch (e) { del.disabled = false; del.after(errBlock()); }
  });
  out.append(h("div", { class: "row" }, del));
  return out;
}

/* ----- After the call ----- */
function viewNew() {
  const ta = h("textarea", { id: "note-text", placeholder: "What did Mom tell you? Chinese or English, messy is fine." });
  const dt = h("input", { type: "date", id: "note-date", value: todayISO() });
  const msg = h("div");
  const btn = h("button", { class: "btn", type: "submit" }, "Turn into timeline");
  const form = h("form", { novalidate: true },
    h("h1", { class: "title" }, "After the call"),
    h("label", { class: "lbl", for: "note-text" }, "What did Mom tell you?"), ta,
    h("label", { class: "lbl", for: "note-date" }, "Date of the call"), dt,
    h("div", { class: "row" }, btn), msg);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const text = ta.value.trim();
    if (!text) { msg.replaceChildren(h("div", { class: "errblock", role: "alert" }, "Type what Mom said first.")); ta.focus(); return; }
    btn.disabled = true; btn.textContent = "Reading the note…"; msg.replaceChildren();
    try {
      const r = await api("POST", "/api/notes", { text: text, note_date: dt.value || todayISO() });
      renderResult(r);
    } catch (e) { btn.disabled = false; btn.textContent = "Turn into timeline"; msg.replaceChildren(errBlock()); }
  });
  show(form);
  ta.focus();
}

function renderResult(r) {
  const out = [];
  if (r.emergency && r.emergency.warning !== false) out.push(emergencyNode(r.emergency.text_en, r.emergency.text_zh, r.emergency.source));
  if (r.extraction_error) out.push(h("div", { class: "errblock bad", role: "alert" }, "Couldn't read this note. It's saved; try again from Notes."));
  else if (r.nothing_medical) out.push(h("div", { class: "errblock" }, "Nothing medical in this note. Saved under Notes."));
  const es = r.entries || [], qs = r.questions || [], ts = (r.todos || []).filter((t) => t.kind !== "emergency");
  if (es.length) out.push(h("h3", { class: "sec" }, "Added to timeline"), h("ol", { class: "tl" }, es.map(entryNode)));
  if (qs.length) out.push(h("h3", { class: "sec" }, "Questions for you"), h("ul", { class: "list" }, qs.map((q) => questionNode(q))));
  if (ts.length) out.push(h("h3", { class: "sec" }, "To do"), h("ul", { class: "list" }, ts.map((t) => todoNode(t))));
  out.push(h("div", { class: "row" }, h("a", { class: "btn", href: "#timeline" }, "Done")));
  show(h("h1", { class: "title" }, "After the call"), out);
  window.scrollTo(0, 0);
}

/* ===== router ===== */
const ROUTES = { timeline: viewTimeline, today: viewToday, card: viewCard, notes: viewNotes, "new": viewNew };
function route() {
  let name = (location.hash || "#timeline").slice(1);
  if (!ROUTES[name]) name = "timeline";
  document.querySelectorAll(".tabs a").forEach((a) => {
    const on = a.dataset.tab === name;
    a.classList.toggle("on", on);
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  document.getElementById("fab").hidden = name === "new";
  ROUTES[name]();
}
window.addEventListener("hashchange", route);
if (IS_MOCK) document.title = "First Rounds (mock)";
route();

/* ===== verification checklist (builder, no browser available) =====
 * [x] node --check app.js: syntax OK (see run output in report)
 * [x] static server on 127.0.0.1:8799 serves index.html?mock=1, app.css, app.js (curl 200)
 * [x] All colors/sizes/radii in app.css come from design/design.md tokens
 * [x] Data is inserted via textContent/createTextNode only (no innerHTML)
 * [x] Mock is opt-in: IS_MOCK only when ?mock=1
 * [ ] NOT verified: actual rendering/layout (no browser here); visual match to look.html
 * [ ] NOT verified: FAB position on wide screens, focus ring look, reduced-motion behaviour
 * [ ] NOT verified: any real backend call (shapes follow CONTRACT.md; guesses listed in report)
 * [ ] NOT verified: Google Fonts load (needs network); falls back to system-ui
 * [ ] NOT verified: tap-target sizes in a real device (min-height 44px set in CSS)
 */
