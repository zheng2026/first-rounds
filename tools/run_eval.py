#!/usr/bin/env python3
"""Run prompt variants x models x notes against Nebius, cache, score, write tests/results.json."""
import argparse, json, os, sys, time, urllib.request, urllib.error, socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import prompts

RUNS = os.path.join(ROOT, "tests", "runs")


def load_env():
    env = {}
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("NEBIUS_API_KEY", "NEBIUS_BASE_URL"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


class HttpErr(Exception):
    def __init__(self, code, body):
        super().__init__("HTTP %s: %s" % (code, body[:300]))
        self.code, self.body = code, body


def post(env, payload):
    url = env["NEBIUS_BASE_URL"].rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + env["NEBIUS_API_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HttpErr(e.code, e.read().decode("utf-8", "replace"))


def call(env, model, system, user, max_tokens, think=False):
    """Returns (text, usage, latency_ms, attempts)."""
    payload = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
               "temperature": 0, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
               "chat_template_kwargs": {"enable_thinking": bool(think)}}
    attempts = 0
    t0 = time.time()
    delays = [2, 4, 8]
    retries = 0
    while True:
        attempts += 1
        try:
            d = post(env, payload)
            text = d["choices"][0]["message"].get("content") or ""
            return text, d.get("usage") or {}, int((time.time() - t0) * 1000), attempts
        except HttpErr as e:
            low = e.body.lower()
            if 400 <= e.code < 500 and e.code != 429 and "response_format" in payload and \
                    ("response_format" in low or "unsupported" in low or "json_object" in low):
                del payload["response_format"]
                continue
            if (e.code == 429 or e.code >= 500) and retries < 3:
                time.sleep(delays[retries]); retries += 1; continue
            raise
        except (socket.timeout, TimeoutError, urllib.error.URLError, ConnectionError) as e:
            if retries < 3:
                time.sleep(delays[retries]); retries += 1; continue
            raise HttpErr("timeout", str(e))


def parse_json(text):
    t = text.strip()
    if "```" in t:
        t = t.replace("```json", "").replace("```", "")
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        return None, "no JSON object found"
    try:
        return json.loads(t[i:j + 1]), None
    except Exception as e:
        return None, str(e)


def cache_path(variant, model, nid):
    return os.path.join(RUNS, "%s__%s" % (variant, model), nid + ".json")


def run_combo(env, variant, model, note, max_tokens):
    steps, prev = [], ""
    think = variant in getattr(prompts, "THINKING_ON", set())
    if think:
        max_tokens = max(max_tokens, getattr(prompts, "MAX_TOKENS_THINKING", 16000))
    for system, tmpl in prompts.VARIANTS[variant]:
        user = tmpl.format(note=note["note"], note_date=note["note_date"], prev=prev,
                           date_context=prompts.date_context(note["note_date"]))
        text, usage, ms, att = call(env, prompts.MODELS[model], system, user, max_tokens, think=think)
        steps.append({"raw": text, "prompt_tokens": usage.get("prompt_tokens"),
                      "completion_tokens": usage.get("completion_tokens"), "latency_ms": ms, "attempts": att})
        prev = text
    out, err = parse_json(prev)
    rec = {"note_id": note["id"], "variant": variant, "model": model, "steps": steps, "output": out,
           "parse_error": err, "ran_at": datetime.now(timezone.utc).isoformat()}
    os.makedirs(os.path.dirname(cache_path(variant, model, note["id"])), exist_ok=True)
    with open(cache_path(variant, model, note["id"]), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notes"); ap.add_argument("--variants"); ap.add_argument("--models")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--score-only", action="store_true", help="no API calls; rescore cached runs only")
    a = ap.parse_args()

    try:
        from score import score_note, DIMENSIONS
    except ImportError as e:
        sys.exit("ERROR: tools/score.py missing or broken (%s). Cannot score." % e)

    nd = json.load(open(os.path.join(ROOT, "tests", "notes.json"), encoding="utf-8"))
    notes = {n["id"]: n for n in nd["notes"]}
    nids = a.notes.split(",") if a.notes else list(notes)
    variants = a.variants.split(",") if a.variants else list(prompts.VARIANTS)
    models = a.models.split(",") if a.models else list(prompts.MODELS)
    for x, pool, nm in ((nids, notes, "note"), (variants, prompts.VARIANTS, "variant"), (models, prompts.MODELS, "model")):
        for i in x:
            if i not in pool:
                sys.exit("unknown %s: %s" % (nm, i))

    env = load_env()
    if not env.get("NEBIUS_API_KEY") or not env.get("NEBIUS_BASE_URL"):
        sys.exit("ERROR: NEBIUS_API_KEY / NEBIUS_BASE_URL missing in .env")

    combos = [(v, m, n) for v in variants for m in models for n in nids]
    todo = [] if a.score_only else [c for c in combos if a.force or not os.path.exists(cache_path(*c))]
    total = len(combos)
    print("%d combos, %d to run, %d cached" % (total, len(todo), total - len(todo)))
    done = total - len(todo)

    def work(c):
        v, m, n = c
        t0 = time.time()
        try:
            rec = run_combo(env, v, m, notes[n], a.max_tokens)
            status = "ok" if rec["output"] is not None else "PARSE_ERROR"
        except HttpErr as e:
            status = "HTTP_ERROR %s" % e.code
        except Exception as e:
            status = "HTTP_ERROR %s" % type(e).__name__
        return c, status, time.time() - t0

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(work, c) for c in todo]
        for f in as_completed(futs):
            c, status, dt = f.result()
            done += 1
            print("[%d/%d] %s %s %s %s %.1fs" % (done, total, c[0], c[1], c[2], status, dt), flush=True)

    runs = []
    for v, m, n in combos:
        p = cache_path(v, m, n)
        if not os.path.exists(p):
            continue
        rec = json.load(open(p, encoding="utf-8"))
        st = rec["steps"]
        sc = score_note(dict(notes[n]["expected"], _note_text=notes[n]["note"]), rec["output"], notes[n]["note_date"])
        runs.append({"note_id": n, "variant": v, "model": m, "output": rec["output"], "parse_error": rec["parse_error"],
                     "scores": sc, "latency_ms_total": sum(s.get("latency_ms") or 0 for s in st),
                     "prompt_tokens": sum(s.get("prompt_tokens") or 0 for s in st),
                     "completion_tokens": sum(s.get("completion_tokens") or 0 for s in st),
                     "steps_raw": [s["raw"] for s in st]})
    res = {"meta": {"ran_at": datetime.now(timezone.utc).isoformat(), "notes": nids, "variants": variants,
                    "models": {m: prompts.MODELS[m] for m in models}, "dimensions": DIMENSIONS}, "runs": runs}
    with open(os.path.join(ROOT, "tests", "results.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # summary
    cols = ["%s__%s" % (v, m) for v in variants for m in models]
    keys = [d[0] for d in DIMENSIONS]
    def cell(col, fn):
        rs = [r for r in runs if "%s__%s" % (r["variant"], r["model"]) == col]
        vals = [x for x in (fn(r) for r in rs) if x is not None]
        return "%.2f" % (sum(vals) / len(vals)) if vals else "-"
    w = max(len(k) for k in keys + ["json_valid", "latency_s"]) + 1
    print("\n" + "".ljust(w) + " ".join(c[:18].rjust(18) for c in cols))
    rows = [(k, (lambda k: lambda r: (r["scores"] or {}).get(k))(k)) for k in keys]
    rows.append(("json_valid", lambda r: 1.0 if r["output"] is not None else 0.0))
    rows.append(("latency_s", lambda r: r["latency_ms_total"] / 1000))
    for name, fn in rows:
        print(name.ljust(w) + " ".join(cell(c, fn).rjust(18) for c in cols))
    print("\nwrote tests/results.json (%d runs)" % len(runs))


if __name__ == "__main__":
    main()
