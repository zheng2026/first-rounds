#!/usr/bin/env python3
"""Plain-code checks on tests/notes.json: date arithmetic, format, coverage.
   python3 -I tools/check_notes.py tests/notes.json
Exit 1 on any FAIL. Date assertions are hand-written per note (the relative phrases
in the notes are the thing under test, so they are listed here explicitly)."""
import json, re, sys, datetime as dt
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from notes_md import coverage, MANDATORY, DATE_PHR, MED_EV, UNCLEAR

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
D = lambda s: dt.date.fromisoformat(s)
fails, warns = [], []
def fail(m): fails.append(m)
def warn(m): warns.append(m)

def last_weekday_prev_week(ref, wd):
    """Chinese 上周X: the given weekday (0=Mon) in the calendar week before ref's week."""
    monday = ref - dt.timedelta(days=ref.weekday())
    return monday - dt.timedelta(days=7) + dt.timedelta(days=wd)
def next_weekday_next_week(ref, wd):
    monday = ref - dt.timedelta(days=ref.weekday())
    return monday + dt.timedelta(days=7) + dt.timedelta(days=wd)
def most_recent_weekday(ref, wd):
    delta = (ref.weekday() - wd) % 7 or 7
    return ref - dt.timedelta(days=delta)

d = json.load(open(sys.argv[1], encoding="utf-8"))
notes = {n["id"]: n for n in d["notes"]}
def entry(nid, substr):
    for e in notes[nid]["expected"]["timeline"]:
        if substr.lower() in (e.get("what") or "").lower():
            return e
    fail(f"{nid}: no timeline entry containing '{substr}'"); return {}
def med(nid, substr, event):
    for e in notes[nid]["expected"]["timeline"]:
        m = e.get("medicine_event")
        if m and substr in (m.get("name") or "") and m.get("event") == event:
            return m
    fail(f"{nid}: no medicine event {event} for '{substr}'"); return {}

# ---------------------------------------------------------------- 1. date arithmetic
# (note id, phrase in note, expected ISO date, expected precision, locator)
nd = lambda i: D(notes[i]["note_date"])
checks = [
  ("n01", "上周二",  last_weekday_prev_week(nd("n01"), 1), "approx", entry("n01", "Visited community hospital")),
  ("n01", "前天",    nd("n01") - dt.timedelta(days=2), "exact", entry("n01", "only once")),
  ("n01", "昨天",    nd("n01") - dt.timedelta(days=1), "exact", entry("n01", "Forgot")),
  ("n01", "下周三",  next_weekday_next_week(nd("n01"), 2), "exact", entry("n01", "Follow-up dental")),
  ("n02", "2 weeks", nd("n02") - dt.timedelta(days=14), "approx", entry("n02", "Ankles")),
  ("n02", "June 1",  D("2026-06-01"), "exact", entry("n02", "ran out")),
  ("n02", "this morning", nd("n02"), "exact", entry("n02", "Home blood pressure")),
  ("n05", "an hour ago", nd("n05"), "exact", entry("n05", "Sudden severe dizziness")),
  ("n06", "上周六",  last_weekday_prev_week(nd("n06"), 5), "approx", entry("n06", "Slipped")),
  ("n09", "jan 17",  D("2026-01-17"), "exact", entry("n09", "Skipped blood pressure pills (travelling")),
  ("n09", "dec 2",   D("2025-12-02"), "exact", entry("n09", "Checkup")),
  ("n09", "3 months", D("2026-03-02"), "approx", entry("n09", "Follow-up checkup due")),
  ("n10", "十天前",  nd("n10") - dt.timedelta(days=10), "approx", entry("n10", "Acid reflux began")),
  ("n13", "last tuesday", most_recent_weekday(nd("n13"), 1), "approx", entry("n13", "Switched sleeping")),
  ("n14", "下周二",  next_weekday_next_week(nd("n14"), 1), "exact", entry("n14", "Cardiology follow-up appointment")),
  ("n14", "11月3号", D("2026-11-03"), "exact", entry("n14", "Cardiology follow-up appointment")),
  ("n15", "11/2",    D("2026-11-02"), "exact", entry("n15", "Dentist visit")),
  ("r01", "for a week", nd("r01") - dt.timedelta(days=7), "approx", entry("r01", "Molars started")),
]
for nid, phrase, want, prec, e in checks:
    if not e: continue
    got = e.get("date")
    if got != want.isoformat():
        fail(f"{nid} '{phrase}': expected {want} got {got}")
    if e.get("date_precision") != prec:
        fail(f"{nid} '{phrase}': precision expected {prec} got {e.get('date_precision')}")
# medicine-event dates that mirror an entry
m = med("n01", "甲硝唑", "started");  m and m.get("date") is not None and fail("n01 med start must be undated (prescription date != first dose)")
m = med("n13", "sleeping", "switched"); m and m.get("date") != most_recent_weekday(nd("n13"), 1).isoformat() and fail("n13 med switch date")

