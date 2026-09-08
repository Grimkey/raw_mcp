"""Smoke test: launch server.py as a subprocess and drive it over stdio.

Run with:  uv run test_server.py
"""

import json
import subprocess
import sys


def main():
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    def request(payload, expect_response=True):
        proc.stdin.write(json.dumps(payload) + "\n")
        proc.stdin.flush()
        if not expect_response:
            return None
        line = proc.stdout.readline()
        return json.loads(line)

    failures = []

    def check(label, condition):
        status = "PASS" if condition else "FAIL"
        print(f"[{status}] {label}")
        if not condition:
            failures.append(label)

    # 1. initialize
    resp = request({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
    })
    check("initialize returns protocolVersion",
          resp["result"]["protocolVersion"] == "2024-11-05")
    check("initialize reports tools capability",
          "tools" in resp["result"]["capabilities"])

    # 2. initialized notification (no response expected)
    request({"jsonrpc": "2.0", "method": "notifications/initialized"},
            expect_response=False)

    # 3. tools/list
    resp = request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = resp["result"]["tools"]
    check("tools/list returns calculate_length",
          any(t["name"] == "calculate_length" for t in tools))

    # 4. tools/call
    resp = request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "calculate_length", "arguments": {"text": "hello"}},
    })
    text = resp["result"]["content"][0]["text"]
    check("calculate_length counts 'hello' as 5", "5 characters" in text)

    # 5. unknown method -> JSON-RPC error
    resp = request({"jsonrpc": "2.0", "id": 4, "method": "does/not/exist"})
    check("unknown method returns error -32601",
          resp.get("error", {}).get("code") == -32601)

    proc.stdin.close()
    proc.wait(timeout=5)

    print("\nServer stderr:")
    print(proc.stderr.read().rstrip())

    if failures:
        print(f"\n{len(failures)} check(s) FAILED")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
