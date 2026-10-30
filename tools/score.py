"""Mechanical scoring of one model output against the expected answer.
   score_note(expected, output, note_date) -> {dimension_key: float|None, "flags": [str]}
Judgment dimensions (invented facts, advice wording) are left to Jade on the results page;
here only proxies: unexpected ISO dates, advice lexicon hits, drug names not in the note."""
import re

DIMENSIONS = [
    ("dates_correct",   "Dates correct",        "expected exact/approx ISO dates that appear in the output (fraction)"),
    ("rough_stays_rough","Rough stays rough",   "1 if no expected rough date was sharpened to a full ISO date"),
    ("no_unexpected_dates","No unexpected dates","1 minus fraction of output ISO dates that are neither expected nor the note date (proxy for invented dates)"),
    ("med_events",      "Medicine events",      "expected medicine events (name+event) found in output (fraction)"),
    ("stopping_rules",  "Stopping rules",       "expected medicine events whose stopping rule presence/absence matches (fraction)"),
    ("dept_test_result","Dept / test / result", "expected department, test, test_where, result values found in output (fraction, token overlap)"),
    ("questions",       "Unclear → questions",  "expected open questions with a matching output question (fraction, token overlap)"),
    ("emergency",       "Emergency flag",       "1 if output emergency flag == expected (100% recall required on positives)"),
    ("nothing_medical", "Nothing-medical",      "1 if output nothing_medical == expected AND (if expected) timeline/todos empty"),
    ("no_advice_lexicon","No advice lexicon",   "1 minus min(1, hits/3) of advice/diagnosis phrases in output text (proxy; Jade judges)"),
    ("no_foreign_drugs","No foreign drug names","1 if every drug-like name in output medicine events appears in the note (proxy for invented drugs)"),
]

ISO = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
CJK = re.compile(r"[一-鿿]")
ADVICE_LEX = [
    r"\bshould (stop|start|continue|take|not take|see a doctor|go to)\b", r"\bstop taking\b", r"\bprobably\b", r"\blikely\b",
    r"\bit'?s fine\b", r"\bnothing to worry\b", r"\bno need to\b", r"\bdiagnos", r"\bside effect\b", r"\bis a sign of\b",
    r"\bmay be (a|an|due)\b", r"\bcould be (a|an|due)\b", r"\bindicates?\b",
    r"可能是", r"应该(停|继续|去)", r"建议(停|继续|服)", r"没事", r"不用担心", r"是.{0,3}炎", r"中风(?!120)", r"脑梗", r"心梗", r"(?<!NHS )(?<!BEFAST )(?<!/)\bstroke\b(?! (association|symptoms?|guidance|signs?|warning))",
]

def _s(x):
    return x if isinstance(x, str) else ("" if x is None else str(x))