# rough dates must stay rough; exact must be ISO; nothing in the future except appointments
FUTURE_OK = re.compile(r"appointment|follow-up|复查|due|planned|intended", re.I)
for nid, n in notes.items():
    ref = D(n["note_date"])
    for i, e in enumerate(n["expected"]["timeline"]):
        date, prec, what = e.get("date"), e.get("date_precision"), e.get("what") or ""
        if prec == "rough" and date and ISO.match(date):
            fail(f"{nid} tl{i}: rough date written as full ISO {date}")
        if prec == "exact" and not (date and ISO.match(date)):
            fail(f"{nid} tl{i}: exact precision but date={date!r}")
        if prec == "unknown" and date:
            fail(f"{nid} tl{i}: precision unknown but date={date!r}")
        if date and ISO.match(date) and D(date) > ref and not FUTURE_OK.search(what):
            fail(f"{nid} tl{i}: future date {date} on non-appointment entry")
        if re.search(r"\b2020-01-01\b|^2020$", date or ""):
            fail(f"{nid} tl{i}: 'about 2020' sharpened: {date}")
        mv = e.get("medicine_event") or {}
        if mv.get("date_precision") == "rough" and mv.get("date") and ISO.match(mv["date"]):
            fail(f"{nid} tl{i}: rough medicine date written as ISO")

# ---------------------------------------------------------------- 2. format
MED_EVENTS = {"started", "stopped", "skipped", "switched", "taken_once", "resumed"}
EXP_KEYS = {"timeline", "open_questions", "todos", "history_question", "ask_the_doctor", "current_medicines",
            "emergency_warning", "nothing_medical", "must_not"}
seen = set()
for n in d["notes"]:
    nid = n.get("id")
    if not nid or nid in seen: fail(f"duplicate/missing id {nid!r}")
    seen.add(nid)
    if not ISO.match(n.get("note_date", "")): fail(f"{nid}: note_date not ISO")
    if n.get("group") not in ("invented", "real"): fail(f"{nid}: bad group")
    if n.get("language") not in ("zh", "en", "mixed"): fail(f"{nid}: bad language")
    if not n.get("note", "").strip(): fail(f"{nid}: empty note")
    if not n.get("covers"): fail(f"{nid}: no covers tags")
    x = n.get("expected", {})
    missing = EXP_KEYS - set(x)
    if missing: fail(f"{nid}: expected missing keys {sorted(missing)}")
    for k in ("emergency_warning", "nothing_medical"):
        if not isinstance(x.get(k), bool): fail(f"{nid}: {k} not bool")
    if x.get("emergency_warning") and not x.get("emergency_reason"): fail(f"{nid}: emergency true but no emergency_reason")
    if x.get("nothing_medical") and (x["timeline"] or x["todos"] or x["ask_the_doctor"]): fail(f"{nid}: nothing_medical but has medical output")
    for i, e in enumerate(x.get("timeline", [])):
        for k in ("date", "date_precision", "what"):
            if k not in e: fail(f"{nid} tl{i}: missing field {k}")
        if e.get("date_precision") not in ("exact", "approx", "rough", "unknown"): fail(f"{nid} tl{i}: bad precision")
        mv = e.get("medicine_event")
        if mv:
            if not mv.get("name"): fail(f"{nid} tl{i}: medicine without name")
            if mv.get("event") not in MED_EVENTS: fail(f"{nid} tl{i}: bad medicine event {mv.get('event')!r}")
            if "stopping_rule" not in mv: fail(f"{nid} tl{i}: medicine without stopping_rule key")
    # link to a real note: every entry lives under exactly one note (structural) — verify id-prefixed refs if any
    for e in x.get("timeline", []):
        src = e.get("source_note")
        if src and src != nid: fail(f"{nid}: entry links to another note {src}")

# ---------------------------------------------------------------- 3. coverage
known_tags = {t for spec in (MANDATORY, DATE_PHR, MED_EV, UNCLEAR) for v in spec.values() for t in v}
for n in d["notes"]:
    for t in n["covers"]:
        if t not in known_tags: warn(f"{n['id']}: tag '{t}' not in any coverage spec (descriptive only)")
recomputed = coverage(d["notes"])
if recomputed != d.get("coverage"):
    fail("stored coverage != recomputed coverage (run: notes_md.py coverage)")
for case, ids in recomputed["mandatory_cases"].items():
    if not ids: fail(f"coverage: mandatory case uncovered: {case}")
    for i in ids:
        if i not in notes: fail(f"coverage references unknown note {i}")
em_ids = recomputed["emergency_true_ids"]
if not em_ids: fail("no emergency-positive notes")

# ---------------------------------------------------------------- report
print(f"notes: {len(d['notes'])} | date checks: {len(checks)} | fails: {len(fails)} | warns: {len(warns)}")
for f in fails: print("FAIL", f)
if warns: print(f"info: {len(warns)} descriptive-only covers tags (not in coverage spec)")
sys.exit(1 if fails else 0)
