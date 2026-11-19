"""Zero-dependency MCP server (stdio, JSON-RPC 2.0) exposing gmk as tools.

Start with:  python gmk.py mcp
Register in Claude Desktop / Cursor / any MCP client as a stdio server (see README).

The API key is read from gmk's private config (`gmk set-key`) or GEMINI_API_KEY -
it never needs to appear in the client's config file.
Tools reuse the CLI commands, so routing, failover and friendly errors all apply.
"""
from __future__ import annotations

import base64, contextlib, io, json, os, sys, time
from pathlib import Path

from . import __version__, config as cfg
from .cli import build_parser

PROTOCOL = "2025-06-18"


def _out_dir() -> Path:
    d = Path(os.environ.get("GMK_OUT") or Path.home() / "Pictures" / "gemini-media-kit")
    d.mkdir(parents=True, exist_ok=True)
    return d

def _default_name(ext: str) -> str:
    return str(_out_dir() / f"gmk_{time.strftime('%Y%m%d_%H%M%S')}{ext}")


# ---------------- tool definitions ----------------
TIER_TEXT = {"type": "string", "enum": ["auto", "lite", "standard", "pro"],
             "description": "auto (default) sends short prompts to a fast lite model"}

TOOLS = [
    {"name": "gemini_text",
     "description": "Ask a Google Gemini model. Optional files/images to analyse. "
                    "Routes small tasks to lite models and fails over when Google is busy.",
     "inputSchema": {"type": "object", "properties": {
         "prompt": {"type": "string"},
         "files": {"type": "array", "items": {"type": "string"},
                   "description": "absolute paths of files/images to include"},
         "tier": TIER_TEXT,
         "think": {"type": "string", "enum": ["low", "medium", "high"]},
         "model": {"type": "string", "description": "pin one model id (disables routing)"}},
         "required": ["prompt"]}},
    {"name": "gemini_image",
     "description": "Generate or edit an image with Nano Banana. Pass input_images to edit "
                    "or keep a character consistent. Returns the saved file path and a preview.",
     "inputSchema": {"type": "object", "properties": {
         "prompt": {"type": "string"},
         "input_images": {"type": "array", "items": {"type": "string"},
                          "description": "absolute paths of reference/source images"},
         "aspect": {"type": "string", "description": "1:1, 16:9, 9:16, 4:3, 3:4 ..."},
         "tier": {"type": "string", "enum": ["standard", "pro"],
                  "description": "pro = Nano Banana Pro (best for text in images)"},
         "output": {"type": "string", "description": "absolute output path (.png)"},
         "model": {"type": "string"}},
         "required": ["prompt"]}},
    {"name": "gemini_video",
     "description": "Generate a video with Google Veo (paid per second, takes 1-6 minutes). "
                    "Optional start_image for image-to-video. Confirm with the user before long runs.",
     "inputSchema": {"type": "object", "properties": {
         "prompt": {"type": "string"},
         "start_image": {"type": "string", "description": "absolute path of the first frame"},
         "aspect": {"type": "string", "enum": ["16:9", "9:16"]},
         "resolution": {"type": "string", "enum": ["720p", "1080p", "4k"]},
         "seconds": {"type": "integer"},
         "negative": {"type": "string", "description": "things to avoid"},
         "allow_cheaper": {"type": "boolean",
                           "description": "if busy, fall back to fast/lite Veo"},
         "output": {"type": "string", "description": "absolute output path (.mp4)"},
         "model": {"type": "string"}},
         "required": ["prompt"]}},
    {"name": "gemini_models",
     "description": "List the models this API key can use, grouped by kind.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "gemini_status",
     "description": "Show whether a key is configured (never reveals it) and which model each kind uses.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def _argv(name: str, a: dict) -> list:
    if name == "gemini_text":
        v = ["text", a["prompt"]]
        if a.get("files"): v += ["--input", *a["files"]]
        for k in ("tier", "think", "model"):
            if a.get(k): v += [f"--{k}", a[k]]
    elif name == "gemini_image":
        v = ["image", a["prompt"], "-o", a.get("output") or _default_name(".png")]
        if a.get("input_images"): v += ["--input", *a["input_images"]]
        for k in ("aspect", "tier", "model"):
            if a.get(k): v += [f"--{k}", a[k]]
    elif name == "gemini_video":
        v = ["video", a["prompt"], "-o", a.get("output") or _default_name(".mp4")]
        if a.get("start_image"): v += ["--image", a["start_image"]]
        for k in ("aspect", "resolution", "negative", "model"):
            if a.get(k): v += [f"--{k}", a[k]]
        if a.get("seconds"): v += ["--seconds", str(a["seconds"])]
        if a.get("allow_cheaper"): v += ["--allow-cheaper"]
    elif name == "gemini_models":
        v = ["models"]
    elif name == "gemini_status":
        v = ["config"]
    else:
        raise KeyError(name)
    return v


def _call_tool(name: str, args: dict) -> dict:
    try:
        argv = _argv(name, args or {})
    except KeyError:
        return {"content": [{"type": "text", "text": f"Unknown tool {name}"}], "isError": True}
    buf, err = io.StringIO(), io.StringIO()
    is_error = False
    try:
        ns = build_parser().parse_args(argv)
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            if name == "gemini_status":
                print("Key: " + ("configured" if cfg.key_source() else
                                 "NOT SET - ask the user to run `gmk set-key --clipboard` in a terminal"))
            ns.func(ns)
    except SystemExit as e:
        is_error = bool(e.code) and e.code != 0
        if isinstance(e.code, str):
            buf.write(e.code)
    except Exception as e:                       # never crash the server
        is_error = True
        buf.write(f"Unexpected error: {e}")
    text = buf.getvalue().strip() or "(no output)"
    content = [{"type": "text", "text": text}]
    # attach small image previews so the assistant can see the result
    for line in text.splitlines():
        if line.startswith("saved ") and line.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            p = Path(line[6:].strip())
            if p.exists() and p.stat().st_size < 3_000_000:
                content.append({"type": "image", "mimeType": "image/png",
                                "data": base64.b64encode(p.read_bytes()).decode()})
    return {"content": content, "isError": is_error}


# ---------------- JSON-RPC loop ----------------
def _send(msg: dict) -> None:
    sys.__stdout__.write(json.dumps(msg) + "\n")
    sys.__stdout__.flush()

def _handle(req: dict):
    method, rid = req.get("method"), req.get("id")
    if method == "initialize":
        client_ver = (req.get("params") or {}).get("protocolVersion") or PROTOCOL
        return {"protocolVersion": client_ver,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "gemini-media-kit", "version": __version__},
                "instructions": "Google Gemini, Nano Banana and Veo. Never ask the user for "
                                "their API key in chat; if missing, tell them to run "
                                "`gmk set-key --clipboard` in a terminal. Veo is paid per second."}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        p = req.get("params") or {}
        return _call_tool(p.get("name", ""), p.get("arguments") or {})
    if rid is None:                    # notification (e.g. notifications/initialized)
        return None
    raise NotImplementedError(method)


def serve() -> None:
    for stream_ in (sys.stdin, sys.__stdout__, sys.stderr):
        try:
            stream_.reconfigure(encoding="utf-8")      # Windows consoles default to cp1252
        except Exception:
            pass
    print(f"[gmk] MCP server {__version__} ready (stdio)", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            _send({"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32700, "message": "Parse error"}})
            continue
        rid = req.get("id")
        try:
            result = _handle(req)
            if rid is not None:
                _send({"jsonrpc": "2.0", "id": rid, "result": result})
        except NotImplementedError as e:
            if rid is not None:
                _send({"jsonrpc": "2.0", "id": rid,
                       "error": {"code": -32601, "message": f"Method not found: {e}"}})
        except Exception as e:
            if rid is not None:
                _send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": str(e)}})


def mcp(a) -> None:
    serve()
