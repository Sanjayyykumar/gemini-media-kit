"""Every `gmk <command>` lives here. Each function takes the parsed argparse namespace."""
from __future__ import annotations
import base64, getpass, json, mimetypes, subprocess, sys, time
from pathlib import Path

from . import config as cfg
from .api import API, ModelBusy, fail, file_part, log, output_paths, request, stream
from . import router
from .router import _box


# ================= key =================
def _clipboard() -> str:
    if sys.platform == "win32":
        cmd = ["powershell", "-NoProfile", "-Command", "Get-Clipboard"]
    elif sys.platform == "darwin":
        cmd = ["pbpaste"]
    else:
        cmd = ["xclip", "-o", "-selection", "clipboard"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout

def set_key(a):
    raw = _clipboard() if a.clipboard else getpass.getpass("Paste your Gemini API key (hidden): ")
    key = cfg.clean_key(raw)
    if not key:
        sys.exit("Nothing received - no key saved.")
    path = cfg.save_key(key)
    print(f"Saved to {path}\nKey: {cfg.describe_key(key)}")

def key_status(a):
    src = cfg.key_source()
    if not src:
        print("No key saved. Run `gmk set-key`.")
        return
    print(f"Key from {src}\nKey: {cfg.describe_key(cfg.load_key())}")

def delete_key(a):
    print("Stored key deleted." if cfg.delete_key() else "No stored key to delete.")


# ================= models =================
_NOT_TEXT = ("image", "banana", "veo", "imagen", "embed", "tts", "audio", "lyria",
             "transcribe", "robotics", "computer-use")

def _fits(kind: str, name: str, methods: list) -> bool:
    n = name.lower()
    if kind == "video":
        return "veo" in n
    if kind == "imagen":
        return "imagen" in n
    if kind == "image":
        return ("image" in n or "banana" in n) and "imagen" not in n
    return "generateContent" in methods and not any(x in n for x in _NOT_TEXT)

def _available(kind: str | None = None) -> list[tuple[str, list]]:
    try:
        r = request("GET", "models?pageSize=500")
    except ModelBusy as e:
        fail(503, f"Couldn't list models ({e.reason}). Try again shortly.")
    items = [(m["name"].split("/")[-1], m.get("supportedGenerationMethods", []))
             for m in r.get("models", [])]
    return [i for i in items if kind is None or _fits(kind, *i)]

def models(a):
    for kind in cfg.KINDS:
        names = [n for n, _ in _available(kind)]
        print(f"\n{kind.upper()} ({len(names)})")
        for n in names:
            print(f"  {n}{'   <- in use' if n == cfg.model_for(kind) else ''}")

def show_config(a):
    saved = cfg.saved_models()
    print(f"Key      : {cfg.key_source() or 'not set'}")
    print(f"Settings : {cfg.settings_file()}\n")
    for k in cfg.KINDS:
        print(f"  {k:7} {cfg.model_for(k):38} {'(your choice)' if k in saved else '(default)'}")

def set_model(a):
    cfg.set_model(a.kind, a.model)
    print(f"{a.kind} -> {a.model}  (saved until you change it)")

def pick_model(a):
    names = [n for n, _ in _available(a.kind)]
    if not names:
        sys.exit(f"Your key has no {a.kind} models.")
    current = cfg.model_for(a.kind)
    for i, n in enumerate(names, 1):
        print(f"{i:3}. {n}{'   <- current' if n == current else ''}")
    choice = input(f"\nNumber for {a.kind} (Enter keeps {current}): ").strip()
    if not choice:
        print("Unchanged.")
        return
    a.model = names[int(choice) - 1]
    set_model(a)

def reset_model(a):
    cfg.reset_model(a.kind)
    print(f"Reset {a.kind} to default.\n")
    show_config(a)


# ================= text =================
def text(a):
    parts = [file_part(f) for f in (a.input or [])] + [{"text": a.prompt}]
    tier = router.text_tier(a.prompt, bool(a.input), a.tier)
    if tier == "lite" and not a.model and router.routing_enabled():
        log("small task -> lite model (use --tier standard to override)")
    contents = [{"role": "user", "parts": parts}]
    router.run("text", router.candidates("text", tier, a.model),
               lambda m: stream(m, contents, a.think), a.wait)

def chat(a):
    pinned, history, files = a.model, [], []
    tier = a.tier if a.tier and a.tier != "auto" else "standard"
    print(f"Chatting ({'model ' + pinned if pinned else tier + ' tier, auto-failover'}). "
          "/file <path>  /model <id>  /tier lite|standard|pro  /clear  /exit")
    while True:
        try:
            msg = input("\nyou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg:
            continue
        if msg in ("/exit", "/quit"):
            break
        if msg == "/clear":
            history.clear(); print("(conversation cleared)"); continue
        if msg.startswith("/model "):
            pinned = msg.split(maxsplit=1)[1]; print(f"(pinned to {pinned})"); continue
        if msg.startswith("/tier "):
            tier, pinned = msg.split(maxsplit=1)[1], None; print(f"(tier {tier})"); continue
        if msg.startswith("/file "):
            files.append(file_part(msg.split(maxsplit=1)[1].strip('"')))
            print("(attached to your next message)"); continue
        history.append({"role": "user", "parts": files + [{"text": msg}]})
        files = []
        print("gemini > ", end="", flush=True)
        try:
            reply = router.run("text", router.candidates("text", tier, pinned),
                               lambda m: stream(m, history, a.think))
        except SystemExit as e:
            print(e); history.pop(); continue
        history.append({"role": "model", "parts": [{"text": reply}]})


# ================= images =================
def image(a):
    parts = [file_part(f) for f in (a.input or [])] + [{"text": a.prompt}]
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}
    if a.aspect:
        body["generationConfig"]["imageConfig"] = {"aspectRatio": a.aspect}
    def call(model):
        log(f"{model} drawing...")
        return request("POST", f"models/{model}:generateContent", body)
    r = router.run("image", router.candidates("image", a.tier or "standard", a.model), call, a.wait)
    imgs = [p["inlineData"] for c in r.get("candidates", [])
            for p in c.get("content", {}).get("parts", []) if "inlineData" in p]
    if not imgs:
        said = " ".join(p.get("text", "") for c in r.get("candidates", [])
                        for p in c.get("content", {}).get("parts", []) if p.get("text")).strip()
        sys.exit(_box("No image this time - Google's safety filter held it back.",
                      "This usually happens when a prompt mentions real people, famous "
                      "characters or brands, or something that reads as unsafe."
                      + (f" Google said: \"{said[:200]}\"" if said else ""),
                      ["Describe the subject in your own words instead of naming a person, "
                       "character or brand.",
                       "Keep it simple first, then add details one at a time.",
                       "Run the command again with the reworded prompt."],
                      ""))
    for path, img in zip(output_paths(a.output, len(imgs), ".png"), imgs):
        path.write_bytes(base64.b64decode(img["data"]))
        print(f"saved {path}")

def imagen(a):
    params = {"sampleCount": a.n, **({"aspectRatio": a.aspect} if a.aspect else {})}
    body = {"instances": [{"prompt": a.prompt}], "parameters": params}
    r = router.run("imagen", router.candidates("imagen", "standard", a.model),
                   lambda m: request("POST", f"models/{m}:predict", body), a.wait)
    preds = r.get("predictions", [])
    if not preds:
        sys.exit(_box("No image this time - Google's safety filter held it back.",
                      "The prompt may mention a real person, a famous character or a brand.",
                      ["Reword the subject in your own words.", "Run the command again."],
                      ""))
    for path, p in zip(output_paths(a.output, len(preds), ".png"), preds):
        path.write_bytes(base64.b64decode(p["bytesBase64Encoded"]))
        print(f"saved {path}")


# ================= video =================
def video(a):
    inst = {"prompt": a.prompt}
    if a.image:
        inst["image"] = {"bytesBase64Encoded": base64.b64encode(Path(a.image).read_bytes()).decode(),
                         "mimeType": mimetypes.guess_type(a.image)[0] or "image/png"}
    params = {k: v for k, v in {"aspectRatio": a.aspect, "negativePrompt": a.negative,
                                "resolution": a.resolution, "durationSeconds": a.seconds}.items() if v}
    body = {"instances": [inst], "parameters": params}
    chain = router.candidates("video", a.tier or "standard", a.model)
    if not a.allow_cheaper and not a.model:
        chain = chain[:1]          # never silently swap a paid video to another model
    used = {}
    def submit(m):
        used["m"] = m
        return request("POST", f"models/{m}:predictLongRunning", body)
    op = router.run("video", chain, submit, a.wait)
    log(f"{used['m']} rendering (usually 1-6 min)", end="")
    t0 = time.time()
    while not op.get("done"):
        time.sleep(10)
        try:
            op = request("GET", op["name"])
        except ModelBusy:
            print("~", end="", file=sys.stderr, flush=True)   # status check hiccup, keep waiting
            continue
        print(".", end="", file=sys.stderr, flush=True)
    print(f" {time.time() - t0:.0f}s", file=sys.stderr)
    if "error" in op:
        why = op["error"].get("message", "")[:200]
        sys.exit(_box("Your video didn't finish this time.",
                      f"Google stopped it partway. Their note: \"{why}\"" if why else
                      "Google stopped it partway without a reason.",
                      ["If it mentions safety or policy: reword the prompt (no real people, "
                       "famous characters or brands).",
                       "Otherwise just run the same command again - one-off failures are common.",
                       "Try a shorter or simpler prompt, or --model veo-3.1-fast-generate-preview."],
                      used["m"]))
    samples = op.get("response", {}).get("generateVideoResponse", {}).get("generatedSamples", [])
    if not samples:
        sys.exit(_box("Your video finished, but Google didn't send a clip back.",
                      "This usually means the safety filter removed it at the end.",
                      ["Reword the prompt (no real people, famous characters or brands).",
                       "Run the command again."],
                      used["m"]))
    for path, s in zip(output_paths(a.output, len(samples), ".mp4"), samples):
        uri = s["video"]["uri"]
        uri += ("&" if "?" in uri else "?") + "alt=media"
        for attempt in range(3):
            try:
                path.write_bytes(request("GET", uri, raw=True)); break
            except ModelBusy:
                log("download busy, retrying..."); time.sleep(5)
        print(f"saved {path}")


# ================= routing =================
def routing(a):
    if a.state:
        d = cfg.load_settings(); d["routing"] = (a.state == "on"); cfg.save_settings(d)
    on = router.routing_enabled()
    print(f"Smart routing is {'ON' if on else 'OFF'}.")
    if on:
        print("  - short text prompts use a lite model (override: --tier standard|pro)")
        print("  - busy / slow / unavailable models fail over to the next in chain")
        print("  - video only fails over with --allow-cheaper")
