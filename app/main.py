"""First Rounds API. See app/CONTRACT.md."""
import datetime as dt
import json
import os
import re
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ROOT, card, db, extract as ex, notify, stopcheck

STATIC = os.path.join(ROOT, "app", "static")
DEMO = os.path.join(ROOT, "app", "demo_notes.json")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_M = re.compile(r"^\d{4}-\d{2}$")
APPT = re.compile(r"appointment|复查|复诊|visit", re.I)
NEXT_WEEK = re.compile(r"next week|下周", re.I)

db.init_db()
os.makedirs(STATIC, exist_ok=True)
app = FastAPI(title="First Rounds")


# ---------------------------------------------------------------- errors
@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException):
    return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def _val_exc(request: Request, exc: RequestValidationError):
    return JSONResponse({"error": "invalid request: " + "; ".join(str(e.get("msg")) for e in exc.errors())}, status_code=422)


# ---------------------------------------------------------------- helpers
def _s(x):
    if x is None:
        return None
    x = str(x).strip()
    return x or None


def _list(x):
    return [str(i).strip() for i in x if i is not None and str(i).strip()] if isinstance(x, list) else []


def today():
    return dt.date.today().isoformat()


def sort_key(date, note_date):
    d = (date or "").strip()
    if ISO.match(d):
        return d
    if ISO_M.match(d):
        return d + "-15"
    m = re.search(r"\d{4}", d)
    if m:
        return m.group(0) + "-07-01"
    return note_date


STROKE_SIGNS = re.compile(r"face|mouth|droop|arm|hand|leg|weak|numb|clumsy|speech|slur|speak|balance|unsteady|vision|blurry|double|see|dizz|headache|"
                          r"脸|嘴|歪|手|胳膊|腿|无力|没劲|麻|说话|口齿|平衡|站不稳|视|看不清|重影|头晕|眩晕|头痛", re.I)
CHEST_SIGNS = re.compile(r"chest|breath|choking|bleed|seizure|swell|confus|胸|喘|呼吸|出血|抽搐|肿|糊涂", re.I)

def emergency_source(sign, model_source):
    """NHS for the general list, 中风120/BEFAST for stroke signs. The sign text decides; the model's label only breaks ties."""
    t = sign or ""
    if CHEST_SIGNS.search(t) and not STROKE_SIGNS.search(t):
        return "NHS"
    if STROKE_SIGNS.search(t):
        return "stroke"
    src = (model_source or "").lower()
    return "stroke" if ("中风" in src or "befast" in src or "stroke" in src) else "NHS"

PROBLEM_MAP = [
    ("teeth", r"teeth|tooth|dental|dentist|molar|gum|crown|牙|口腔"),
    ("blood pressure", r"blood pressure|\bbp\b|hypertens|血压"),
    ("heart", r"heart|cardio|心脏|心内|心电"),
    ("chest", r"chest|胸"),
    ("stomach", r"stomach|abdom|bloat|reflux|digest|gastr|胃|肚|反酸|消化"),
    ("sleep", r"sleep|insomnia|睡|失眠"),
    ("dizziness", r"dizz|vertigo|头晕|眩晕"),
    ("skin", r"skin|itch|rash|皮肤|痒|疹"),
    ("joints", r"joint|knee|arthr|膝|关节"),
    ("fall", r"\bfall|fell|slip|摔|跌"),
    ("eyes", r"\beye|vision|眼|视力"),
]

def normalize_problem(label, c=None):
    """Map the model's free-text label onto a small canonical set so one story stays one group; reuse an existing
    group when the label shares a word with it; else keep the model's label."""
    t = (label or "").strip().lower()
    if not t:
        return "other"
    for canon, pat in PROBLEM_MAP:
        if re.search(pat, t, re.I):
            return canon
    if c is not None:
        words = {w for w in re.findall(r"[a-z]{4,}", t)} | set(re.findall(r"[\u4e00-\u9fff]{2}", t))
        for (existing,) in c.execute("SELECT DISTINCT problem FROM entries"):
            ew = {w for w in re.findall(r"[a-z]{4,}", (existing or "").lower())} | set(re.findall(r"[\u4e00-\u9fff]{2}", existing or ""))
            if words & ew:
                return existing
    return t

