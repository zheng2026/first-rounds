"""Notes -> structured JSON via Nebius Token Factory, using the shipping prompt in tools/prompts.py."""
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request

from . import ROOT

sys.path.insert(0, os.path.join(ROOT, "tools"))
import prompts  # noqa: E402

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
MODEL_ID = prompts.MODELS[prompts.SHIPPING_MODEL]
VARIANT = prompts.SHIPPING_VARIANT


class ExtractError(Exception):
    def __init__(self, message, raw_text=""):
        super().__init__(message)
        self.message, self.raw_text = message, raw_text


class _HttpErr(Exception):
    def __init__(self, code, body):
        super().__init__("HTTP %s: %s" % (code, body[:300]))
        self.code, self.body = code, body


def apply_private_names(text):
    names = [n.strip() for n in (os.environ.get("PRIVATE_NAMES") or "").split(",") if n.strip()]
    for n in sorted(names, key=len, reverse=True):  # longest first
        text = re.sub(re.escape(n), "Mom", text, flags=re.IGNORECASE)
    return text


def _post(payload):
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        raise ExtractError("NEBIUS_API_KEY is not set")
    url = (os.environ.get("NEBIUS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/") + "/chat/completions"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise _HttpErr(e.code, e.read().decode("utf-8", "replace"))


def _call(system, user, max_tokens=4000):
    payload = {"model": MODEL_ID, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
               "temperature": 0, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
               "chat_template_kwargs": {"enable_thinking": bool(prompts.SHIPPING_THINKING)}}
    delays, retries = [2, 4, 8], 0
    while True:
        try:
            d = _post(payload)
            return d["choices"][0]["message"].get("content") or ""
        except _HttpErr as e:
            low = e.body.lower()
            if 400 <= e.code < 500 and e.code != 429 and "response_format" in payload and \
                    ("response_format" in low or "unsupported" in low or "json_object" in low):
                del payload["response_format"]
                continue
            if (e.code == 429 or e.code >= 500) and retries < 3:
                time.sleep(delays[retries]); retries += 1; continue
            raise ExtractError("model request failed: HTTP %s" % e.code, e.body[:2000])
        except (socket.timeout, TimeoutError, urllib.error.URLError, ConnectionError) as e:
            if retries < 3:
                time.sleep(delays[retries]); retries += 1; continue
            raise ExtractError("model request failed: %s" % type(e).__name__, str(e))
        except (KeyError, IndexError, ValueError) as e:
            raise ExtractError("unexpected model response", str(e))


def _parse(text):
    t = (text or "").strip().replace("```json", "").replace("```", "")
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        raise ExtractError("no JSON object in model output", text)
    try:
        out = json.loads(t[i:j + 1])
    except Exception as e:
        raise ExtractError("model output is not valid JSON: %s" % e, text)
    if not isinstance(out, dict):
        raise ExtractError("model output is not a JSON object", text)
    return out


def extract(note_text, note_date):
    """Returns the parsed output dict (prompts.OUTPUT_SCHEMA). Raises ExtractError(message, raw_text)."""
    note = apply_private_names(note_text)
    prev, raw = "", ""
    for system, tmpl in prompts.VARIANTS[VARIANT]:
        user = tmpl.format(note=note, note_date=note_date, prev=prev,
                           date_context=prompts.date_context(note_date))
        raw = _call(system, user)
        prev = raw
    return _parse(raw)
