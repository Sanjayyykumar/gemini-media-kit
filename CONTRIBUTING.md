# Contributing

Thanks for helping!

- Keep it **zero-dependency**: Python standard library only, Python 3.8+.
- Code layout: `config.py` (key and settings), `api.py` (HTTP), `router.py` (routing and failover), `commands.py` (CLI commands), `cli.py` (arguments), `mcp_server.py` (MCP tools).
- New Google models usually only need an update to `CHAINS` in `router.py` and `DEFAULTS` in `config.py`.
- User-facing failures should stay kind and actionable: use `_box(title, body, steps, tried)`.
- Never log or print the API key.
- Run `python gmk.py -h` and a quick `python gmk.py mcp` handshake before opening a PR.
