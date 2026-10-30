#!/usr/bin/env python3
"""First Rounds test-set tool.

  python3 -I tools/notes_md.py export tests/notes.json tests/notes.md   # JSON -> editable markdown
  python3 -I tools/notes_md.py import tests/notes.md tests/notes.json   # markdown -> JSON (meta/rubric kept, coverage recomputed)
  python3 -I tools/notes_md.py coverage tests/notes.json tests/coverage.md

Markdown is the file Jade edits. JSON is what the runner reads. Keep headings and the
"- key: value" sub-bullet shapes; free text inside them is yours.
"""
import json, re, sys, collections

EMPTY = "—"

# ---------------------------------------------------------------- export
def _v(x):
    return EMPTY if x in (None, "", [], {}) else x

def _date_str(e):
    d = _v(e.get("date"))
    p = e.get("date_precision")
    return f"{d} ({p})" if p and d != EMPTY else (f"{d}" if d != EMPTY else f"{EMPTY} ({p})" if p else EMPTY)

def _med_line(m):
    parts = [m.get("name") or EMPTY, m.get("event") or EMPTY]
    d = m.get("date")
    dp = m.get("date_precision")
    parts.append((f"{d} ({dp})" if dp else str(d)) if d else EMPTY)
    for k in ("dose", "rule", "reason", "from", "to", "detail", "note"):
        src = "stopping_rule" if k == "rule" else k
        val = m.get(src)
        if val not in (None, ""):
            parts.append(f"{k}: {val}")
    if m.get("stopping_rule") is None and "rule" not in " ".join(parts):
        parts.append("rule: none recorded")
    return " | ".join(str(p) for p in parts)

def export(d):
    out = ["# First Rounds — test notes (edit THIS file; `tools/notes_md.py import` writes it back to notes.json)", "",
           "How to edit: rewrite any `Note` text freely. Under each note, every bullet is part of the expected answer — fix, add or delete bullets.",
           "Keep the `###` headings and the `- key: value` shapes. `—` means empty. Dates: `YYYY-MM-DD (exact|approx|rough)` or free text `(rough)`.",
           "Medicine lines: `name | event | date (precision) | dose: … | rule: … | reason: … | from: … | to: … | detail: … | note: …` (event = started/stopped/skipped/switched/taken_once/resumed).",
           "To drop a note, delete its whole `##` section. Don't edit the `##` header line except the date.", ""]
    for n in d["notes"]:
        x = n["expected"]
        out.append(f"## {n['id']} · {n['note_date']} · {n['language']} · {n['problem']}")
        out.append("")
        out.append("### Note")
        out.append(n["note"].strip())
        out.append("")
        out.append("### Timeline")
        if not x["timeline"]:
            out.append(f"- {EMPTY}")
        for e in x["timeline"]:
            out.append(f"- **{_date_str(e)}** — {e.get('what') or EMPTY}")
            for key, label in (("date_note", "date note"), ("time_note", "time note"), ("department", "dept"),
                               ("test", "test"), ("test_where", "where"), ("result", "result"),
                               ("doctor_instruction", "doctor said"), ("previously_used", "previously used")):
                if e.get(key):
                    out.append(f"  - {label}: {e[key]}")
            if e.get("medicine_event"):
                out.append(f"  - medicine: {_med_line(e['medicine_event'])}")
            if e.get("helps"):
                out.append(f"  - helps: {'; '.join(e['helps'])}")
            if e.get("worsens"):
                out.append(f"  - worsens: {'; '.join(e['worsens'])}")
        out.append("")
        for key, title in (("open_questions", "Open questions"), ("todos", "To-dos"), ("ask_the_doctor", "Ask the doctor"),
                           ("current_medicines", "Current medicines"), ("must_not", "Must not")):
            out.append(f"### {title}")
            out.extend([f"- {s}" for s in x.get(key) or []] or [f"- {EMPTY}"])
            out.append("")
        out.append("### History question")
        out.append(x.get("history_question") or EMPTY)
        out.append("")
        out.append("### Flags")
        em = x.get("emergency_warning")
        out.append(f"- emergency: {'yes' if em else 'no'}" + (f" — {x['emergency_reason']}" if em and x.get("emergency_reason") else ""))
        out.append(f"- nothing medical: {'yes' if x.get('nothing_medical') else 'no'}")
        if x.get("emergency_note"):
            out.append(f"- emergency note: {x['emergency_note']}")
        out.append("")
        out.append(f"<!-- covers: {', '.join(n['covers'])} | group: {n['group']} -->")
        out.append("")
    return "\n".join(out) + "\n"

# ---------------------------------------------------------------- import
def _none(s):
    s = s.strip()
    return None if s in (EMPTY, "", "null", "none", "None") else s

DATE_RE = re.compile(r"^(.*?)\s*\((exact|approx|rough|unknown)\)\s*$")

def _parse_date(s):
    s = s.strip()
    m = DATE_RE.match(s)
    if m:
        return _none(m.group(1)), m.group(2)
    return _none(s), None

