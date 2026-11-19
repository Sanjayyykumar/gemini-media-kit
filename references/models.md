# Models

Google renames and retires models often. Treat this as a guide and check with `gmk models`.

## Defaults (used until the user picks their own)
| Kind | Default | Notes |
|---|---|---|
| text | `gemini-flash-latest` | An alias for the current Flash model, so it doesn't go stale |
| image | `gemini-nano-banana-2.1` | Nano Banana: fast and cheap, good for editing and chaining |
| video | `veo-3.1-generate-preview` | Best quality, with native audio |
| imagen | `imagen-4.0-generate-001` | Retired by Google (2026-08-17); kept for older keys |

## Common alternatives
| Kind | Model | When |
|---|---|---|
| text | `gemini-3.5-flash-lite`, `gemini-flash-lite-latest` | Fastest and cheapest |
| text | `gemini-pro-latest`, `gemini-3.1-pro-preview` | Hard reasoning, long documents |
| image | `nano-banana-pro-preview` | Final art, posters, logos, readable text inside images |
| video | `veo-3.1-fast-generate-preview` | About 4× cheaper; drafts and iterations |
| video | `veo-3.1-lite-generate-preview` | Cheapest; no 4k |

## Approximate cost (verify on Google's pricing page)
- Nano Banana image: about $0.05–0.15 each, depending on size.
- Veo 3.1: about $0.40 per second (fast about $0.10–0.12, lite about $0.05–0.08).

## Routing chains (router.py)
- text lite: flash-lite-latest → 3.5-flash-lite → 3.1-flash-lite → 2.5-flash-lite
- text standard: your model → flash-latest → 3.5-flash → 3-flash-preview → flash-lite-latest
- text pro: pro-latest → 3.1-pro-preview → 2.5-pro → flash-latest
- image: your model → nano-banana-2.1 ↔ nano-banana-pro-preview
- video (only with --allow-cheaper): your model → 3.1-fast → 3.1-lite

## Automatic switching
If Google answers 404 and names a replacement model, the CLI switches to it for that run. The saved choice is not changed.
