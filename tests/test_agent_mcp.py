"""Tool registry, policy gate, budgets and the MCP protocol."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from hcs_therapy.agent.mcp_server import McpServer, run
from hcs_therapy.agent.policy import (
    BudgetState,
    LoopBudget,
    PolicyDenied,
    PolicyGate,
)
from hcs_therapy.agent.tools import Registry, Tool, ToolError, build_registry
from hcs_therapy.storage import Database


@pytest.fixture
def db(paths) -> Database:
    database = Database(paths, encrypt=True)
    yield database
    database.close()


@pytest.fixture
def registry(paths) -> Registry:
    return build_registry(paths)


def test_default_tools_are_read_only(paths) -> None:
    registry = build_registry(paths)
    assert "get_local_time" in registry.names()
    for name in registry.names():
        assert registry.get(name).permission == "read"


def test_no_shell_or_delete_tool_is_exposed(paths) -> None:
    names = set(build_registry(paths).names())
    forbidden = {"run_command", "shell", "powershell", "delete_file", "rm", "exec"}
    assert names.isdisjoint(forbidden)


def test_schema_validation_rejects_missing_argument(registry) -> None:
    with pytest.raises(ToolError, match="missing required"):
        registry.call("search_local_knowledge_base", {})


def test_schema_validation_rejects_wrong_type(registry) -> None:
    with pytest.raises(ToolError, match="string"):
        registry.call("search_local_knowledge_base", {"query": 5})


def test_schema_validation_rejects_extra_argument(registry) -> None:
    with pytest.raises(ToolError, match="unexpected"):
        registry.call("get_local_time", {"nonsense": 1})


def test_unknown_tool_is_rejected(registry) -> None:
    with pytest.raises(ToolError, match="unknown tool"):
        registry.call("destroy_everything", {})


def test_get_local_time_works(registry) -> None:
    result = registry.call("get_local_time", {})
    assert "local_time" in result


def test_duplicate_registration_fails() -> None:
    registry = Registry()
    tool = Tool("a", "d", "read", {"type": "object"}, lambda _a: {})
    registry.register(tool)
    with pytest.raises(ValueError):
        registry.register(tool)


def test_reading_outside_allowed_roots_is_refused(paths, tmp_path: Path) -> None:
    outside = tmp_path / "secret.txt"
    outside.write_text("nope", encoding="utf-8")
    registry = build_registry(paths, allowed_read_roots=[paths.root / "knowledge"])
    with pytest.raises(ToolError, match="outside"):
        registry.call("read_user_selected_file", {"path": str(outside)})


def test_reading_inside_allowed_root_works(paths) -> None:
    approved = paths.root / "knowledge"
    approved.mkdir(parents=True, exist_ok=True)
    target = approved / "note.md"
    target.write_text("erlaubt", encoding="utf-8")
    registry = build_registry(paths, allowed_read_roots=[approved])
    result = registry.call("read_user_selected_file", {"path": str(target)})
    assert result["text"] == "erlaubt"


# ---------------------------------------------------------------------------
# policy gate
# ---------------------------------------------------------------------------


def test_read_tools_allowed_by_default(registry, db) -> None:
    gate = PolicyGate(registry, db)
    outcome = gate.execute("get_local_time", {})
    assert outcome["ok"] is True
    assert db.audit_events()[0]["tool"] == "get_local_time"


def test_policy_can_deny_a_read_tool(registry, db) -> None:
    db.set_preference("tool_permission:get_local_time", "deny")
    gate = PolicyGate(registry, db)
    with pytest.raises(PolicyDenied, match="denied"):
        gate.execute("get_local_time", {})


def test_ask_requires_approval(registry, db) -> None:
    db.set_preference("tool_permission:get_local_time", "ask")
    gate = PolicyGate(registry, db)
    with pytest.raises(PolicyDenied, match="approval"):
        gate.execute("get_local_time", {})
    assert gate.execute("get_local_time", {}, approved=True)["ok"] is True


def test_session_allow_list_is_enforced(registry, db) -> None:
    gate = PolicyGate(registry, db, allowed_tools={"get_device_profile"})
    with pytest.raises(PolicyDenied, match="allow-list"):
        gate.execute("get_local_time", {})


def test_budget_call_limit(registry, db) -> None:
    gate = PolicyGate(registry, db)
    state = BudgetState(LoopBudget(max_calls=2, max_seconds=30))
    gate.execute("get_local_time", {}, state=state)
    gate.execute("get_local_time", {}, state=state)
    with pytest.raises(PolicyDenied, match="limit"):
        gate.execute("get_local_time", {}, state=state)


def test_repeated_identical_call_aborts(registry, db) -> None:
    gate = PolicyGate(registry, db)
    state = BudgetState(LoopBudget(max_calls=10, max_repeats=2))
    gate.execute("get_local_time", {}, state=state)
    gate.execute("get_local_time", {}, state=state)
    with pytest.raises(PolicyDenied, match="repeated"):
        gate.execute("get_local_time", {}, state=state)


def test_budget_time_limit() -> None:
    # Wall-clock dependence made this flaky: Windows' default timer granularity
    # is ~15.6 ms, so sleeping 10 ms can read as 0 ms elapsed and the test fails
    # only on a busy machine. The state can be aged explicitly instead.
    import time as _time

    state = BudgetState(LoopBudget(max_calls=5, max_seconds=0.001), started=_time.monotonic() - 1.0)
    with pytest.raises(PolicyDenied, match="time budget"):
        state.consume("x")


def test_denied_calls_are_audited(registry, db) -> None:
    db.set_preference("tool_permission:get_local_time", "deny")
    gate = PolicyGate(registry, db)
    with pytest.raises(PolicyDenied):
        gate.execute("get_local_time", {})
    assert db.audit_events()[0]["status"] == "denied"


# ---------------------------------------------------------------------------
# MCP protocol
# ---------------------------------------------------------------------------


@pytest.fixture
def server(registry, db) -> McpServer:
    return McpServer(registry, PolicyGate(registry, db), db)


def test_initialize_handshake(server) -> None:
    response = server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"clientInfo": {"name": "t"}}}
    )
    assert response["result"]["protocolVersion"]
    assert response["result"]["capabilities"]["tools"]


def test_tools_list(server) -> None:
    response = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [t["name"] for t in response["result"]["tools"]]
    assert "get_local_time" in names
    for tool in response["result"]["tools"]:
        assert tool["inputSchema"]["type"] == "object"


def test_tools_call(server) -> None:
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_local_time", "arguments": {}},
        }
    )
    assert response["result"]["isError"] is False
    assert "local_time" in response["result"]["content"][0]["text"]


def test_tools_call_policy_denial_is_a_protocol_error(server, db) -> None:
    db.set_preference("tool_permission:get_local_time", "deny")
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "get_local_time", "arguments": {}},
        }
    )
    assert response["error"]["code"] == -32001


def test_unknown_method(server) -> None:
    response = server.handle({"jsonrpc": "2.0", "id": 5, "method": "nope"})
    assert response["error"]["code"] == -32601


def test_notifications_get_no_response(server) -> None:
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_stdio_transport_roundtrip() -> None:
    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        + "\n"
    )
    stdout = io.StringIO()
    assert run(stdin=stdin, stdout=stdout) == 0
    lines = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
    assert lines[0]["result"]["serverInfo"]["name"] == "hcs-therapy-mcp"
    assert lines[1]["result"]["tools"]


def test_malformed_json_is_reported_not_fatal() -> None:
    stdin = io.StringIO("not json\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n")
    stdout = io.StringIO()
    assert run(stdin=stdin, stdout=stdout) == 0
    lines = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
    assert lines[0]["error"]["code"] == -32700
    assert lines[1]["result"] == {}
