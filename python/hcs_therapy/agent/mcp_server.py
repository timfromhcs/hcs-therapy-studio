"""Minimal, strict MCP server over stdio.

Only registered tools are exposed. Every call goes through the policy gate, gets
a loop budget, and produces an audit row. Protocol traffic goes to stdout; every
diagnostic goes to stderr, because a stray ``print`` on stdout corrupts the
transport.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .. import __version__
from ..paths import paths as resolve_paths
from ..storage import Database
from .policy import BudgetState, LoopBudget, PolicyDenied, PolicyGate
from .tools import Registry, ToolError, build_registry

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "hcs-therapy-mcp", "version": __version__}


def _log(message: str) -> None:
    print(f"[hcs-therapy-mcp] {message}", file=sys.stderr, flush=True)


def _error(id_: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _result(id_: Any, payload: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "result": payload}


class McpServer:
    def __init__(self, registry: Registry, gate: PolicyGate, db: Database) -> None:
        self.registry = registry
        self.gate = gate
        self.db = db
        self.budget = BudgetState(LoopBudget(max_calls=32, max_seconds=300.0))
        self._handlers = {
            "initialize": self._initialize,
            "notifications/initialized": self._noop,
            "ping": lambda _params: {},
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "shutdown": lambda _params: {},
        }

    # -- protocol ----------------------------------------------------------
    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        id_ = message.get("id")
        params = message.get("params") or {}
        if not isinstance(method, str):
            return _error(id_, -32600, "invalid request: method must be a string")
        handler = self._handlers.get(method)
        if handler is None:
            return _error(id_, -32601, f"method not found: {method}")
        try:
            payload = handler(params if isinstance(params, dict) else {})
        except PolicyDenied as exc:
            return _error(id_, -32001, str(exc))
        except ToolError as exc:
            return _error(id_, -32602, str(exc))
        except Exception as exc:  # noqa: BLE001 - protocol must not die on one bad call
            _log(f"internal error in {method}: {type(exc).__name__}")
            return _error(id_, -32603, f"internal error: {type(exc).__name__}")
        if id_ is None:
            return None
        return _result(id_, payload or {})

    # -- methods -----------------------------------------------------------
    def _initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        client = params.get("clientInfo") or {}
        _log(f"initialize from {client.get('name', 'unknown')}")
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": (
                "Local-only wellbeing studio tools. Read-only by default. "
                "No shell, no network, no unrestricted file access."
            ),
        }

    def _noop(self, _params: dict[str, Any]) -> None:
        return None

    def _tools_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        return {"tools": self.registry.describe()}

    def _tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            raise ToolError("name must be a string")
        if not isinstance(arguments, dict):
            raise ToolError("arguments must be an object")
        outcome = self.gate.execute(name, arguments, state=self.budget)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(outcome["result"], ensure_ascii=False, indent=2),
                }
            ],
            "isError": False,
        }


def run(stdin=None, stdout=None, paths_root: str | None = None) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    resolved = resolve_paths(paths_root)
    resolved.ensure()
    db = Database(resolved, encrypt=True)
    registry = build_registry(resolved)
    gate = PolicyGate(registry, db)
    server = McpServer(registry, gate, db)
    _log(f"ready: {len(registry.names())} tools, data at {resolved.root}")

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(json.dumps(_error(None, -32700, "parse error")) + "\n")
            stdout.flush()
            continue
        if isinstance(message, list):  # batch
            responses = [r for r in (server.handle(m) for m in message) if r is not None]
            if responses:
                stdout.write(json.dumps(responses) + "\n")
        else:
            response = server.handle(message)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        stdout.flush()
    db.close()
    return 0


def main() -> int:
    try:
        return run()
    except KeyboardInterrupt:  # pragma: no cover
        return 130
    except Exception as exc:  # noqa: BLE001
        _log(f"fatal: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
