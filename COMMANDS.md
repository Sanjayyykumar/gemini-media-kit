# Cheat sheet

Run these from the kit folder. On Windows use `gmk.cmd` or `python gmk.py`; on macOS/Linux use `./gmk`.

## First time
```
gmk set-key --clipboard        # copy your AI Studio key first
gmk key-status
gmk pick-model text
gmk pick-model image
gmk pick-model video
gmk config
```

## Text
```
gmk text "Say hello in one line" --think low
gmk text "Summarise this" --input notes.pdf
gmk chat                       # /file path · /model id · /clear · /exit
```

## Images
```
gmk image "tribal jungle temple at dawn, flat vector" -o out/temple.png
gmk image "same temple, night, fireflies" --input out/temple.png -o out/temple_night.png
gmk image "poster: 'JUNGLE BOXOO' in bold letters" --model nano-banana-pro-preview --aspect 3:4
```

## Video
```
gmk video "slow drone shot over misty jungle, birds chirping" -o out/jungle.mp4
gmk video "the warrior turns and smiles" --image out/warrior.png --aspect 9:16 -o out/reel.mp4
gmk video "..." --model veo-3.1-fast-generate-preview --resolution 720p   # cheap draft
```

## Routing
```
gmk routing                    # status (on by default)
gmk text "long analysis..." --tier pro
gmk image "final poster" --tier pro
gmk video "..." --allow-cheaper   # ok to fall back to fast/lite Veo if busy
gmk routing off
```

## When it's busy or blocked
```
gmk image "..." --wait 5       # keep retrying for up to 5 minutes
set GMK_DEBUG=1                # Windows: show Google's raw error (key masked)
```

## Models
```
gmk models                     # everything your key can use
gmk set-model text gemini-3.5-flash-lite
gmk reset-model all
```

## Open the results (Windows)
```
start out\temple.png
explorer out
```