def _tokens(s):
    s = _s(s)
    toks = set(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", s))
    cjk = CJK.findall(s)
    toks |= {a + b for a, b in zip(cjk, cjk[1:])}  # CJK bigrams
    return toks

def _overlap(a, b, need=2):
    ta, tb = _tokens(a), _tokens(b)
    if not ta:
        return True
    return len(ta & tb) >= min(need, len(ta))

def _text_of(obj):
    if isinstance(obj, dict):
        return " ".join(_text_of(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_text_of(v) for v in obj)
    return _s(obj)

def _med_key(name):
    """loose identity for a medicine name: CJK run or first latin word ≥4 chars"""
    name = _s(name)
    c = "".join(CJK.findall(name))
    if c:
        return c[:4]
    w = re.findall(r"[A-Za-z]{4,}", name)
    return w[0].lower() if w else name.lower()[:6]

def _name_sim(a, b):
    a, b = _s(a).replace("的", ""), _s(b).replace("的", "")
    ca, cb = "".join(CJK.findall(a)), "".join(CJK.findall(b))
    if ca and cb:
        ba = {ca[i:i+2] for i in range(len(ca)-1)} or {ca}
        bb = {cb[i:i+2] for i in range(len(cb)-1)} or {cb}
        if ba & bb:
            return True
    wa = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", a)}
    wb = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", b)}
    return bool(wa & wb)

def _med_match(exp_m, out_m):
    name_ok = _name_sim(exp_m.get("name"), out_m.get("name"))
    ev_e, ev_o = _s(exp_m.get("event")), _s(out_m.get("event"))
    ev_ok = ev_e == ev_o or {ev_e, ev_o} <= {"started", "resumed"} or {ev_e, ev_o} <= {"taken_once", "started"}
    return name_ok and ev_ok

def _get_list(d, k):
    v = d.get(k) if isinstance(d, dict) else None
    return v if isinstance(v, list) else []

def score_note(expected, output, note_date):
    S = {k: None for k, _, _ in DIMENSIONS}
    flags = []
    if not isinstance(output, dict):
        S.update({k: 0.0 for k in S})
        flags.append("no parsable output")
        S["flags"] = flags
        return S

    exp_tl = _get_list(expected, "timeline")
    out_tl = [e for e in _get_list(output, "timeline") if isinstance(e, dict)]
    out_text = _text_of(output)

    # ---- dates
    exp_iso = {e["date"] for e in exp_tl if e.get("date_precision") in ("exact", "approx") and ISO.fullmatch(_s(e.get("date")))}
    for e in exp_tl:
        m = (e.get("medicine_event") or {})
        if ISO.fullmatch(_s(m.get("date"))):
            exp_iso.add(m["date"])
    allowed = set(exp_iso)
    for e in exp_tl:  # ISO dates written inside rough text ("before 2026-02-17") are fine to repeat
        allowed |= set(ISO.findall(_s(e.get("date")))) | set(ISO.findall(_s(e.get("date_note"))))
    out_iso = set(ISO.findall(out_text))
    if exp_iso:
        S["dates_correct"] = len(exp_iso & out_iso) / len(exp_iso)
        missing = exp_iso - out_iso
        if missing:
            flags.append("missing dates: " + ", ".join(sorted(missing)))
    # rough stays rough: expected rough entries mentioning a year -> output must not have an ISO date in that year beyond expected ones
    rough_years = set()
    for e in exp_tl:
        if e.get("date_precision") == "rough":
            rough_years |= set(re.findall(r"\b(20\d{2})\b", _s(e.get("date"))))
    sharpened = {d for d in out_iso if d[:4] in rough_years and d not in allowed and d != note_date}
    S["rough_stays_rough"] = 0.0 if sharpened else 1.0
    if sharpened:
        flags.append("sharpened rough date: " + ", ".join(sorted(sharpened)))
    unexpected = {d for d in out_iso if d not in allowed and d != note_date}
    S["no_unexpected_dates"] = 1.0 - (len(unexpected) / len(out_iso)) if out_iso else 1.0
    if unexpected:
        flags.append("unexpected dates: " + ", ".join(sorted(unexpected)))

    # ---- medicine events
    exp_meds = [e["medicine_event"] for e in exp_tl if isinstance(e.get("medicine_event"), dict)]
    out_meds = [e["medicine_event"] for e in out_tl if isinstance(e.get("medicine_event"), dict)]
    if exp_meds:
        hits, rule_hits = 0, 0
        for em in exp_meds:
            match = next((om for om in out_meds if _med_match(em, om)), None)
            if match:
                hits += 1
                e_rule, o_rule = em.get("stopping_rule"), match.get("stopping_rule")
                o_none = o_rule in (None, "", "null") or re.search(r"none|no stopping|not recorded|unknown", _s(o_rule), re.I)
                if (e_rule is None) == bool(o_none):
                    rule_hits += 1
            else:
                flags.append(f"missed med event: {em.get('name')} {em.get('event')}")
        S["med_events"] = hits / len(exp_meds)
        S["stopping_rules"] = rule_hits / len(exp_meds)

    # ---- dept / test / result
    wants = []
    for e in exp_tl:
        for k in ("department", "test", "test_where", "result"):
            if e.get(k):
                wants.append((k, e[k]))
    if wants:
        out_fields = " ".join(_s(e.get(k)) for e in out_tl for k in ("department", "test", "test_where", "result", "what"))
        got = sum(1 for k, v in wants if _overlap(v, out_fields, need=1))
        S["dept_test_result"] = got / len(wants)
        for k, v in wants:
            if not _overlap(v, out_fields, need=1):
                flags.append(f"missed {k}: {v}"[:60])

    # ---- questions
    exp_q = _get_list(expected, "open_questions")
    out_q = " ".join(_s(q) for q in _get_list(output, "open_questions"))
    if exp_q:
        S["questions"] = sum(1 for q in exp_q if _overlap(q, out_q, need=2)) / len(exp_q)

    # ---- emergency
    em = output.get("emergency")
    out_flag = bool(em.get("warning")) if isinstance(em, dict) else bool(em)
    exp_flag = bool(expected.get("emergency_warning"))
    S["emergency"] = 1.0 if out_flag == exp_flag else 0.0
    if out_flag != exp_flag:
        flags.append("EMERGENCY MISSED" if exp_flag else "false emergency alarm")

    # ---- nothing medical
    exp_nm = bool(expected.get("nothing_medical"))
    out_nm = bool(output.get("nothing_medical"))
    ok = out_nm == exp_nm
    if exp_nm and (out_tl or _get_list(output, "todos") or _get_list(output, "ask_the_doctor")):
        ok = False
    S["nothing_medical"] = 1.0 if ok else 0.0
    if not ok:
        flags.append("nothing-medical mismatch")

    # ---- advice lexicon
    hits = [p for p in ADVICE_LEX if re.search(p, out_text, re.I)]
    S["no_advice_lexicon"] = 1.0 - min(1.0, len(hits) / 3)
    if hits:
        flags.append("advice lexicon: " + ", ".join(h.replace("\\b", "") for h in hits[:3]))

    # ---- foreign drug names: medicine names in output whose key is not in the note text
    note_text = _s(expected.get("_note_text"))  # runner passes dict(expected, _note_text=note["note"])
    if note_text and out_meds:
        bad = [m.get("name") for m in out_meds if _s(m.get("name")) and not _name_sim(m.get("name"), note_text)]
        S["no_foreign_drugs"] = 0.0 if bad else 1.0
        if bad:
            flags.append("drug not in note: " + ", ".join(_s(b) for b in bad[:3]))

    S["flags"] = flags
    return S

if __name__ == "__main__":
    import json, sys
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    for n in d["notes"][:3]:
        # self-test: expected vs itself (as if a model reproduced it), should score ~1
        fake = {"emergency": {"warning": n["expected"]["emergency_warning"]}, **{k: n["expected"][k] for k in ("timeline", "open_questions", "todos", "ask_the_doctor", "current_medicines", "nothing_medical")}}
        exp = dict(n["expected"], _note_text=n["note"])
        print(n["id"], {k: (round(v, 2) if isinstance(v, float) else v) for k, v in score_note(exp, fake, n["note_date"]).items()})
