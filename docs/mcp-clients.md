# MCP Client Configuration

Sample Librarian's MCP server uses **stdio transport**. The command to run it:

```
Command: /path/to/sample-librarian/.venv/bin/python3
Args:    [/path/to/sample-librarian/mcp_server.py]
```

Replace `/path/to/sample-librarian` with your actual install path throughout.

---

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "librarian": {
      "command": "/path/to/sample-librarian/.venv/bin/python3",
      "args": ["/path/to/sample-librarian/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop. Tools appear prefixed as `librarian__` (e.g., `librarian__librarian_search`).

---

## Cursor

Create or edit `.cursor/mcp.json` in your project root (or `~/.cursor/mcp.json` for global):

```json
{
  "mcpServers": {
    "librarian": {
      "command": "/path/to/sample-librarian/.venv/bin/python3",
      "args": ["/path/to/sample-librarian/mcp_server.py"]
    }
  }
}
```

Restart Cursor. The 9 librarian tools become available in chat and agent mode.

---

## Codex CLI

Codex CLI reads MCP server config from `~/.codex/config.json`:

```json
{
  "mcpServers": {
    "librarian": {
      "command": "/path/to/sample-librarian/.venv/bin/python3",
      "args": ["/path/to/sample-librarian/mcp_server.py"]
    }
  }
}
```

Or pass inline:

```bash
codex --mcp-server 'librarian:/path/to/sample-librarian/.venv/bin/python3 /path/to/sample-librarian/mcp_server.py'
```

---

## OpenClaw

Add to your OpenClaw MCP config (typically `~/.openclaw/mcp.json` or your project's config):

```json
{
  "mcpServers": {
    "librarian": {
      "command": "/path/to/sample-librarian/.venv/bin/python3",
      "args": ["/path/to/sample-librarian/mcp_server.py"]
    }
  }
}
```

---

## Hermes Agent

Edit `~/.hermes/profiles/<profile>/config.yaml`:

```yaml
mcp_servers:
  librarian:
    command: /path/to/sample-librarian/.venv/bin/python3
    args:
      - /path/to/sample-librarian/mcp_server.py
```

Register alongside LiveAgent for full Ableton integration:

```yaml
mcp_servers:
  liveagent:
    command: /path/to/live-agent-remote/.venv/bin/python3
    args:
      - /path/to/live-agent-remote/mcp_server.py
  librarian:
    command: /path/to/sample-librarian/.venv/bin/python3
    args:
      - /path/to/sample-librarian/mcp_server.py
```

Tools are namespaced by server key: `mcp_liveagent_*` and `mcp_liveagent_librarian_*` (or whichever prefix the client uses).

---

## Verifying the Connection

After configuring any client, verify the server starts:

```bash
/path/to/sample-librarian/.venv/bin/python3 /path/to/sample-librarian/mcp_server.py
```

Should run without errors. If `mcp` package is missing:

```bash
.venv/bin/pip install mcp
```

The server logs to stderr — check your client's MCP logs if tools don't appear.
