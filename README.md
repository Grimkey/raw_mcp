# raw_mcp

A minimal [Model Context Protocol](https://modelcontextprotocol.io) server written
in **pure Python** — no MCP SDK, no third-party libraries. It speaks JSON-RPC 2.0
over stdio, which is how MCP clients talk to servers they launch as a subprocess.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (`brew install uv`)

## Layout

- `server.py` — the MCP server (stdlib only)
- `test_server.py` — a smoke test that drives the server through a full handshake
- `pyproject.toml` — uv project metadata (no runtime dependencies)

## Run the tests

```sh
uv run test_server.py
```

## Run the server manually

The server reads JSON-RPC from stdin and writes responses to stdout, so you can
poke at it by hand:

```sh
uv run server.py
```

Then paste a line and press enter:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}
```

Diagnostic logs go to **stderr** so they never corrupt the JSON on stdout.

## Use it from an MCP client

Point any MCP client (Claude Desktop, etc.) at the server via uv. Example
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "raw-mcp": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/Users/jameswhite/conductor/workspaces/raw_mcp/san-salvador"
    }
  }
}
```

## Use it from Claude Code

Register the server with Claude Code's MCP support, then call the tool from a
session.

### Add the server

```sh
claude mcp add raw-mcp -- uv run --directory /Users/jameswhite/conductor/workspaces/raw_mcp/san-salvador server.py
```

- `raw-mcp` is the name it shows up as.
- Everything after `--` is the launch command. Using `uv run --directory <path>`
  means it works regardless of which directory you start Claude Code from. If you
  always launch from this folder, `claude mcp add raw-mcp -- uv run server.py` is
  enough.
- Default scope is `local` (just you, this project). Add `-s user` to make it
  available everywhere, or `-s project` to share it via a committed `.mcp.json`.

### Verify it connected

```sh
claude mcp list          # shows configured servers + connection status
claude mcp get raw-mcp   # shows the launch command for this one
```

`raw-mcp` should report `✔ Connected`.

### Use it

MCP servers are loaded at session startup, so open a fresh interactive Claude Code
session (or restart your current one), then:

- Run `/mcp` — you should see `raw-mcp` connected with one tool,
  `calculate_length`.
- Ask Claude to use it, e.g. *"Use the raw-mcp calculate_length tool on the string
  'hello world'."* The tool is exposed as `mcp__raw-mcp__calculate_length`.

### Remove it when done

```sh
claude mcp remove raw-mcp
```

## The one tool

`calculate_length` — returns the character count of a string.

## How it works

1. **initialize** — the handshake. The server advertises `protocolVersion` and its
   `tools` capability.
2. **notifications/initialized** — the client acknowledges. It's a *notification*
   (no `id`), so the server sends nothing back.
3. **tools/list** — the server returns its tool definitions and JSON schemas.
4. **tools/call** — the client invokes a tool; the server returns `content` blocks.

Adding a tool is two steps: append its definition to `TOOLS`, then handle its name
in `call_tool`.
