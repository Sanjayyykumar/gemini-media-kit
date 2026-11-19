# Gemini Media Kit: a Google AI Studio MCP server and CLI

Use Google's **Gemini** (text), **Nano Banana** (images) and **Veo** (video) from **Claude, Cursor or any MCP app**, or straight from your terminal.

- **Nothing to install:** pure Python, no `pip`, no Node, no extra packages.
- **Your key stays private:** it's saved once on your own computer, never pasted into chat or any app's config.
- **Smart routing:** small tasks go to fast lite models, and if a model is busy the kit switches to another automatically.
- **Friendly errors:** if something can't be generated, you get the reason in plain words plus steps to fix it.

```
gmk text  "explain Veo in two lines"            → streamed answer
gmk image "jungle temple at dawn, flat vector"  → saved .png
gmk video "drone shot over misty jungle"        → saved .mp4
gmk mcp                                         → MCP server for Claude Desktop / Cursor
```

---

## 1. What you need
- **Python 3.8+**. Check with `python --version`; get it from [python.org](https://www.python.org/downloads/) if needed.
- **A Google AI Studio API key**, free to create at https://aistudio.google.com/apikey.
  - Text works on the free plan.
  - **Images and video need billing turned on** for the key's project. Google's free plan allows 0 of them.

## 2. Download
```bash
git clone https://github.com/Sanjayyykumar/gemini-media-kit.git
cd gemini-media-kit
```
Or click **Code → Download ZIP** on GitHub and unzip it.

How to run it, depending on your system:

| System | Command |
|---|---|
| Windows | `gmk.cmd <command>` (or `python gmk.py <command>`) |
| macOS / Linux | `./gmk <command>` (or `python3 gmk.py <command>`) |

The examples below just say `gmk`.

## 3. Save your key (one time)
1. Open https://aistudio.google.com/apikey and click the **copy icon** next to your key.
2. In the `gemini-media-kit` folder, **type** (don't paste) this command:
   ```
   gmk set-key --clipboard
   ```
3. Check it:
   ```
   gmk key-status
   ```
   You should see something like `53 chars, AQ.A...hIBA - looks valid`. The full key is never shown.

> Prefer an environment variable? Set `GEMINI_API_KEY` and gmk will use that instead.

## 4. Test it
```
gmk text "Say hello in one line"
gmk image "tribal jungle temple at dawn, flat vector" -o out/temple.png
```
If the image step says your plan doesn't include images, turn on billing (see step 1), wait a minute and run it again.

## 5. Connect it to Claude Desktop, Cursor or another MCP app
gmk includes an MCP server. Add it to your app's MCP config. **No key goes in this file**, because gmk reads the one you saved in step 3.

**Claude Desktop:** open Settings → Developer → Edit Config, then add:
```json
{
  "mcpServers": {
    "gemini-media-kit": {
      "command": "python",
      "args": ["C:\\full\\path\\to\\gemini-media-kit\\gmk.py", "mcp"]
    }
  }
}
```
- On macOS/Linux, use `"command": "python3"` and a path like `"/Users/you/gemini-media-kit/gmk.py"`.
- On Windows, write the path with double backslashes `\\`, as shown above.
- Restart the app. You'll see these tools:

| Tool | What it does |
|---|---|
| `gemini_text` | Ask Gemini a question; optionally include files or images |
| `gemini_image` | Generate or edit images with Nano Banana; returns the file and a preview |
| `gemini_video` | Generate video with Veo (paid, 1–6 min) |
| `gemini_models` | List the models your key can use |
| `gemini_status` | Check the key and which models are in use (never reveals the key) |

Images and videos made through MCP are saved to `~/Pictures/gemini-media-kit/`. To save them somewhere else, set the `GMK_OUT` environment variable to a folder path.

**Cursor / Windsurf / others:** use the same `command` + `args` in that app's MCP settings.

## 6. Use it from the terminal
| Task | Command |
|---|---|
| Quick answer | `gmk text "your question" [--think low]` |
| Chat (remembers context) | `gmk chat`. In chat: `/file path`, `/model id`, `/tier pro`, `/clear`, `/exit` |
| New image | `gmk image "prompt" [--aspect 16:9] [--tier pro] -o out/name.png` |
| Edit an image | `gmk image "make the sky purple" --input out/name.png` |
| Video | `gmk video "prompt" [--image start.png] [--aspect 9:16] [--resolution 1080p] -o out/clip.mp4` |
| Keep retrying while Google is busy | add `--wait 5` (minutes) |

The full list is in [COMMANDS.md](COMMANDS.md), and prompt ideas are in [examples/prompts.md](examples/prompts.md).

## 7. Choose your models (optional)
```
gmk models               # everything your key can use
gmk pick-model image     # choose from a numbered list - saved until you change it
gmk config               # see current choices
gmk reset-model all      # back to defaults
```
Add `--model <id>` to any command to use a model for that run only. Tiers and costs are in [references/models.md](references/models.md).

## 8. Smart routing
On by default. `gmk routing` shows its status, and `gmk routing off` turns it off.
- **Small tasks go to lite models:** short text prompts with no files use a lite model, which is faster and cheaper. Use `--tier standard` or `--tier pro` for bigger work.
- **Busy models fail over:** overloaded, slow or unavailable models hand over to the next model in the chain.
- **Rate limits:** gmk waits the time Google asks for (up to 60 seconds), then retries.
- **Video is never swapped silently**, because cheaper Veo models give different quality. Add `--allow-cheaper` to allow it.

## 9. When something can't be generated
gmk tells you what happened and what to do next, for example:
```
  Your image couldn't be created this time, and that's not your fault.

  Your API key works, but Google's free plan doesn't include image generation.

  What you can do:
    1. Open https://aistudio.google.com/apikey and sign in.
    2. Find your key's project and click 'Set up billing'.
    3. Wait a minute, then run the same command again.
```

| You see | It means | Fix |
|---|---|---|
| "free plan doesn't include image/video" | No image or video quota on a free key | Turn on billing in AI Studio |
| "Google just asked us to slow down" | Rate limit | Wait, or add `--wait 5` |
| "Google is very busy right now" | Google is overloaded | `--wait 5`, or try again later |
| "models aren't switched on for your key" | Model not available to you | `gmk pick-model <kind>` |
| "safety filter held it back" | Prompt was blocked | Reword it: avoid real people, famous characters and brands |
| Key not valid / 401 | Wrong or garbled key | Copy the key again and run `gmk set-key --clipboard` |

To see Google's raw error, set the environment variable `GMK_DEBUG=1` (`set GMK_DEBUG=1` on Windows). The key stays masked.

## 10. Use it as an AI-agent skill
Copy this folder into your agent's skills directory, for example `~/.claude/skills/gemini-media-kit/`.
[`SKILL.md`](SKILL.md) tells the agent when to use it, how to keep the key safe, and how to recover when generation is blocked.

## Privacy and security
- The key is stored only at `%APPDATA%\gemini-media-kit\config.json` (Windows) or `~/.config/gemini-media-kit/config.json`, with owner-only permissions.
- It's never printed, logged or committed, and it's masked as `***` in errors.
- More detail in [SECURITY.md](SECURITY.md).

## Project layout
```
gemini-media-kit/
├── gmk.py · gmk.cmd · gmk       launchers
├── gemini_media_kit/
│   ├── config.py                key and saved model choices (private, outside the repo)
│   ├── api.py                   HTTP, streaming, error classification, key masking
│   ├── router.py                lite routing, failover chains, friendly messages
│   ├── commands.py              CLI commands
│   ├── cli.py                   argument parsing
│   └── mcp_server.py            MCP server (stdio, zero-dependency)
├── SKILL.md                     agent instructions
├── references/                  models.md · prompting.md
├── examples/                    prompts.md · claude_desktop_config.json
└── COMMANDS.md · CHANGELOG.md · CONTRIBUTING.md · SECURITY.md · LICENSE
```

## FAQ
**Does it support Google Flow?** Flow is a web app with no API. gmk uses the same Veo models directly.

**Who pays?** Google bills your own key. Roughly $0.05–0.15 per image, and Veo is billed per second (see [references/models.md](references/models.md)).

**Model names changed?** Google updates them often. Run `gmk pick-model <kind>`, and gmk also follows Google's "use model X instead" hints automatically.

---
MIT licensed · Not affiliated with Google · Contributions welcome ([CONTRIBUTING.md](CONTRIBUTING.md))
