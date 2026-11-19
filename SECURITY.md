# Security

- Your Gemini API key is stored only on your computer, outside this project:
  `%APPDATA%\gemini-media-kit\config.json` (Windows) or `~/.config/gemini-media-kit/config.json` (macOS/Linux).
- gmk never prints or logs the key, and masks it as `***` in error messages.
- The MCP server reads the key from that file, so it never needs to go into Claude's or Cursor's config.
- Never commit keys. `.gitignore` already blocks `config.json`, `.env` and `*.key`.
- If a key leaks, delete it at https://aistudio.google.com/apikey, create a new one, and run `gmk set-key --clipboard`.

Found a security issue in gmk itself? Please open a private security advisory on GitHub rather than a public issue.
