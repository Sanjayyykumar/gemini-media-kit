"""Command-line interface: `gmk <command> [options]`."""
import argparse

from . import __version__, commands as c
from .config import KINDS

EXAMPLES = """examples:
  gmk set-key --clipboard                 save your key (copy it first)
  gmk pick-model image                    choose a model, saved until changed
  gmk text "explain Veo in 2 lines" --think low
  gmk chat
  gmk image "jungle temple at dawn, flat vector" -o out/temple.png
  gmk image "make the sky purple" --input out/temple.png
  gmk video "drone shot over misty jungle, birds chirping" --aspect 9:16
"""


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gmk", epilog=EXAMPLES,
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                description="Gemini Media Kit - Gemini, Nano Banana and Veo from your terminal.")
    p.add_argument("--version", action="version", version=f"gmk {__version__}")
    sp = p.add_subparsers(dest="cmd", required=True, metavar="<command>")

    def add(name, fn, help_):
        s = sp.add_parser(name, help=help_)
        s.set_defaults(func=fn)
        return s

    # key
    s = add("set-key", c.set_key, "save your API key privately on this computer")
    s.add_argument("--clipboard", action="store_true", help="read the key from the clipboard")
    add("key-status", c.key_status, "check the saved key (never shows it)")
    add("delete-key", c.delete_key, "remove the saved key")

    # models
    add("config", c.show_config, "show key location and the model used for each kind")
    add("models", c.models, "list every model your key can use, grouped by kind")
    s = add("pick-model", c.pick_model, "choose a model from a numbered list (saved)")
    s.add_argument("kind", choices=KINDS)
    s = add("set-model", c.set_model, "save a model by name")
    s.add_argument("kind", choices=KINDS); s.add_argument("model")
    s = add("reset-model", c.reset_model, "go back to the default model")
    s.add_argument("kind", choices=KINDS + ("all",))
    def _mcp(a):
        from .mcp_server import serve
        serve()
    add("mcp", _mcp, "run as an MCP server (stdio) for Claude Desktop, Cursor, etc.")
    s = add("routing", c.routing, "smart routing on/off (lite for small tasks, failover when busy)")
    s.add_argument("state", nargs="?", choices=["on", "off"])

    # text
    for name, fn, h in (("text", c.text, "one answer, streamed word by word"),
                        ("chat", c.chat, "interactive chat that remembers the conversation")):
        s = add(name, fn, h)
        if name == "text":
            s.add_argument("prompt")
            s.add_argument("--input", nargs="*", metavar="FILE", help="files/images to include")
        s.add_argument("--model", help="use this model for this run only")
        s.add_argument("--think", choices=["low", "medium", "high"], help="low = faster")
        s.add_argument("--tier", choices=["auto", "lite", "standard", "pro"],
                       help="model size; auto (default) sends small tasks to lite")

    # images
    s = add("image", c.image, "generate or edit an image (Nano Banana)")
    s.add_argument("prompt")
    s.add_argument("--input", nargs="*", metavar="FILE", help="image(s) to edit or use as reference")
    s.add_argument("--aspect", help="e.g. 1:1, 16:9, 9:16, 4:3")
    s.add_argument("-o", "--output", help="file path (default out/gmk_<time>.png)")
    s.add_argument("--model")
    s.add_argument("--tier", choices=["standard", "pro"], help="pro = Nano Banana Pro first")
    s = add("imagen", c.imagen, "legacy Imagen 4 (retired by Google, kept for old keys)")
    s.add_argument("prompt"); s.add_argument("-n", type=int, default=1)
    s.add_argument("--aspect"); s.add_argument("-o", "--output"); s.add_argument("--model")

    # video
    s = add("video", c.video, "generate a video with Veo (paid, 1-6 min)")
    s.add_argument("prompt")
    s.add_argument("--image", help="start frame image")
    s.add_argument("--aspect", help="16:9 or 9:16")
    s.add_argument("--resolution", help="720p, 1080p or 4k")
    s.add_argument("--seconds", type=int, help="clip length")
    s.add_argument("--negative", help="things to avoid")
    s.add_argument("-o", "--output", help="file path (default out/gmk_<time>.mp4)")
    s.add_argument("--model")
    s.add_argument("--tier", choices=["standard", "lite"], help="lite = cheapest Veo first")
    s.add_argument("--allow-cheaper", action="store_true",
                   help="if busy, fall back to fast/lite Veo instead of failing")
    for name in ("text", "image", "imagen", "video"):
        sp.choices[name].add_argument("--wait", type=float, default=0, metavar="MIN",
            help="if Google is busy, keep retrying for up to MIN minutes")
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
