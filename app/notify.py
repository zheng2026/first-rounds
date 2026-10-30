"""Optional push of each new todo to ntfy.sh/<NTFY_TOPIC>. Never raises."""
import os
import threading
import urllib.request


def _send(topic, text, kind):
    try:
        req = urllib.request.Request("https://ntfy.sh/" + topic, data=text.encode("utf-8"), method="POST", headers={
            "Title": "First Rounds", "Priority": "urgent" if kind == "emergency" else "default",
            "Tags": "rotating_light" if kind == "emergency" else "memo"})
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass


def push(text, kind="reminder"):
    topic = (os.environ.get("NTFY_TOPIC") or "").strip()
    if topic:
        threading.Thread(target=_send, args=(topic, text, kind), daemon=True).start()