def emergency_texts(sign, source):
    if emergency_source(sign, source) == "stroke":
        en_src, zh_src = "中风120 / BEFAST (Chinese Stroke Association)", "中风120 / BEFAST（中国卒中学会）"
    else:
        en_src, zh_src = "NHS guidance on when to call an ambulance", "英国NHS急救指南"
    sign = sign or "(not specified)"
    en = ("This note describes a possible warning sign: %s. %s advises calling emergency services (120 in China) "
          "immediately, even if symptoms have passed. Call Mom now. If signs are present, she or someone near her should call 120.") % (sign, en_src)
    zh = ("这条记录提到了可能的预警信号：%s。%s建议：即使症状已经消失，也应立即拨打120。"
          "请现在给妈妈打电话；如果症状仍在，请她或身边的人拨打120。") % (sign, zh_src)
    return en, zh


def _jl(s):
    try:
        v = json.loads(s) if s else []
        return v if isinstance(v, list) else []
    except Exception:
        return []


def chips_for(e):
    ch = []
    if e["med_name"] and e["med_event"]:
        ch.append({"kind": "med-stop" if e["med_event"] == "stopped" else "med", "text": "%s · %s" % (e["med_event"], e["med_name"])})
    if e["med_rule"]:
        ch.append({"kind": "rule", "text": "rule: " + e["med_rule"]})
    for w in _jl(e["worsens_json"]):
        ch.append({"kind": "worse", "text": "worse: " + str(w)})
    for h in _jl(e["helps_json"]):
        ch.append({"kind": "help", "text": "helps: " + str(h)})
    if e["test"]:
        ch.append({"kind": "test", "text": "%s · %s" % (e["test"], e["result"]) if e["result"] else e["test"]})
    return ch


def todo_json(r):
    return {"id": r["id"], "note_id": r["note_id"], "kind": r["kind"], "text": r["text"], "detail": r["detail"],
            "done_at": r["done_at"], "created_at": r["created_at"], "note_date": r["note_date"]}


TODO_SQL = "SELECT t.*, n.note_date AS note_date FROM todos t JOIN notes n ON n.id=t.note_id "


def entry_json(c, r, stop_by_entry=None):
    d = {k: r[k] for k in r.keys() if k != "note_date"}
    d["note_date"] = r["note_date"]
    d["helps"], d["worsens"] = _jl(r["helps_json"]), _jl(r["worsens_json"])
    d["chips"] = chips_for(r)
    sc = None
    if r["med_event"] == "stopped":
        if stop_by_entry is None:
            t = c.execute(TODO_SQL + "WHERE t.entry_id=? AND t.kind='stopcheck'", (r["id"],)).fetchone()
        else:
            t = stop_by_entry.get(r["id"])
        sc = todo_json(t) if t else None
    d["stopcheck"] = sc
    return d


ENTRY_SQL = "SELECT e.*, n.note_date AS note_date FROM entries e JOIN notes n ON n.id=e.note_id "


def question_json(r):
    return {"id": r["id"], "note_id": r["note_id"], "text": r["text"], "answered_at": r["answered_at"], "note_date": r["note_date"]}


def _ext_output(c, note_id):
    r = c.execute("SELECT output_json, error FROM extractions WHERE note_id=? ORDER BY id DESC LIMIT 1", (note_id,)).fetchone()
    out = None
    if r and r["output_json"]:
        try:
            out = json.loads(r["output_json"])
        except Exception:
            out = None
    return out, (r["error"] if r else None)


def emergency_block(out):
    em = (out or {}).get("emergency")
    if isinstance(em, dict) and em.get("warning") is True:
        sign, source = _s(em.get("sign")), _s(em.get("source"))
        en, zh = emergency_texts(sign, source)
        return {"warning": True, "sign": sign, "source": source, "text_en": en, "text_zh": zh}
    return None


def note_response(c, note_id):
    n = c.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if not n:
        raise HTTPException(404, "note not found")
    out, err = _ext_output(c, note_id)
    out = out if isinstance(out, dict) else {}
    ents = c.execute(ENTRY_SQL + "WHERE e.note_id=? ORDER BY e.sort_key, e.id", (note_id,)).fetchall()
    return {
        "note": {"id": n["id"], "note_date": n["note_date"], "text": n["text"], "kind": n["kind"]},
        "problem": normalize_problem(_s(out.get("problem"))),
        "nothing_medical": bool(out.get("nothing_medical")),
        "emergency": emergency_block(out),
        "entries": [entry_json(c, e) for e in ents],
        "questions": [question_json(q) for q in c.execute(
            "SELECT q.*, n.note_date AS note_date FROM questions q JOIN notes n ON n.id=q.note_id WHERE q.note_id=? ORDER BY q.id", (note_id,))],
        "todos": [todo_json(t) for t in c.execute(TODO_SQL + "WHERE t.note_id=? ORDER BY t.id", (note_id,))],
        "ask_doctor": [r["text"] for r in c.execute("SELECT text FROM ask_doctor WHERE note_id=? ORDER BY id", (note_id,))],
        "current_medicines": [r["text"] for r in c.execute("SELECT text FROM current_medicines WHERE note_id=? ORDER BY id", (note_id,))],
        "history_question": _s(out.get("history_question")),
        "extraction_error": err,
    }