def _parse_med(line):
    parts = [p.strip() for p in line.split("|")]
    m = {"name": _none(parts[0]) if parts else None, "event": _none(parts[1]) if len(parts) > 1 else None}
    if len(parts) > 2:
        d, p = _parse_date(parts[2])
        m["date"] = d
        if p:
            m["date_precision"] = p
    m["stopping_rule"] = None
    for p in parts[3:]:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        k, v = k.strip(), v.strip()
        if k == "rule":
            m["stopping_rule"] = None if v in ("none recorded", EMPTY, "") else v
        elif k in ("dose", "reason", "from", "to", "detail", "note"):
            m[k] = v
    return m

def _bullets(lines):
    items = []
    for l in lines:
        if l.startswith("- "):
            s = l[2:].strip()
            if s != EMPTY:
                items.append(s)
    return items

def import_md(text, base):
    notes = []
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    for sec in sections:
        header, _, body = sec.partition("\n")
        hid, hdate, hlang, hprob = [p.strip() for p in header.split("·")]
        cov = re.search(r"<!-- covers: (.*?) \| group: (.*?) -->", body)
        covers = [c.strip() for c in cov.group(1).split(",")] if cov else []
        group = cov.group(2).strip() if cov else "invented"
        body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
        parts = re.split(r"^### ", body, flags=re.M)[1:]
        sub = {}
        for p in parts:
            t, _, b = p.partition("\n")
            sub[t.strip()] = [l.rstrip() for l in b.strip("\n").split("\n")]
        tl = []
        cur = None
        for l in sub.get("Timeline", []):
            if l.startswith("- "):
                s = l[2:].strip()
                if s == EMPTY:
                    continue
                mm = re.match(r"\*\*(.*?)\*\*\s*—\s*(.*)$", s)
                if not mm:
                    raise SystemExit(f"{hid}: bad timeline line: {l}")
                d, p = _parse_date(mm.group(1))
                cur = {"date": d, "date_precision": p or ("exact" if d and re.match(r"^\d{4}-\d{2}-\d{2}$", d) else "unknown" if d is None else "rough"),
                       "what": _none(mm.group(2))}
                tl.append(cur)
            elif l.startswith("  - ") and cur is not None:
                k, _, v = l[4:].partition(":")
                k, v = k.strip(), v.strip()
                key = {"date note": "date_note", "time note": "time_note", "dept": "department", "test": "test",
                       "where": "test_where", "result": "result", "doctor said": "doctor_instruction",
                       "previously used": "previously_used"}.get(k)
                if key:
                    cur[key] = _none(v)
                elif k == "medicine":
                    cur["medicine_event"] = _parse_med(v)
                elif k in ("helps", "worsens"):
                    cur[k] = [s.strip() for s in v.split(";") if s.strip() and s.strip() != EMPTY]
        flags = {}
        for l in sub.get("Flags", []):
            k, _, v = l[2:].partition(":")
            flags[k.strip()] = v.strip()
        em_raw = flags.get("emergency", "no")
        em = em_raw.lower().startswith("yes")
        em_reason = em_raw.split("—", 1)[1].strip() if "—" in em_raw else None
        hq = "\n".join(sub.get("History question", [])).strip()
        exp = {
            "timeline": tl,
            "open_questions": _bullets(sub.get("Open questions", [])),
            "todos": _bullets(sub.get("To-dos", [])),
            "history_question": _none(hq),
            "ask_the_doctor": _bullets(sub.get("Ask the doctor", [])),
            "current_medicines": _bullets(sub.get("Current medicines", [])),
            "emergency_warning": em,
            "nothing_medical": flags.get("nothing medical", "no").lower().startswith("yes"),
            "must_not": _bullets(sub.get("Must not", [])),
        }
        if em and em_reason:
            exp["emergency_reason"] = em_reason
        if flags.get("emergency note"):
            exp["emergency_note"] = flags["emergency note"]
        notes.append({"id": hid, "group": group, "note_date": hdate, "language": hlang, "problem": hprob,
                      "note": "\n".join(sub.get("Note", [])).strip(), "covers": covers, "expected": exp})
    out = {k: v for k, v in base.items() if k not in ("notes", "coverage")}
    out["notes"] = notes
    out["coverage"] = coverage(notes)
    return out

