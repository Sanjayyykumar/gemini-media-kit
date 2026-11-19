# Prompting guide

## Images (Nano Banana)
Formula: **subject + action/pose + setting + style + lighting + composition + details**.

> A young tribal warrior girl holding a glowing gem, standing on a jungle temple step,
> flat vector illustration, warm sunrise backlight, centered, wide shot, clean background.

- Name the style precisely: "flat vector", "watercolor", "3D clay render", "children's colouring-book line art, no shading".
- Text inside images: put the exact words in quotes, keep them short, and prefer the Pro model.
- Editing: say only what changes ("make the sky purple, keep everything else identical") and pass the source with `--input`.
- Consistency: approve one reference image, then always pass it with `--input` for new poses or scenes.

## Video (Veo)
Formula: **shot type + subject + action + setting + camera move + lighting/mood + audio**.

> Slow aerial drone shot gliding over a misty tropical jungle at sunrise, golden light through fog,
> camera drifts forward, birds chirping and distant waterfall sound, cinematic, no text.

- Describe one shot per clip. Stitch multiple clips together afterwards.
- Add audio cues: ambience, sound effects, or short dialogue in quotes.
- Use `--negative` for things to avoid: "text, watermark, blurry, extra limbs".
- Image-to-video: create the first frame with `image`, then `video --image frame.png "what moves"`.
- Vertical for reels and shorts: `--aspect 9:16`.

## Text
- Be explicit about the format you want ("3 bullet points", "a JSON array").
- Use `--think low` for quick factual or creative replies. Use the default or `high` for analysis.