# ---------------------------------------------------------------- ingest pipeline
def ingest(text, note_date, kind="call", answers_question_id=None):
    """Save note, run extraction, apply the code-owned rules. Returns note id."""
    c = db.connect()
    try:
        cur = c.execute("INSERT INTO notes(note_date,text,kind,answers_question_id,created_at) VALUES(?,?,?,?,?)",
                        (note_date, text, kind, answers_question_id, db.now()))
        note_id = cur.lastrowid
        c.commit()
    finally:
        c.close()

    try:
        out = ex.extract(text, note_date)
        err, raw = None, None
    except ex.ExtractError as e:
        out, err, raw = None, e.message, e.raw_text
    except Exception as e:  # never lose the note
        out, err, raw = None, "extraction failed: %s" % type(e).__name__, ""

    c = db.connect()
    try:
        c.execute("INSERT INTO extractions(note_id,model,variant,output_json,raw_text,error,created_at) VALUES(?,?,?,?,?,?,?)",
                  (note_id, ex.MODEL_ID, ex.VARIANT, json.dumps(out, ensure_ascii=False) if out is not None else None,
                   raw if raw is not None else json.dumps(out, ensure_ascii=False), err, db.now()))
        if out is not None:
            _apply(c, note_id, note_date, out)
        c.commit()
    finally:
        c.close()
    return note_id


META_ENTRY = re.compile(r"^\s*(note (written|taken|recorded)|phone ?call|call with mom|mom called|i called)\b", re.I)
ADVICE_TODO = re.compile(r"encourage|urge|should (see|go|stop|start|take|rest|avoid)|seek (medical|urgent|care)|advise|recommend|make sure (she|mom)|ensure (she|mom)|rest\b|avoid\b|建议|应该|劝", re.I)
ASK_PREFIX = re.compile(r"^\s*(ask mom|ask (her|the note-writer)|confirm with mom|confirm mom|clarify|check with mom|find out|verify|follow[- ]?up question)\b[:：]?\s*", re.I)

def _add_todo(c, note_id, kind, text, detail=None, entry_id=None):
    c.execute("INSERT INTO todos(note_id,kind,text,detail,done_at,created_at,entry_id) VALUES(?,?,?,?,NULL,?,?)",
              (note_id, kind, text, detail, db.now(), entry_id))
    notify.push(text, kind)


