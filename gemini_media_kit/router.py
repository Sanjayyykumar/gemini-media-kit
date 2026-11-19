"""Smart routing: pick the right-sized model and fail over when Google is busy.

Two ideas:
1. Task size - small text tasks (short prompt, no files) go to a LITE model:
   faster and cheaper. Bigger work stays on the user's chosen model.
2. Failover - if a model is busy (429/5xx), silent (timeout) or unavailable (404),
   try the next model in its chain. One short retry first, then move on.

The user's saved model is always tried first. `--model X` pins one model (no routing).
`gmk routing off` turns all of this off.
"""
from __future__ import annotations

import sys, time

from . import config as cfg
from .api import ModelBusy, fail, log

# Ordered fallback chains per kind and tier. Only models the key can use will work;
# unavailable ones are skipped automatically (404 -> next).
CHAINS = {
    "text": {
        "lite": ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
                 "gemini-2.5-flash-lite"],
        "standard": ["gemini-flash-latest", "gemini-3.5-flash", "gemini-3-flash-preview",
                     "gemini-flash-lite-latest"],
        "pro": ["gemini-pro-latest", "gemini-3.1-pro-preview", "gemini-2.5-pro",
                "gemini-flash-latest"],
    },
    "image": {
        "standard": ["gemini-nano-banana-2.1", "nano-banana-pro-preview", "gemini-3.1-flash-image"],
        "pro": ["nano-banana-pro-preview", "gemini-nano-banana-2.1", "gemini-3-pro-image"],
    },
    "video": {
        "standard": ["veo-3.1-generate-preview", "veo-3.1-fast-generate-preview",
                     "veo-3.1-lite-generate-preview"],
        "lite": ["veo-3.1-lite-generate-preview", "veo-3.1-fast-generate-preview"],
    },
    "imagen": {"standard": ["imagen-4.0-generate-001"]},
}

SMALL_PROMPT_CHARS = 200


def routing_enabled() -> bool:
    return cfg.load_settings().get("routing", True)


def text_tier(prompt: str, has_files: bool, requested: str | None) -> str:
    """auto: short + no files -> lite; otherwise the user's standard model."""
    if requested and requested != "auto":
        return requested
    if not has_files and len(prompt) <= SMALL_PROMPT_CHARS:
        return "lite"
    return "standard"


def candidates(kind: str, tier: str = "standard", pinned: str | None = None) -> list:
    if pinned:                                # --model X: exactly this model
        return [pinned]
    saved = cfg.saved_models().get(kind)
    chain = list(CHAINS.get(kind, {}).get(tier) or CHAINS[kind]["standard"])
    if tier == "standard":
        first = saved or cfg.DEFAULTS[kind]
        chain = [first] + [m for m in chain if m != first]
    elif saved and saved not in chain:        # keep user's model as a last resort
        chain.append(saved)
    if not routing_enabled():
        return chain[:1] if tier == "standard" else [saved or cfg.DEFAULTS[kind]]
    return chain


BILLING_URL = "https://aistudio.google.com/apikey  (open your project -> Set up billing)"
MAX_AUTO_WAIT = 60        # seconds we wait on our own for a rate limit
_IMAGE_KINDS = ("image", "imagen", "video")


def _countdown(seconds: float, why: str) -> None:
    seconds = int(seconds + 0.5)
    for left in range(seconds, 0, -1):
        print(f"\r[gmk] {why} - retrying in {left:>3}s ", end="", file=sys.stderr, flush=True)
        time.sleep(1)
    print("\r" + " " * 60 + "\r", end="", file=sys.stderr, flush=True)


def _box(title: str, body: str, steps: list, tried: str) -> str:
    lines = ["", f"  {title}", "", f"  {body}", "", "  What you can do:"]
    lines += [f"    {i}. {step}" for i, step in enumerate(steps, 1)]
    lines += (["", f"  (models tried: {tried})"] if tried else []) + [""]
    return "\n".join(lines)


