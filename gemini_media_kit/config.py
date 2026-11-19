"""Local, private storage: the API key and saved model choices.

Both live OUTSIDE the project folder so they can never be committed:
  Windows : %APPDATA%\\gemini-media-kit\\
  macOS/Linux : $XDG_CONFIG_HOME/gemini-media-kit/ (default ~/.config/...)

config.json   -> {"api_key": "..."}            (owner-only permissions)
settings.json -> {"models": {"image": "..."}}  (no secrets)
"""
from __future__ import annotations
import json, os, re, stat, sys
from pathlib import Path

KINDS = ("text", "image", "imagen", "video")

# Fallback models, used only until the user picks their own (gmk pick-model <kind>).
DEFAULTS = {
    "text":   "gemini-flash-latest",        # Google alias, always points at the current Flash
    "image":  "gemini-nano-banana-2.1",     # Nano Banana; Pro: nano-banana-pro-preview
    "imagen": "imagen-4.0-generate-001",    # legacy - Google retired Imagen 4 on 2026-08-17
    "video":  "veo-3.1-generate-preview",   # cheaper: veo-3.1-fast-generate-preview
}

_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_\-]{35}|AQ\.[0-9A-Za-z_\-.]{20,}")


# ---------- paths ----------
def config_dir() -> Path:
    base = os.environ.get("APPDATA") if os.name == "nt" else os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "gemini-media-kit"

def key_file() -> Path:
    return config_dir() / "config.json"

def settings_file() -> Path:
    return config_dir() / "settings.json"


# ---------- API key ----------
def clean_key(raw: str) -> str:
    """Strip quotes, whitespace and invisible characters; extract the key from stray text."""
    k = "".join(ch for ch in raw if ch.isprintable()).strip().strip("\"'").strip()
    m = _KEY_PATTERN.search(k)
    return m.group(0) if m else k

def key_looks_valid(k: str) -> bool:
    return (k.startswith("AIza") and len(k) == 39) or (k.startswith("AQ.") and len(k) >= 30)

def describe_key(k: str) -> str:
    verdict = "looks valid" if key_looks_valid(k) else "unrecognised format (expected AIza... or AQ....)"
    return f"{len(k)} chars, {k[:4]}...{k[-4:]} - {verdict}"

def key_source() -> str | None:
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(var):
            return f"environment variable {var}"
    return str(key_file()) if key_file().exists() else None

def load_key() -> str:
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(var):
            return clean_key(os.environ[var])
    try:
        return clean_key(json.loads(key_file().read_text())["api_key"])
    except Exception:
        sys.exit("No API key yet. Run `gmk set-key` in your own terminal "
                 "(get a key at https://aistudio.google.com/apikey).")

def save_key(k: str) -> Path:
    p = key_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"api_key": k}))
    try:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return p

def delete_key() -> bool:
    if key_file().exists():
        key_file().unlink()
        return True
    return False


# ---------- model choices ----------
def load_settings() -> dict:
    try:
        return json.loads(settings_file().read_text())
    except Exception:
        return {}

def save_settings(d: dict) -> None:
    settings_file().parent.mkdir(parents=True, exist_ok=True)
    settings_file().write_text(json.dumps(d, indent=2))

def saved_models() -> dict:
    return load_settings().get("models", {})

def model_for(kind: str, override: str | None = None) -> str:
    return override or saved_models().get(kind) or DEFAULTS[kind]

def set_model(kind: str, model: str) -> None:
    d = load_settings()
    d.setdefault("models", {})[kind] = model
    save_settings(d)

def reset_model(kind: str) -> None:
    d = load_settings()
    models = d.setdefault("models", {})
    for k in (KINDS if kind == "all" else (kind,)):
        models.pop(k, None)
    save_settings(d)