def _apply(c, note_id, note_date, out):
    # emergency first: code owns it, regardless of anything else
    em = emergency_block(out)
    if em:
        _add_todo(c, note_id, "emergency", em["text_en"], em["text_zh"])
    if out.get("nothing_medical") is True:
        return

    problem = normalize_problem(_s(out.get("problem")), c)
    appt_what = None
    for t in out.get("timeline") if isinstance(out.get("timeline"), list) else []:
        if not isinstance(t, dict):
            continue
        me = t.get("medicine_event") if isinstance(t.get("medicine_event"), dict) else {}
        if META_ENTRY.match(_s(t.get("what")) or "") and not me:
            continue
        date = _s(t.get("date"))
        prec = _s(t.get("date_precision")) or "unknown"
        c.execute("""INSERT INTO entries(note_id,problem,date,date_precision,sort_key,what,source,department,test,test_where,result,
                     med_name,med_event,med_date,med_dose,med_rule,med_reason,helps_json,worsens_json)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (note_id, problem, date, prec, sort_key(date, note_date), _s(t.get("what")) or "", _s(t.get("source")),
                   _s(t.get("department")), _s(t.get("test")), _s(t.get("test_where")), _s(t.get("result")),
                   _s(me.get("name")), _s(me.get("event")), _s(me.get("date")), _s(me.get("dose")),
                   _s(me.get("stopping_rule")), _s(me.get("reason")),
                   json.dumps(_list(t.get("helps")), ensure_ascii=False), json.dumps(_list(t.get("worsens")), ensure_ascii=False)))
        what = _s(t.get("what")) or ""
        if appt_what is None and APPT.search(what):
            future = bool(date and ISO.match(date) and date > note_date)
            nxt = prec in ("rough", "approx", "unknown") and bool(NEXT_WEEK.search((date or "") + " " + what))
            if future or nxt:
                appt_what = what

    # stop-check (code-owned)
    for s in stopcheck.stop_todos(c, note_id):
        _add_todo(c, note_id, "stopcheck", s["text"], s["detail"], s["entry_id"])

    # model todos -> reminders (drop the ones code owns)
    seen = set()
    routed_questions = []
    kept = 0
    for txt in _list(out.get("todos")):
        low = txt.lower()
        if low.startswith("mom stopped") or low.startswith("tell mom") or low.startswith("emergency:") or txt in seen:
            continue
        seen.add(txt)
        if ADVICE_TODO.search(txt) or (em and not ASK_PREFIX.match(txt)):
            continue  # advice wording never becomes a reminder; on emergency notes the warning owns the action
        if ASK_PREFIX.match(txt):
            routed_questions.append(ASK_PREFIX.sub("", txt).strip() or txt)
            continue
        if kept >= 4:
            continue
        kept += 1
        _add_todo(c, note_id, "reminder", txt)

    if appt_what:
        _add_todo(c, note_id, "appointment", "%s — has the date been confirmed?" % appt_what.rstrip(".。"))

    qseen = set()
    for q in _list(out.get("open_questions")) + routed_questions:
        if q.strip().lower() in qseen or len(qseen) >= 5:
            continue
        qseen.add(q.strip().lower())
        c.execute("INSERT INTO questions(note_id,text) VALUES(?,?)", (note_id, q))
    hq = _s(out.get("history_question"))
    if hq:
        c.execute("INSERT INTO questions(note_id,text) VALUES(?,?)", (note_id, hq))
        _add_todo(c, note_id, "history", hq)
    for m in _list(out.get("current_medicines")):
        c.execute("INSERT INTO current_medicines(note_id,text) VALUES(?,?)", (note_id, m))
    for a in _list(out.get("ask_the_doctor")):
        c.execute("INSERT INTO ask_doctor(note_id,problem,text) VALUES(?,?,?)", (note_id, problem, a))


# ---------------------------------------------------------------- API
class NoteIn(BaseModel):
    text: str
    note_date: Optional[str] = None


class AnswerIn(BaseModel):
    text: str


def _check_date(d):
    d = (d or "").strip() or today()
    try:
        dt.date.fromisoformat(d)
    except ValueError:
        raise HTTPException(400, "note_date must be YYYY-MM-DD")
    return d


@app.get("/api/health")
def health():
    return {"ok": True, "model": ex.MODEL_ID, "variant": ex.VARIANT, "db": db.db_path()}


@app.post("/api/notes", status_code=201)
def post_note(body: NoteIn):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text is empty")
    nid = ingest(text, _check_date(body.note_date))
    c = db.connect()
    try:
        return note_response(c, nid)
    finally:
        c.close()


@app.get("/api/notes")
def list_notes():
    c = db.connect()
    try:
        res = []
        for n in c.execute("SELECT * FROM notes ORDER BY note_date DESC, id DESC").fetchall():
            out, _ = _ext_output(c, n["id"])
            out = out if isinstance(out, dict) else {}
            res.append({"id": n["id"], "note_date": n["note_date"], "text": n["text"], "kind": n["kind"],
                        "created_at": n["created_at"], "problem": _s(out.get("problem")),
                        "entry_count": c.execute("SELECT COUNT(*) FROM entries WHERE note_id=?", (n["id"],)).fetchone()[0],
                        "emergency": emergency_block(out) is not None})
        return res
    finally:
        c.close()


@app.get("/api/notes/{note_id}")
def get_note(note_id: int):
    c = db.connect()
    try:
        return note_response(c, note_id)
    finally:
        c.close()


@app.delete("/api/notes/{note_id}")
def delete_note(note_id: int):
    c = db.connect()
    try:
        if not c.execute("SELECT 1 FROM notes WHERE id=?", (note_id,)).fetchone():
            raise HTTPException(404, "note not found")
        for t in ("entries", "todos", "questions", "current_medicines", "ask_doctor", "extractions"):
            c.execute("DELETE FROM %s WHERE note_id=?" % t, (note_id,))
        c.execute("UPDATE questions SET answered_at=NULL, answer_note_id=NULL WHERE answer_note_id=?", (note_id,))
        c.execute("DELETE FROM notes WHERE id=?", (note_id,))
        c.commit()
        return {"ok": True}
    finally:
        c.close()


@app.get("/api/timeline")
def timeline():
    c = db.connect()
    try:
        stops = {}
        for t in c.execute(TODO_SQL + "WHERE t.kind='stopcheck' AND t.entry_id IS NOT NULL"):
            stops[t["entry_id"]] = t
        groups = {}
        for r in c.execute(ENTRY_SQL + "ORDER BY e.sort_key, e.id"):
            groups.setdefault(r["problem"] or "other", []).append(r)
        probs = []
        for name, rows in groups.items():
            probs.append({"problem": name, "since": rows[0]["date"], "note_count": len({r["note_id"] for r in rows}),
                          "entries": [entry_json(c, r, stops) for r in rows], "_latest": max(r["sort_key"] for r in rows)})
        probs.sort(key=lambda p: p["_latest"], reverse=True)
        for p in probs:
            del p["_latest"]
        return {"problems": probs}
    finally:
        c.close()


@app.get("/api/today")
def get_today():
    c = db.connect()
    try:
        t = today()
        em = [todo_json(r) for r in c.execute(TODO_SQL + "WHERE t.kind='emergency' AND t.done_at IS NULL ORDER BY t.id DESC")]
        todos = [todo_json(r) for r in c.execute(TODO_SQL + "WHERE t.kind!='emergency' AND t.done_at IS NULL ORDER BY t.id")]
        qs = [question_json(r) for r in c.execute(
            "SELECT q.*, n.note_date AS note_date FROM questions q JOIN notes n ON n.id=q.note_id WHERE q.answered_at IS NULL ORDER BY q.id")]
        stops = {}
        appts = []
        for r in c.execute(ENTRY_SQL + "ORDER BY e.sort_key, e.id"):
            if not APPT.search(r["what"] or ""):
                continue
            d = r["date"] or ""
            # future-dated (ISO > today), or a rough "next week" appointment from a note in the last 14 days
            recent = r["note_date"] >= (dt.date.today() - dt.timedelta(days=14)).isoformat()
            if (ISO.match(d) and d > t) or (not ISO.match(d) and r["date_precision"] in ("rough", "approx", "unknown")
                                           and NEXT_WEEK.search(d + " " + (r["what"] or "")) and recent):
                appts.append(entry_json(c, r, stops))
        return {"emergencies": em, "todos": todos, "questions": qs, "appointments": appts}
    finally:
        c.close()


def _set_done(todo_id, done):
    c = db.connect()
    try:
        if not c.execute("SELECT 1 FROM todos WHERE id=?", (todo_id,)).fetchone():
            raise HTTPException(404, "todo not found")
        c.execute("UPDATE todos SET done_at=? WHERE id=?", (db.now() if done else None, todo_id))
        c.commit()
        return {"ok": True}
    finally:
        c.close()


@app.post("/api/todos/{todo_id}/done")
def todo_done(todo_id: int):
    return _set_done(todo_id, True)


@app.post("/api/todos/{todo_id}/undone")
def todo_undone(todo_id: int):
    return _set_done(todo_id, False)


@app.post("/api/questions/{qid}/answer", status_code=201)
def answer_question(qid: int, body: AnswerIn):
    ans = body.text.strip()
    if not ans:
        raise HTTPException(400, "answer is empty")
    c = db.connect()
    try:
        q = c.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
        if not q:
            raise HTTPException(404, "question not found")
    finally:
        c.close()
    nid = ingest('Answer to "%s": %s' % (q["text"], ans), today(), kind="answer", answers_question_id=qid)
    c = db.connect()
    try:
        c.execute("UPDATE questions SET answered_at=?, answer_note_id=? WHERE id=?", (db.now(), nid, qid))
        c.execute("UPDATE todos SET done_at=? WHERE kind='history' AND note_id=? AND text=? AND done_at IS NULL",
                  (db.now(), q["note_id"], q["text"]))
        c.commit()
        return note_response(c, nid)
    finally:
        c.close()


@app.get("/api/demo/load")
def demo_load():
    with open(DEMO, encoding="utf-8") as f:
        notes = sorted(json.load(f), key=lambda n: n["note_date"])
    loaded = 0
    for n in notes:
        c = db.connect()
        try:
            exists = c.execute("SELECT 1 FROM notes WHERE text=?", (n["text"],)).fetchone()
        finally:
            c.close()
        if not exists:
            ingest(n["text"], n["note_date"])
            loaded += 1
    return {"loaded": loaded}


# ---------------------------------------------------------------- frontend
app.include_router(card.router)


@app.get("/", include_in_schema=False)
def index():
    p = os.path.join(STATIC, "index.html")
    if os.path.exists(p):
        return FileResponse(p)
    return PlainTextResponse("frontend not built yet")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
