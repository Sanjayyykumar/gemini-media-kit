---
name: gemini-media-kit
description: Use when asked to generate or edit images or video with Google models (Nano Banana, Imagen, Veo) or to call Gemini, via the zero-dependency gmk.py CLI.
---

# Gemini Media Kit

`gmk` is a stdlib-only Python CLI (3.8+) for Google's Gemini API: streamed text and chat, Nano Banana images, and Veo video. It lives in this folder: run `python gmk.py <command>`, or `gmk.cmd` / `./gmk`.

## Hard rules: the API key
- Never ask for the key in chat. Never print, log, read, copy or commit it, and never put it on a command line.
- Start with `gmk key-status`. If no key is saved, tell the user to run `gmk set-key --clipboard` in their own terminal.
- The key and settings live outside the project (`%APPDATA%\gemini-media-kit\` or `~/.config/gemini-media-kit/`). Don't open those files.

## Two ways to use it
- **MCP tools** (if connected): `gemini_text`, `gemini_image`, `gemini_video`, `gemini_models`, `gemini_status`. Prefer these when available.
- **CLI:** `python gmk.py <command>` on the user's machine.

## Where to run
On the user's machine (device shell). Cloud sandboxes usually can't reach Google's API.

## Pick the command
| Need | Command |
|---|---|
| Quick answer, or analyse a file | `text "<prompt>" [--input file...] [--think low]` |
| Conversation | `chat` (the user drives it; don't use it for agent work) |
| New image | `image "<prompt>" [--aspect 16:9] -o out/<name>.png` |
| Edit image / keep a character consistent | `image "<change>" --input <ref.png> -o out/<name>.png` |
| Video | `video "<prompt>" [--image start.png] [--aspect 9:16] [--resolution 1080p] -o out/<name>.mp4` |

## Models
- `config` shows what each kind uses. **Respect the user's saved choices**; change them (`set-model`, `pick-model`, `reset-model`) only when asked.
- For a one-off model, pass `--model <id>`. To see what's available, run `models`.
- Details and tiers: [references/models.md](references/models.md).

## Smart routing (on by default)
- **Task size:** text prompts of 200 characters or less with no files go to a lite model automatically. Use `--tier standard` or `--tier pro` for real work: analysis, long writing, code.
- **Failover:** busy (429/5xx), silent (timeout) or unavailable (404) models fall through a chain to the next model within seconds.
- **Video never switches models silently.** Add `--allow-cheaper` only if the user agrees to fall back to fast/lite Veo.
- `--model X` pins exactly one model. `gmk routing off|on` turns routing off or on. The chains are in `gemini_media_kit/router.py`.
- Pick the tier yourself: lite for titles, short rewrites and quick facts; standard for most work; pro for hard reasoning and final copy. For images, use `--tier pro` (Nano Banana Pro) for final art or text in images.

## Workflow
1. Clarify the brief: subject, style, aspect ratio, length, where it will be used.
2. Write the prompt with [references/prompting.md](references/prompting.md).
3. Images: generate, review, then refine with `--input` rather than starting over.
4. Video: it's slow and **billed per second**. Confirm before long or batch runs. For consistency, make a Nano Banana keyframe first, then `video --image`.
5. Save into `out/` with descriptive names, then show or send the result.

## When generation is blocked (never leave the user empty-handed)
gmk reads Google's real reason and says it in plain words:
- **"isn't included in your key's current plan"**: the free tier allows 0 images or videos. Don't retry. Tell the user once that billing unlocks it, then **offer another engine right away**: any connected image or video tool (for example Higgsfield or ElevenLabs creative tools), or the user's media-studio router. Write the same prompt for that engine.
- **Rate limit**: gmk waits the time Google asks for (up to 60s) by itself. For longer waits, rerun with `--wait 5`.
- **Overloaded**: rerun with `--wait 5`, or switch engines if the user is in a hurry.
- Raw error for debugging: set env `GMK_DEBUG=1`. The key stays masked.
Keep the tone calm: it's Google's limit, not the user's fault, and there's always a next step.

## Errors
The CLI prints a plain-language hint for each HTTP error. In short: 401 means re-save the key; 404 means `pick-model`; 403/429 means billing or quota; no image back means a safety block, so rephrase (no real people or copyrighted characters).

Google Flow has no API. `video` uses the same Veo models. Only drive Flow in a browser if the user wants its editor.