def _explain(kind: str, failures: list) -> str:
    kinds = {f.kind for f in failures}
    tried = ", ".join(dict.fromkeys(f.model for f in failures))
    thing = {"image": "image", "imagen": "image", "video": "video"}.get(kind, "reply")
    rerun = "Run the same command again" if kind != "video" else "Run the same video command again"

    if "no_quota" in kinds and kinds <= {"no_quota", "unavailable"}:
        return _box(
            f"Your {thing} couldn't be created this time, and that's not your fault.",
            f"Your API key works, but Google's free plan doesn't include {thing} generation "
            f"(it allows 0 {thing}s). Text still works for free.",
            ["Open https://aistudio.google.com/apikey and sign in.",
             "Find your key's project and click 'Set up billing' (a small charge per "
             f"{thing}, roughly $0.05-0.15 per image, more for video).",
             "Wait a minute after enabling billing, then " + rerun.lower() + ".",
             "Can't enable billing right now? Ask Claude to make it with another connected "
             "tool (e.g. Higgsfield) using the same prompt."],
            tried)
    if "rate" in kinds:
        waits = [f.retry_after for f in failures if f.retry_after]
        when = f"about {int(max(waits))} seconds" if waits else "a minute"
        return _box(
            f"Almost there - Google just asked us to slow down for a moment.",
            "Your key has a limit on how many requests it can send per minute, "
            "and it's been reached. Nothing is broken.",
            [f"Wait {when}, then {rerun.lower()}.",
             "Or add --wait 5 and gmk will keep trying for up to 5 minutes on its own.",
             "Making lots of images? Space them out, or raise your limits by enabling billing "
             "in AI Studio."],
            tried)
    if kinds == {"unavailable"}:
        return _box(
            f"These models aren't switched on for your key yet.",
            "Google offers different models to different accounts, and the ones we tried "
            "aren't on yours.",
            [f"Run: gmk pick-model {kind}  - it shows only the models your key can use.",
             "Pick one by number; gmk will remember it.",
             rerun + "."],
            tried)
    return _box(
        f"Google is very busy right now, so your {thing} didn't come through.",
        "This happens at peak times and usually clears up within a few minutes. "
        "Your setup and key are fine.",
        ["Add --wait 5 to the same command - gmk will keep retrying for up to 5 minutes.",
         "Or try again in 5-10 minutes.",
         "In a hurry? Ask Claude to use another connected tool (e.g. Higgsfield) with the same prompt."],
        tried)


def run(kind: str, models: list, call, wait_minutes: float = 0):
    """Call `call(model)` down the chain until one succeeds.

    - unavailable (404): skip to the next model
    - overloaded (5xx/timeout): next model
    - rate limit (429 + retry time): wait the time Google asks for (<=60s), retry same model
    - no quota (limit 0 / daily cap): stop early - other models share the same project quota
    - wait_minutes > 0: when the whole chain fails, keep cycling until the deadline
    """
    deadline = time.time() + wait_minutes * 60
    rnd = 0
    while True:
        failures, tried, queue = [], [], list(models)
        while queue:
            model = queue.pop(0)
            if model in tried:
                continue
            tried.append(model)
            try:
                return call(model)
            except ModelBusy as e:
                failures.append(e)
                if e.replacement and e.replacement not in tried:
                    log(f"{model} retired -> {e.replacement}")
                    queue.insert(0, e.replacement)
                    continue
                if e.kind == "rate" and (e.retry_after or 0) <= MAX_AUTO_WAIT:
                    _countdown(e.retry_after or 10, f"{model}: rate limit")
                    try:
                        return call(model)
                    except ModelBusy as e2:
                        failures.append(e2)
                if e.kind == "no_quota":
                    others = [f for f in failures if f.kind == "no_quota"]
                    if len(others) >= 2:            # two models, same answer: it's the project
                        log("quota is project-wide - stopping (other models would fail the same way)")
                        queue.clear()
                        break
                nxt = f" -> trying {queue[0]}" if queue else ""
                log(f"{model}: {e.reason}{nxt}")
        if wait_minutes <= 0 or time.time() >= deadline or \
                all(f.kind in ("no_quota", "unavailable") for f in failures):
            fail("", _explain(kind, failures))
        rnd += 1
        pause = min(15 * rnd, 60, max(5, deadline - time.time()))
        _countdown(pause, f"all busy, round {rnd + 1} (until --wait deadline)")
