# Changelog

## 1.3.0 (2026-11-20)
- **Built-in MCP server** (`gmk mcp`) with no dependencies: `gemini_text`, `gemini_image` (returns a preview), `gemini_video`, `gemini_models`, `gemini_status`. The key is read from gmk's private config, never from the client config.
- New README with step-by-step setup, MCP instructions for Claude Desktop and Cursor, and troubleshooting.
- Added SECURITY.md, CONTRIBUTING.md and examples/claude_desktop_config.json.

## 1.2.0 (2026-11-20)
- Reads Google's error body: separates **no quota / billing needed**, **rate limit** (waits Google's retryDelay, up to 60s), **overloaded** and **unavailable**.
- Stops early when the quota is project-wide, instead of trying every model.
- `--wait MIN` keeps retrying through busy periods; plain-language summaries; `GMK_DEBUG=1` for raw errors.
- Kinder failure messages: what happened in plain words plus numbered steps (quota, rate limit, busy, unavailable, safety filter, video stopped).
- Skill: falls back to other connected image/video engines when Google blocks generation.

## 1.1.0 (2026-11-20)
- Smart routing (`router.py`): small text tasks go to lite models; busy, silent or unavailable models fail over down a chain.
- `--tier` on text, chat, image and video; `/tier` inside chat; `gmk routing on|off`.
- Streams treat 40s of silence as busy and move on, instead of waiting 2 minutes.
- Video stays on the chosen model unless `--allow-cheaper` is passed.

## 1.0.0 (2026-11-20)
- Restructured into a package (`gemini_media_kit/`) with launchers `gmk.py`, `gmk.cmd` and `gmk`.
- Streamed text output and an interactive `chat` mode; `--think low` for faster answers.
- Saved model choices per kind (`pick-model`, `set-model`, `reset-model`, `config`), grouped `models` list.
- Accepts both key formats (`AIza…`, `AQ.…`), reads the key from the clipboard, and extracts it from stray pasted text.
- Plain-language error hints, key masking, timeouts, and automatic switching when Google retires a model.
- Automatic retry (3s, 8s, 20s) when Google is busy (429/5xx).
- Defaults: `gemini-flash-latest`, `gemini-nano-banana-2.1`, `veo-3.1-generate-preview`.
