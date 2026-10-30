"""Doctor card: English built from the DB by code; Chinese rendered by one model call; wording variants spliced in by code."""
import datetime as dt
import hashlib
import json
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from . import db, extract as ex
from .stopcheck import DURATION, name_sim
from .extract import prompts

router = APIRouter()
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RULE_SKEL = {"title": "", "history": [], "tests": [], "medicines": [], "med_events": [], "helps": [], "worsens": [], "ask": []}


def _s(x):
    return "" if x is None else str(x).strip()


PROBLEM_ZH = {"all": "全部", "teeth": "牙齿", "blood pressure": "血压", "heart": "心脏", "chest": "胸口", "stomach": "肠胃", "sleep": "睡眠",
              "dizziness": "头晕", "skin": "皮肤", "joints": "关节", "fall": "摔倒", "eyes": "眼睛", "other": "其他"}

EVENT_ZH = {"started": "开始吃", "stopped": "停了", "skipped": "漏吃", "switched": "换了", "taken_once": "吃了一次", "resumed": "重新开始吃", "continued": "继续吃", "prescribed": "开了"}
CJK = re.compile(r"[\u4e00-\u9fff]")

def zh_date_text(t):
    """Code-formatted Chinese dates so the model never touches them."""
    t = _s(t).strip()
    if not t or t == "date unknown":
        return "日期不详"
    m = re.match(r"^(about |around |大约|约)?\s*(\d{4})-(\d{2})-(\d{2})$", t, re.I)
    if m:
        return ("大约" if m.group(1) else "") + "%d年%d月%d日" % (int(m.group(2)), int(m.group(3)), int(m.group(4)))
    m = re.match(r"^(about |around |大约|约)?\s*(\d{4})-(\d{2})$", t, re.I)
    if m:
        return ("大约" if m.group(1) else "") + "%d年%d月" % (int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(about |around |大约|约)?\s*(\d{4})$", t, re.I)
    if m:
        return "大约%s年" % m.group(2)
    t = re.sub(r"^before ", "", t)
    return t.replace("about ", "大约").replace("Spring Festival", "春节").replace("New Year", "新年")

def zh_fix_dates_events(en, zh):
    for sec in ("history", "tests", "med_events"):
        for a, b in zip(en.get(sec, []), zh.get(sec, [])):
            b["date_text"] = zh_date_text(a.get("date_text"))
            if sec == "med_events":
                b["event"] = EVENT_ZH.get(a.get("event", ""), a.get("event", ""))
                b["name"] = a.get("name", b.get("name", ""))  # names verbatim
    return zh

def _chinese_enough(en, zh):
    """Reject a rendering where the model left free text in English (any field, any section)."""
    total = hits = 0
    for sec in ("history", "tests", "medicines", "med_events", "ask", "helps", "worsens"):
        for a, b in zip(en.get(sec, []), zh.get(sec, [])):
            pairs = [(a, b)] if isinstance(a, str) else [(a.get(k), b.get(k)) for k in a if k not in ("date_text", "name", "kind", "event")]
            for src, out in pairs:
                src, out = _s(src), _s(out)
                if len(re.findall(r"[A-Za-z]", src)) < 6 or re.fullmatch(r"[A-Za-z0-9 ]+", src.strip()):
                    continue  # too short, or a bare product/brand name that stays as is
                total += 1
                if CJK.search(out):
                    hits += 1
    return total == 0 or hits / total >= 0.85

def zh_title(problem):
    t = dt.date.today()
    return "妈妈的就诊卡 · %s · %d年%d月%d日" % (PROBLEM_ZH.get(problem, problem), t.year, t.month, t.day)

def date_text(date, precision):
    d = _s(date)
    if not d:
        return "date unknown"
    p = _s(precision).lower()
    if p == "approx" and not d.lower().startswith(("about", "around", "大约", "约")):
        return "about " + d
    return d  # exact -> ISO; rough -> stored text


def _json_list(x):
    try:
        v = json.loads(x or "[]")
        return [_s(i) for i in v if _s(i)] if isinstance(v, list) else []
    except Exception:
        return []


def _dedupe(items):
    seen, out = set(), []
    for i in items:
        k = i.lower()
        if i and k not in seen:
            seen.add(k)
            out.append(i)
    return out


def _has_rule(name, rows):
    for r in rows:
        if not name_sim(r["med_name"], name):
            continue
        if _s(r["med_rule"]):
            return True
        for f in ("med_dose", "what", "source"):
            if DURATION.search(_s(r[f])):
                return True
    return False


def build_card_en(conn, problem="all"):
    problem = _s(problem) or "all"
    q = "SELECT * FROM entries" + ("" if problem == "all" else " WHERE problem=?") + " ORDER BY sort_key, id"
    rows = conn.execute(q, () if problem == "all" else (problem,)).fetchall()
    pre = (lambda r: "[%s] " % _s(r["problem"])) if problem == "all" else (lambda r: "")
    card = {"title": "Doctor card · %s · %s" % (problem, dt.date.today().isoformat()),
            "history": [], "tests": [], "medicines": [], "med_events": [], "helps": [], "worsens": [], "ask": []}
    med_rows = [r for r in rows if _s(r["med_name"])]
    for r in rows:
        dtx = date_text(r["date"], r["date_precision"])
        if _s(r["test"]):
            card["tests"].append({"date_text": dtx, "test": pre(r) + _s(r["test"]), "where": _s(r["test_where"]),
                                  "result": _s(r["result"])})
        elif not _s(r["med_name"]):
            card["history"].append({"date_text": dtx, "text": pre(r) + _s(r["what"])})
    for r in med_rows:
        d = _s(r["med_date"]) or _s(r["date"])
        card["med_events"].append({"date_text": date_text(d, r["date_precision"]), "name": _s(r["med_name"]),
                                   "event": _s(r["med_event"]), "rule": _s(r["med_rule"]), "reason": _s(r["med_reason"])})
    seen_ev, deduped = {}, []
    for e in card["med_events"]:
        k = (e["name"].lower(), e["event"])
        if k in seen_ev:
            j = seen_ev[k]
            if deduped[j]["date_text"] == "date unknown" and e["date_text"] != "date unknown":
                deduped[j] = e
            continue
        seen_ev[k] = len(deduped)
        deduped.append(e)
    card["med_events"] = deduped
    # helps / worsens
    for r in rows:
        card["helps"] += _json_list(r["helps_json"])
        card["worsens"] += _json_list(r["worsens_json"])
    card["helps"], card["worsens"] = _dedupe(card["helps"]), _dedupe(card["worsens"])

    # medicines: groups by lowercase name, in order of first appearance
    groups = {}
    for r in med_rows:
        groups.setdefault(_s(r["med_name"]).lower(), []).append(r)

    def detail_of(rs):
        bits = []
        dose = next((_s(x["med_dose"]) for x in reversed(rs) if _s(x["med_dose"])), "")
        rule = next((_s(x["med_rule"]) for x in reversed(rs) if _s(x["med_rule"])), "")
        since = next((_s(x["med_date"]) or _s(x["date"]) for x in rs if x["med_event"] == "started"), "")
        if dose: bits.append(dose)
        if rule: bits.append(rule)
        if since: bits.append("since " + since)
        return "; ".join(bits)

    stopped_names = {k for k, rs in groups.items() if rs[-1]["med_event"] == "stopped"}
    nid = rows and {r["note_id"] for r in rows}
    cm = None
    for n in conn.execute("SELECT DISTINCT note_id FROM current_medicines ORDER BY note_id DESC"):
        if problem == "all" or n[0] in nid:
            cm = n[0]
            break
    listed = []
    if cm is not None:
        for m in conn.execute("SELECT text FROM current_medicines WHERE note_id=? ORDER BY id", (cm,)):
            t = _s(m["text"]); tl = t.lower()
            if any(k in tl for k in stopped_names) or "stopped" in tl or "停" in t:
                continue
            hit = [k for k in groups if k in tl]
            card["medicines"].append({"name": t, "detail": detail_of(groups[hit[0]]) if hit else ""})
            listed.append(tl)
    for k, rs in groups.items():
        if k in stopped_names or any(k in t for t in listed) or any(x["med_event"] == "stopped" for x in rs):
            continue
        if any(x["med_event"] in ("started", "resumed", "continued") for x in rs):
            card["medicines"].append({"name": _s(rs[0]["med_name"]), "detail": detail_of(rs)})
    if problem == "all":
        for e, r in zip(card["med_events"], med_rows):
            e["name"] = pre(r) + e["name"]

    # ask
    qa = "SELECT text FROM ask_doctor" + ("" if problem == "all" else " WHERE problem=?") + " ORDER BY id"
    notes = _dedupe([_s(x["text"]) for x in conn.execute(qa, () if problem == "all" else (problem,))])
    card["ask"] = [{"text": t, "kind": "note"} for t in notes]
    # stop-rule question: only for medicines she is still taking (started, not later stopped), and only real medicines
    NOT_MED = re.compile(r"toothpaste|牙膏|mouthwash|漱口水|cream|膏$|shampoo|soap|vaseline|凡士林", re.I)
    stopped_names = [_s(r["med_name"]) for r in med_rows if r["med_event"] == "stopped"]
    started = _dedupe([_s(r["med_name"]) for r in med_rows if r["med_event"] == "started"
                       and not NOT_MED.search(_s(r["med_name"]))
                       and not any(name_sim(_s(r["med_name"]), sn) for sn in stopped_names)])
    card["ask"] += [{"text": "%s (%s)" % (prompts.STOP_RULE_EN, n), "kind": "stop_rule", "name": n} for n in started]
    for r in med_rows:
        if r["med_event"] != "stopped":
            continue
        n = _s(r["med_name"])
        rule = _s(r["med_rule"]) or next((_s(x["med_rule"]) for x in med_rows if name_sim(_s(x["med_name"]), n) and _s(x["med_rule"])), "")
        if not rule:
            m = next((DURATION.search(_s(x[f]) or "") for x in med_rows if name_sim(_s(x["med_name"]), n) for f in ("med_dose", "what", "source") if DURATION.search(_s(x[f]) or "")), None)
            rule = m.group(0).strip() if m else ""
        if rule:
            when = _s(r["med_date"]) or _s(r["date"]) or "date unknown"
            reason = _s(r["med_reason"])
            card["ask"].append({"kind": "stopcheck", "name": n, "stopped": when, "reason": reason, "rule": rule,
                                "text": "She stopped %s on %s%s. The doctor had said \"%s\". What should she do now?" % (n, when, (" because " + reason) if reason else "", rule)})
    stops = []
    for r in med_rows:
        if r["med_event"] == "stopped" and _s(r["med_name"]).lower() not in [s[0] for s in stops]:
            stops.append((_s(r["med_name"]).lower(), r))
    for _, r in stops:
        if _has_rule(r["med_name"], med_rows):
            continue
        when = _s(r["med_date"]) or _s(r["date"]) or "an unknown date"
        why = _s(r["med_reason"])
        card["ask"].append({"kind": "stopcheck", "text": "She stopped %s on %s%s. Was it OK to stop? Should she restart?" % (
            _s(r["med_name"]), when, (" because " + why) if why else "")})
    return card


def _strip_stop(card):
    c = dict(card)
    c["ask"] = [{"text": a["text"], "kind": a["kind"]} for a in card["ask"] if a["kind"] != "stop_rule"]
    return c


def source_hash(card):
    return hashlib.sha1(json.dumps(_strip_stop(card), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _check_shape(en, zh):
    if not isinstance(zh, dict) or not set(en) <= set(zh):
        raise ex.ExtractError("Chinese card is missing keys")
    for extra in set(zh) - set(en):  # model sometimes adds e.g. title_zh; drop
        del zh[extra]
    for k, v in en.items():
        z = zh[k]
        if isinstance(v, str):
            if not isinstance(z, str) or not z.strip():
                raise ex.ExtractError("Chinese card: %s is not text" % k)
            continue
        if not isinstance(z, list) or len(z) != len(v):
            raise ex.ExtractError("Chinese card: %s has a different length" % k)
        for i, (a, b) in enumerate(zip(v, z)):
            if isinstance(a, str):
                if not isinstance(b, str):
                    raise ex.ExtractError("Chinese card: %s item is not text" % k)
            else:
                if not isinstance(b, dict):
                    raise ex.ExtractError("Chinese card: %s item is not an object" % k)
                merged = dict(a)  # en values as fallback for fields the model dropped; extra model fields ignored
                for fk, fv in b.items():
                    if fk in a and isinstance(fv, str):
                        merged[fk] = fv
                z[i] = merged


def render_zh(card_no_stop):
    """Returns (zh_card, None) or (None, error_message). Input ask must hold only 'note' and 'stopcheck' items."""
    inp = {k: v for k, v in card_no_stop.items()}
    inp["ask"] = [{"text": a["text"], "kind": a["kind"]} for a in inp["ask"]]
    if not any(inp[k] for k in RULE_SKEL if isinstance(RULE_SKEL[k], list)):  # nothing to translate
        return dict(inp, title=inp["title"]), None
    err = None
    for _ in range(2):  # one retry if the shape check fails
        try:
            zh = ex._parse(ex._call(prompts.CARD_ZH_SYSTEM, json.dumps(inp, ensure_ascii=False), 4000))
            _check_shape(inp, zh)
            if not _chinese_enough(inp, zh):
                raise ex.ExtractError("Chinese card: rendering came back mostly in English")
            for a, b in zip(inp["ask"], zh["ask"]):
                b["kind"] = a["kind"]
            return zh, None
        except ex.ExtractError as e:
            err = e.message
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, e)
    return None, err


def _with_stop_rules(en, zh_core, wording):
    """zh ask in the same order as en.ask: model text for note/stopcheck, wording text for stop_rule."""
    it = iter(zh_core["ask"])
    out = []
    for a in en["ask"]:
        if a["kind"] == "stop_rule":
            out.append({"text": "%s（%s）" % (prompts.STOP_RULE_WORDINGS[wording], a["name"]), "kind": "stop_rule"})
        else:
            out.append(next(it))
    zh = dict(zh_core)
    zh["ask"] = out
    return zh


def _public_en(en):
    e = dict(en)
    e["ask"] = [{"text": a["text"], "kind": a["kind"]} for a in en["ask"]]
    return e


def get_card(conn, problem="all", wording="A"):
    en = build_card_en(conn, problem)
    h = source_hash(en)
    row = conn.execute("SELECT * FROM cards WHERE source_hash=? AND zh_json IS NOT NULL ORDER BY id DESC LIMIT 1", (h,)).fetchone()
    zh_core, err = None, None
    if row:
        zh_core = json.loads(row["zh_json"])
    else:
        zh_core, err = render_zh(_strip_stop(en))
        if zh_core:
            conn.execute("INSERT INTO cards(problem,source_hash,en_json,zh_json,zh_error,created_at) VALUES(?,?,?,?,?,?)",
                         (problem, h, json.dumps(_strip_stop(en), ensure_ascii=False),
                          json.dumps(zh_core, ensure_ascii=False), None, db.now()))
            conn.commit()
    zh = _with_stop_rules(en, zh_core, wording) if zh_core else None
    if zh:
        zh = zh_fix_dates_events(en, zh)
        zh["title"] = zh_title(problem)
    return {"problem": problem, "generated_at": db.now(), "source_hash": h, "en": _public_en(en), "zh": zh, "zh_error": err}


HEAD = {"zh": ["病史", "已做的检查", "现在在吃的药", "用药记录", "有帮助的", "会加重的", "想问医生的问题"],
        "en": ["History", "Tests already done", "Current medicines", "Medicine changes", "What helps", "What makes it worse", "Ask the doctor"]}


def render_text(card, lang):
    h = HEAD[lang]
    out = [card["title"], ""]

    def sec(i, lines, numbered=False):
        if not lines:
            return
        out.append(h[i])
        out.extend(("%d. %s" % (n, l)) if numbered else "- " + l for n, l in enumerate(lines, 1))
        out.append("")
    sec(0, ["%s: %s" % (x["date_text"], x["text"]) for x in card["history"]])
    sec(1, [" · ".join(p for p in ["%s: %s" % (x["date_text"], x["test"]), x["where"], x["result"]] if p) for x in card["tests"]])
    sec(2, [("%s: %s" % (x["name"], x["detail"])) if x["detail"] else x["name"] for x in card["medicines"]])
    sec(3, [" · ".join(p for p in ["%s: %s" % (x["date_text"], x["name"]), x["event"], x["rule"], x["reason"]] if p) for x in card["med_events"]])
    sec(4, card["helps"])
    sec(5, card["worsens"])
    sec(6, [a["text"] for a in card["ask"]], numbered=True)
    return "\n".join(out).rstrip() + "\n"


def _check_wording(w):
    if w not in prompts.STOP_RULE_WORDINGS:
        raise HTTPException(400, "unknown wording %r (use one of %s)" % (w, ", ".join(sorted(prompts.STOP_RULE_WORDINGS))))


@router.get("/api/card")
def api_card(problem: str = "all", wording: str = "A"):
    _check_wording(wording)
    c = db.connect()
    try:
        return get_card(c, problem, wording)
    finally:
        c.close()


@router.get("/api/card/text")
def api_card_text(problem: str = "all", wording: str = "A", lang: str = "zh"):
    _check_wording(wording)
    if lang not in ("zh", "en"):
        raise HTTPException(400, "lang must be zh or en")
    c = db.connect()
    try:
        d = get_card(c, problem, wording)
    finally:
        c.close()
    if lang == "zh" and d["zh"]:
        t = render_text(d["zh"], "zh")
    else:
        t = render_text(d["en"], "en")
        if lang == "zh":
            t = "(Chinese version failed; showing English: %s)\n\n" % d["zh_error"] + t
    return PlainTextResponse(t, media_type="text/plain; charset=utf-8")
