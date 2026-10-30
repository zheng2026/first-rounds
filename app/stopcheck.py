"""Stop-check: code (not the model) decides what to tell Mom / ask a doctor when a medicine was stopped."""
import re

CJK = re.compile(r"[一-鿿]")


def _s(x):
    return "" if x is None else str(x).strip()


def name_sim(a, b):
    a, b = _s(a).replace("的", ""), _s(b).replace("的", "")
    ca, cb = "".join(CJK.findall(a)), "".join(CJK.findall(b))
    if ca and cb:
        ba = {ca[i:i + 2] for i in range(len(ca) - 1)} or {ca}
        bb = {cb[i:i + 2] for i in range(len(cb) - 1)} or {cb}
        if ba & bb:
            return True
    wa = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", a)}
    wb = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", b)}
    return bool(wa & wb)


DURATION = re.compile(r"(?:for|finish(?: all)?|take(?: it)?(?: for)?)\s+(?:all\s+)?\d+\s*(?:days?|weeks?)|(?:吃|服|连续|连吃|吃满|吃完)\s*[一二三四五六七八九十\d]+\s*(?:天|日|周|个星期|星期)|[一二三四五六七八九十\d]+\s*(?:天|日)(?:的)?(?:疗程|药)", re.I)

def _when(row):
    return _s(row["med_date"]) or _s(row["date"])


def stop_todos(conn, note_id):
    """For each 'stopped' entry of this note: [{entry_id, text, detail}]."""
    out = []
    stops = conn.execute("SELECT * FROM entries WHERE note_id=? AND med_event='stopped' ORDER BY id", (note_id,)).fetchall()
    for st in stops:
        med = _s(st["med_name"])
        earlier = [r for r in conn.execute("SELECT * FROM entries WHERE id!=? AND (id<? OR note_id=?) AND med_name IS NOT NULL AND med_name!='' ORDER BY id",
                   (st["id"], st["id"], note_id))
                   if name_sim(r["med_name"], med)]
        rule = _s(st["med_rule"])
        if not rule:
            for r in reversed(earlier):
                if _s(r["med_rule"]):
                    rule = _s(r["med_rule"])
                    break
        if not rule:  # the doctor's duration often lands in dose/what/source instead of stopping_rule
            for r in [st] + list(reversed(earlier)):
                for field in ("med_dose", "what", "source"):
                    m = DURATION.search(_s(r[field]))
                    if m:
                        rule = m.group(0).strip()
                        break
                if rule:
                    break
        stopped = _when(st)
        reason = _s(st["med_reason"])
        if rule:
            text = 'Tell Mom: the doctor said "%s" (%s)' % (rule, med)
            detail = "%s stopped %s; reason: %s" % (med, stopped or "date unknown", reason or "not stated")
        else:
            start = ""
            for r in earlier:
                if r["med_event"] in ("started", "resumed") and _when(r):
                    start = _when(r)
                    break
            text = "Mom stopped %s %s; no stopping instruction recorded. Ask a doctor or pharmacist." % (
                med, stopped or "(date unknown)")
            zh = "我妈%s开始吃%s，%s就停了。当时医生有没有说要吃多久？现在停可以吗？" % (start or "不记得什么时候", med, reason)
            en = "Mom started %s on %s, stopped %s%s. Did the doctor say how long to take it? Is stopping now OK?" % (
                med, start or "(date unknown)", stopped or "(date unknown)", (" because " + reason) if reason else "")
            detail = zh + "\n" + en
        out.append({"entry_id": st["id"], "text": text, "detail": detail})
    return out