# ---------------------------------------------------------------- coverage
MANDATORY = {
  "A multi-department journey, mostly normal results": ["multi-department-journey"],
  "B 'the scan was fine' without which scan": ["scan-unspecified"],
  "C sudden/severe symptoms -> urgent care": ["emergency-true"],
  "D medicine stopped because she felt better": ["med-stopped-felt-better"],
  "E list of supplements / 保健品 / 中药": ["supplements-list", "current-medicines-list", "supplements"],
  "F rough date (about 2020 etc.)": ["rough-date-about-2020", "date-before-new-year-zh", "date-before-new-year-ambiguous"],
  "G upcoming appointment": ["appointment-upcoming", "appointment-upcoming-unbooked"],
  "H note with nothing medical": ["nothing-medical"],
  "I appointment -> history question (additions #1)": ["history-question"],
  "J stop-check, rule recorded (additions #7)": ["stop-check-rule-recorded"],
  "K stop-check, no rule recorded (additions #7)": ["stop-check-no-rule"],
  "L department / test / result captured (additions #3)": ["department-captured", "test-and-where", "normal-results"],
  "M helps / worsens (additions #8)": ["helps-worsens"],
  "N emergency: resolved episode still triggers (brief must-pass)": ["emergency-resolved"],
  "O emergency: negative control (toothache / tired) must NOT trigger": ["emergency-false-control"],
}
DATE_PHR = {"'10 days ago'": ["date-10-days-ago"],
            "'last Tuesday' (zh 上周二 / en)": ["date-last-tuesday-zh", "date-last-tuesday-en", "date-last-saturday-zh"],
            "'about 2020'": ["rough-date-about-2020"],
            "'before New Year'": ["date-before-new-year-zh", "date-before-new-year-ambiguous"],
            "exact dates": ["date-exact"],
            "month-level ('in April', 'last month')": ["date-month-level", "date-last-month"]}
MED_EV = {"started": ["med-started"], "stopped because felt better": ["med-stopped-felt-better"], "skipped": ["med-skipped"],
          "switched brands": ["med-switched"], "taken once / extra": ["med-taken-once"], "stopped on family's request": ["med-stopped-by-family"]}
UNCLEAR = {"'one of her teeth'": ["unclear-which-tooth"],
           "'the pink pills' / unnamed medicine": ["unclear-pink-pills", "unclear-which-pill", "unclear-which-brand", "unclear-which-product"],
           "'the scan'": ["scan-unspecified"]}

def coverage(notes):
    idx = collections.defaultdict(list)
    for n in notes:
        for t in n["covers"]:
            idx[t].append(n["id"])
    tab = lambda spec: {k: sorted({i for t in v for i in idx.get(t, [])}) for k, v in spec.items()}
    byp, byl = collections.defaultdict(list), collections.defaultdict(list)
    for n in notes:
        byp[n["problem"]].append(n["id"]); byl[n["language"]].append(n["id"])
    return {"mandatory_cases": tab(MANDATORY), "problem": dict(byp), "language": dict(byl), "date_phrasing": tab(DATE_PHR),
            "medicine_events": tab(MED_EV), "unclear_details": tab(UNCLEAR),
            "emergency_true_ids": [n["id"] for n in notes if n["expected"]["emergency_warning"]],
            "nothing_medical_ids": [n["id"] for n in notes if n["expected"]["nothing_medical"]]}

def coverage_md(d):
    c = d["coverage"]; notes = d["notes"]
    def tbl(title, m):
        rows = [f"### {title}", "", "| case | notes |", "|---|---|"] + [f"| {k} | {', '.join(v) if v else '**MISSING**'} |" for k, v in m.items()]
        return "\n".join(rows) + "\n"
    inv = sum(1 for n in notes if n["group"] == "invented"); real = len(notes) - inv
    L = ["# Test-set coverage (generated from tests/notes.json — do not edit)", "",
         f"{len(notes)} notes: {inv} invented + {real} real.", ""]
    for t, m in (("Mandatory cases", c["mandatory_cases"]), ("Problem", c["problem"]), ("Language", c["language"]),
                 ("Date phrasing", c["date_phrasing"]), ("Medicine events", c["medicine_events"]), ("Unclear details", c["unclear_details"])):
        L.append(tbl(t, m))
    L += ["### Flags", "", f"- emergency_warning = true: {', '.join(c['emergency_true_ids'])}  (must be 100% recall)",
          f"- nothing_medical = true: {', '.join(c['nothing_medical_ids'])}", "", "### One-line index", "",
          "| id | date | lang | problem | note (first 60 chars) |", "|---|---|---|---|---|"]
    L += [f"| {n['id']} | {n['note_date']} | {n['language']} | {n['problem']} | {n['note'][:60].replace('|','/').replace(chr(10),' ')}… |" for n in notes]
    return "\n".join(L) + "\n"

# ---------------------------------------------------------------- main
if __name__ == "__main__":
    cmd, src, dst = sys.argv[1:4]
    if cmd == "export":
        d = json.load(open(src, encoding="utf-8"))
        open(dst, "w", encoding="utf-8").write(export(d))
        print(f"exported {len(d['notes'])} notes -> {dst}")
    elif cmd == "import":
        base = json.load(open(dst, encoding="utf-8"))
        d = import_md(open(src, encoding="utf-8").read(), base)
        d["meta"]["status"] = "imported from notes.md"
        json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        miss = [k for k, v in d["coverage"]["mandatory_cases"].items() if not v]
        print(f"imported {len(d['notes'])} notes -> {dst}; missing mandatory: {miss or 'none'}")
    elif cmd == "coverage":
        d = json.load(open(src, encoding="utf-8"))
        d["coverage"] = coverage(d["notes"])
        json.dump(d, open(src, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open(dst, "w", encoding="utf-8").write(coverage_md(d))
        print(f"coverage -> {dst}")
    else:
        raise SystemExit(__doc__)
