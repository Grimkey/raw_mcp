"""A minimal MCP server implemented with only the Python standard library.

It speaks JSON-RPC 2.0 over stdio (newline-delimited JSON), which is the
transport MCP clients use when they launch a server as a subprocess.
"""

import sys
import json

PROTOCOL_VERSION = "2024-11-05"


def send(payload):
    """Serialize a JSON-RPC message to stdout as one newline-delimited line."""
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def send_result(message_id, result):
    """Send a successful JSON-RPC response."""
    send({"jsonrpc": "2.0", "id": message_id, "result": result})


def send_error(message_id, code, message):
    """Send a JSON-RPC error response."""
    send({"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}})


def log(message):
    """Log to stderr so we never corrupt the JSON-RPC stream on stdout."""
    sys.stderr.write(f"[raw-mcp] {message}\n")
    sys.stderr.flush()


# --- Tool definitions -------------------------------------------------------

TOOLS = [
    {
        "name": "calculate_length",
        "description": "Returns the character count of a string",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
    },
]


def call_tool(name, args):
    """Dispatch a tool call and return an MCP tool result dict."""
    if name == "calculate_length":
        text_input = args.get("text", "")
        length = len(text_input)
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"The string '{text_input}' has {length} characters.",
                }
            ]
        }
    # Unknown tool: report it as a tool error rather than a protocol error.
    return {
        "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
        "isError": True,
    }


# --- Message routing --------------------------------------------------------

def handle_message(line):
    """Parse and route a single JSON-RPC message."""
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        log(f"Ignoring non-JSON line: {line!r}")
        return

    method = msg.get("method")
    msg_id = msg.get("id")
    # Notifications have no "id" and must never receive a response.
    is_notification = "id" not in msg

    if method == "initialize":
        send_result(msg_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "raw-mcp", "version": "1.0.0"},
        })

    elif method == "notifications/initialized":
        # Client acknowledging the handshake; nothing to send back.
        pass

    elif method == "tools/list":
        send_result(msg_id, {"tools": TOOLS})

    elif method == "tools/call":
        params = msg.get("params", {})
        result = call_tool(params.get("name"), params.get("arguments", {}))
        send_result(msg_id, result)

    elif method == "ping":
        send_result(msg_id, {})

    else:
        if not is_notification:
            send_error(msg_id, -32601, f"Method not found: {method}")
        else:
            log(f"Ignoring unknown notification: {method}")


def main():
    log("Server started, waiting for messages on stdin.")
    for line in sys.stdin:
        if line.strip():
            handle_message(line)
    log("stdin closed, shutting down.")


if __name__ == "__main__":
    main()
