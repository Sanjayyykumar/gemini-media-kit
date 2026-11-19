"""Thin HTTP layer over the Gemini REST API (stdlib only).

- The key is sent as a query parameter (works for AIza... and AQ.... keys) and is
  masked as *** in every message shown to the user.
- Busy / overloaded / timed-out / unavailable models raise `ModelBusy`, so the router
  (router.py) can move to the next model instead of failing.
"""
from __future__ import annotations

import base64, json, mimetypes, os, re, sys, time
import urllib.error, urllib.request
from pathlib import Path
from urllib.parse import quote

from .config import load_key

API = "https://generativelanguage.googleapis.com/v1beta"
_HINT = re.compile(r"use models/([\w.\-]+)")
BUSY_CODES = (429, 500, 502, 503, 504)
SKIP_CODES = BUSY_CODES + (404,)


class ModelBusy(Exception):
    """This model can't serve the request right now; another model might.

    kind: "overloaded" (5xx/timeout), "rate" (429, try again soon),
          "no_quota" (429 with limit 0 - needs billing), "unavailable" (404)
    """
    def __init__(self, model: str, reason: str, replacement: str | None = None,
                 kind: str = "overloaded", retry_after: float | None = None, detail: str = ""):
        super().__init__(reason)
        self.model, self.reason, self.replacement = model, reason, replacement
        self.kind, self.retry_after, self.detail = kind, retry_after, detail


def classify(code: int, msg: str, model: str) -> ModelBusy:
    """Turn Google's error body into a precise, actionable ModelBusy."""
    hint = _HINT.search(msg)
    if code == 404:
        return ModelBusy(model, "not available to this key", hint.group(1) if hint else None,
                         kind="unavailable")
    if code == 429:
        retry = None
        m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', msg) or \
            re.search(r"retry in (\d+(?:\.\d+)?)s", msg, re.I)
        if m:
            retry = float(m.group(1))
        metric = re.search(r"metric: ([\w./\-]+)", msg)
        detail = metric.group(1).split("/")[-1] if metric else ""
        if re.search(r"limit:\s*0\b", msg) or ("free_tier" in msg and retry is None and "limit" in msg):
            return ModelBusy(model, "no quota on this key (free tier allows 0)", kind="no_quota",
                             detail=detail)
        if "per day" in msg.lower() or "PerDay" in msg:
            return ModelBusy(model, "daily quota used up", kind="no_quota", detail=detail)
        return ModelBusy(model, "rate limit", kind="rate", retry_after=retry, detail=detail)
    return ModelBusy(model, "Google overloaded" if code in (500, 502, 503, 504) else f"HTTP {code}",
                     kind="overloaded")


def log(msg: str, end: str = "\n") -> None:
    print(f"[gmk] {msg}", file=sys.stderr, end=end, flush=True)

def _timeout(kind: str = "default") -> int:
    # Streams must show first words quickly; a silent model is treated as busy.
    env = os.environ.get("GMK_TIMEOUT")
    if env:
        return int(env)
    return {"stream": 40, "default": 120}.get(kind, 120)

def _url(path: str, key: str, extra: str = "") -> str:
    if path.startswith("http"):
        base = path
    else:
        base = f"{API}/{path.lstrip('/')}"
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{extra}key={quote(key, safe='')}"

_HINTS = {
    400: "Bad request - check the prompt/options, or the key format (`gmk key-status`).",
    401: "Key rejected - re-save it with `gmk set-key --clipboard`.",
    403: "Permission/billing - Veo and some models need a paid key.",
    404: "Model not available to this key - choose one with `gmk pick-model <kind>`.",
    429: "Quota or rate limit hit - wait, or raise limits in AI Studio.",
    503: "Google is overloaded right now (not your setup).",
}

def fail(code, msg: str = "") -> None:
    if code == "":                       # router summary: already plain language
        sys.exit(msg)
    sys.exit(f"HTTP {code}: {_HINTS.get(code, 'Request failed.')}\n{msg[:1200]}".rstrip())

def _model_of(path: str) -> str:
    m = re.search(r"models/([\w.\-]+):", path)
    return m.group(1) if m else "?"

def _http_error(e: urllib.error.HTTPError, key: str, model: str):
    msg = e.read().decode(errors="replace").replace(key, "***")
    if e.code in SKIP_CODES:
        if os.environ.get("GMK_DEBUG"):
            log(f"raw error from {model}: {msg[:800]}")
        raise classify(e.code, msg, model)
    fail(e.code, msg)


def request(method: str, path: str, body=None, raw: bool = False):
    """JSON (or raw bytes) request. `path` is relative to the API root, or a full URL."""
    key = load_key()
    model = _model_of(path)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(_url(path, key), data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_timeout()) as r:
            out = r.read()
    except urllib.error.HTTPError as e:
        _http_error(e, key, model)
    except (TimeoutError, urllib.error.URLError) as e:
        if "timed out" in str(e).lower() and model != "?":
            raise ModelBusy(model, "no reply in time", kind="overloaded")
        sys.exit(f"Network error ({e}). Check your internet / VPN / proxy.")
    return out if raw else json.loads(out or b"{}")


def stream(model: str, contents: list, think: str | None = None) -> str:
    """Stream a text reply to stdout as it is generated. Returns the full text."""
    key = load_key()
    body = {"contents": contents}
    if think:
        body["generationConfig"] = {"thinkingConfig": {"thinkingLevel": think}}
    req = urllib.request.Request(
        _url(f"models/{model}:streamGenerateContent", key, "alt=sse&"),
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    t0, out = time.time(), []
    log(f"{model} thinking...", end="")
    try:
        with urllib.request.urlopen(req, timeout=_timeout("stream")) as r:
            for raw_line in r:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                for cand in json.loads(line[5:]).get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if part.get("thought") or not part.get("text"):
                            continue
                        if not out:
                            print(f"\r[gmk] {model} - first words in {time.time() - t0:.1f}s",
                                  file=sys.stderr, flush=True)
                        print(part["text"], end="", flush=True)
                        out.append(part["text"])
    except urllib.error.HTTPError as e:
        print(file=sys.stderr)
        msg = e.read().decode(errors="replace").replace(key, "***")
        if e.code == 400 and think and "think" in msg.lower():
            log("this model has no thinking control; retrying without --think")
            return stream(model, contents, None)
        if not out and e.code in SKIP_CODES:
            if os.environ.get("GMK_DEBUG"):
                log(f"raw error from {model}: {msg[:800]}")
            raise classify(e.code, msg, model)
        fail(e.code, msg)
    except (TimeoutError, urllib.error.URLError) as e:
        print(file=sys.stderr)
        if not out and "timed out" in str(e).lower():
            raise ModelBusy(model, "no reply in time", kind="overloaded")
        sys.exit(f"\nNetwork error ({e}). Check your internet / VPN / proxy.")
    print()
    return "".join(out)


# ---------- helpers ----------
def file_part(path: str) -> dict:
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return {"inlineData": {"mimeType": mime,
                           "data": base64.b64encode(Path(path).read_bytes()).decode()}}

def output_paths(base: str | None, count: int, ext: str) -> list:
    p = Path(base or f"out/gmk_{time.strftime('%Y%m%d_%H%M%S')}{ext}")
    if not p.suffix:
        p = p.with_suffix(ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    if count == 1:
        return [p]
    return [p.with_name(f"{p.stem}_{i + 1}{p.suffix}") for i in range(count)]
