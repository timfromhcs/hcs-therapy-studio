"""Policy gate for tool calls.

Every call passes through ``PolicyGate.check`` before execution. The gate is
deterministic, denies by default, and records why. It is the only place that may
decide a side effect is allowed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..storage import Database
from .tools import Registry, Tool, ToolError


class PolicyDenied(PermissionError):
    """Raised when a tool call must not happen."""


@dataclass
class LoopBudget:
    """Hard budgets for one user-initiated action."""

    max_calls: int = 8
    max_seconds: float = 60.0
    max_output_bytes: int = 256 * 1024
    max_repeats: int = 2

    def __post_init__(self) -> None:
        if self.max_calls <= 0:
            raise ValueError("max_calls must be positive")
        if self.max_seconds <= 0:
            raise ValueError("max_seconds must be positive")


@dataclass
class BudgetState:
    budget: LoopBudget
    calls: int = 0
    output_bytes: int = 0
    started: float = field(default_factory=time.monotonic)
    signatures: dict[str, int] = field(default_factory=dict)

    def consume(self, signature: str, output_bytes: int = 0) -> None:
        if self.calls >= self.budget.max_calls:
            raise PolicyDenied(f"tool-call limit reached ({self.budget.max_calls})")
        if time.monotonic() - self.started > self.budget.max_seconds:
            raise PolicyDenied(f"time budget exhausted ({self.budget.max_seconds:.0f}s)")
        repeats = self.signatures.get(signature, 0) + 1
        if repeats > self.budget.max_repeats:
            raise PolicyDenied("repeated identical tool call detected; aborting loop")
        self.signatures[signature] = repeats
        self.calls += 1
        self.output_bytes += output_bytes
        if self.output_bytes > self.budget.max_output_bytes:
            raise PolicyDenied(
                f"total tool output exceeded {self.budget.max_output_bytes} bytes"
            )


DEFAULT_DECISIONS = {"read": "allow", "write": "ask", "external": "ask"}


class PolicyGate:
    def __init__(
        self,
        registry: Registry,
        db: Database,
        *,
        decisions: dict[str, str] | None = None,
        allowed_tools: set[str] | None = None,
    ) -> None:
        self.registry = registry
        self.db = db
        self.decisions = {**DEFAULT_DECISIONS, **(decisions or {})}
        self.allowed_tools = allowed_tools

    def decision_for(self, tool: Tool) -> str:
        stored = self.db.get_preference(f"tool_permission:{tool.name}")
        if stored in {"allow", "ask", "deny"}:
            return stored
        return self.decisions.get(tool.permission, "deny")

    def check(self, name: str, arguments: dict, *, approved: bool = False) -> Tool:
        tool = self.registry.get(name)
        if self.allowed_tools is not None and name not in self.allowed_tools:
            raise PolicyDenied(f"tool {name!r} is not in the allow-list for this session")
        decision = self.decision_for(tool)
        if decision == "deny":
            raise PolicyDenied(f"tool {name!r} is denied by policy")
        if decision == "ask" and not approved:
            raise PolicyDenied(
                f"tool {name!r} ({tool.permission}) requires explicit user approval"
            )
        return tool

    def execute(
        self,
        name: str,
        arguments: dict,
        *,
        state: BudgetState | None = None,
        approved: bool = False,
    ) -> dict:
        import json

        signature = f"{name}:{json.dumps(arguments, sort_keys=True)}"
        try:
            tool = self.check(name, arguments, approved=approved)
            if state is not None:
                state.consume(signature)
            result = self.registry.call(name, arguments)
            size = len(json.dumps(result, default=str).encode("utf-8"))
            if state is not None:
                state.output_bytes += size
            self.db.audit(
                "tool_call",
                "ok",
                tool=name,
                summary=f"permission={tool.permission} bytes={size}",
            )
            return {"ok": True, "tool": name, "result": result}
        except (PolicyDenied, ToolError) as exc:
            self.db.audit(
                "tool_call", "denied" if isinstance(exc, PolicyDenied) else "error", tool=name,
                summary=type(exc).__name__,
            )
            raise
