"""Tool registry with explicit, enforced contracts.

A tool is a named, schema-validated capability with a declared permission level.
There is no "run arbitrary command" tool, and there never will be a default one.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..hardware import detect
from ..models.store import ModelStore
from ..paths import Paths
from ..profiles import QWEN3_1_7B, assess

Permission = str  # "read" | "write" | "external"

MAX_ARGS_BYTES = 16 * 1024
MAX_OUTPUT_BYTES = 64 * 1024


class ToolError(RuntimeError):
    """A tool rejected its arguments or failed safely."""


@dataclass
class Tool:
    name: str
    description: str
    permission: Permission
    schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]
    #: hard cap on the serialised output handed back to a model
    max_output_bytes: int = MAX_OUTPUT_BYTES

    def to_mcp(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.schema,
        }


@dataclass
class Registry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        if tool.name in self.tools:
            raise ValueError(f"tool {tool.name!r} is already registered")
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self.tools[name]
        except KeyError as exc:
            raise ToolError(f"unknown tool {name!r}") from exc

    def names(self) -> list[str]:
        return sorted(self.tools)

    def describe(self) -> list[dict[str, Any]]:
        return [tool.to_mcp() for tool in (self.tools[n] for n in self.names())]

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self.get(name)
        payload = json.dumps(arguments, ensure_ascii=False)
        if len(payload.encode("utf-8")) > MAX_ARGS_BYTES:
            raise ToolError("arguments exceed the 16 KiB limit")
        _validate_schema(tool.schema, arguments)
        result = tool.handler(arguments)
        encoded = json.dumps(result, ensure_ascii=False, default=str)
        if len(encoded.encode("utf-8")) > tool.max_output_bytes:
            raise ToolError(
                f"tool output exceeded {tool.max_output_bytes} bytes; narrow the request"
            )
        return result


def _validate_schema(schema: dict[str, Any], arguments: dict[str, Any]) -> None:
    """Minimal JSON-Schema subset: type, required, properties, additionalProperties."""
    if not isinstance(arguments, dict):
        raise ToolError("arguments must be an object")
    expected_type = schema.get("type", "object")
    if expected_type != "object":
        raise ToolError("tool schema must describe an object")
    required = schema.get("required", [])
    for key in required:
        if key not in arguments:
            raise ToolError(f"missing required argument {key!r}")
    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        for key in arguments:
            if key not in properties:
                raise ToolError(f"unexpected argument {key!r}")
    for key, value in arguments.items():
        definition = properties.get(key)
        if not definition:
            continue
        declared = definition.get("type")
        if declared == "string" and not isinstance(value, str):
            raise ToolError(f"argument {key!r} must be a string")
        if declared == "integer" and not isinstance(value, int):
            raise ToolError(f"argument {key!r} must be an integer")
        if declared == "boolean" and not isinstance(value, bool):
            raise ToolError(f"argument {key!r} must be a boolean")
        if declared == "array" and not isinstance(value, list):
            raise ToolError(f"argument {key!r} must be an array")
        if "enum" in definition and value not in definition["enum"]:
            raise ToolError(f"argument {key!r} must be one of {definition['enum']}")
        maximum = definition.get("maximum")
        if maximum is not None and isinstance(value, (int, float)) and value > maximum:
            raise ToolError(f"argument {key!r} must be <= {maximum}")


# ---------------------------------------------------------------------------
# Local, safe tools
# ---------------------------------------------------------------------------


def build_registry(paths: Paths, *, allowed_read_roots: list[Path] | None = None) -> Registry:
    """The default tool set: read-only except for journal-style writes (none here)."""
    registry = Registry()
    allowed_roots = [p.resolve() for p in (allowed_read_roots or [])] + [
        (paths.root / "knowledge").resolve(),
    ]

    registry.register(
        Tool(
            name="get_local_time",
            description="Current local date and time on this device.",
            permission="read",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
            handler=lambda _args: {
                "local_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": time.strftime("%Z"),
            },
        )
    )

    registry.register(
        Tool(
            name="get_device_profile",
            description=(
                "Detected hardware and the compute profile this app selected. "
                "Contains no user content."
            ),
            permission="read",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
            handler=lambda _args: _device_profile(),
        )
    )

    registry.register(
        Tool(
            name="list_available_local_models",
            description="Locally installed models with licence and size. No network.",
            permission="read",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
            handler=lambda _args: {
                "installed": [
                    {
                        "id": model.id,
                        "name": model.name,
                        "license": model.license_spdx,
                        "size_bytes": sum(f.size_bytes for f in model.files),
                    }
                    for model in ModelStore(paths).installed()
                ]
            },
        )
    )

    registry.register(
        Tool(
            name="search_local_knowledge_base",
            description=(
                "Full-text search over the locally installed educational knowledge base. "
                "Returns excerpts with file names so the assistant can cite them."
            ),
            permission="read",
            schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "maximum": 10},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=lambda args: _search_knowledge(paths, allowed_roots, args),
        )
    )

    registry.register(
        Tool(
            name="read_user_selected_file",
            description=(
                "Read a text file the user explicitly selected in this session. "
                "Refuses anything outside the selected roots."
            ),
            permission="read",
            schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
            handler=lambda args: _read_selected_file(allowed_roots, args),
        )
    )

    registry.register(
        Tool(
            name="get_benchmark_report",
            description="Latest locally stored evaluation report for this device.",
            permission="read",
            schema={
                "type": "object",
                "properties": {"suite": {"type": "string"}},
                "additionalProperties": False,
            },
            handler=lambda args: _benchmark_report(paths, args),
        )
    )

    return registry


def _device_profile() -> dict[str, Any]:
    hardware = detect()
    assessment = assess(hardware, QWEN3_1_7B)
    return {"hardware": hardware.to_dict(redact=True), "profile": assessment.to_dict()}


def _search_knowledge(paths: Paths, roots: list[Path], args: dict[str, Any]) -> dict[str, Any]:
    """Search the local knowledge base, then the approved markdown folders.

    The knowledge base is the real index (BM25 over words, BM25 over character
    trigrams, RRF fusion, MMR diversification). The folder walk below stays as a
    fallback for the case where nothing has been indexed yet, and is labelled
    ``retriever: substring`` so a caller can tell the two apart instead of
    believing a quality claim that was never made.
    """
    from ..knowledge import KnowledgeBase
    from ..storage import ContentKey

    query = str(args.get("query", "")).strip()
    if not query:
        raise ToolError("query must not be empty")
    limit = max(1, min(int(args.get("limit") or 5), 20))

    base = KnowledgeBase(paths, key=ContentKey.load_or_create(paths.root))
    try:
        indexed = base.search(query, k=limit)
        if indexed:
            return {
                "query": query,
                "retriever": "bm25-word + bm25-trigram + rrf(60) + mmr",
                "results": [
                    {
                        "citation": hit.citation,
                        "source": hit.source,
                        "title": hit.title,
                        "score": round(hit.score, 6),
                        "excerpt": hit.text[:400].strip(),
                    }
                    for hit in indexed
                ],
            }
    finally:
        base.close()

    tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    hits: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lowered = text.lower()
            score = sum(lowered.count(token) for token in tokens)
            if score == 0:
                continue
            snippet_start = max(0, lowered.find(tokens[0]) - 120)
            hits.append(
                {
                    "file": path.name,
                    "score": score,
                    "excerpt": text[snippet_start : snippet_start + 400].strip(),
                }
            )
    hits.sort(key=lambda h: h["score"], reverse=True)
    return {"query": query, "retriever": "substring", "results": hits[:limit]}


def _read_selected_file(roots: list[Path], args: dict[str, Any]) -> dict[str, Any]:
    raw = str(args.get("path", "")).strip()
    if not raw:
        raise ToolError("path must not be empty")
    candidate = Path(raw).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ToolError(f"file not readable: {exc}") from exc
    if not any(resolved == root or root in resolved.parents for root in roots):
        raise ToolError("path is outside the folders the user approved for this session")
    if resolved.stat().st_size > 2 * 1024 * 1024:
        raise ToolError("file is larger than the 2 MiB read limit")
    text = resolved.read_text(encoding="utf-8", errors="replace")
    return {"path": str(resolved), "bytes": len(text.encode("utf-8")), "text": text[:20000]}


def _benchmark_report(paths: Paths, args: dict[str, Any]) -> dict[str, Any]:
    suite = str(args.get("suite") or "hcs-core")
    report = paths.reports / f"{suite}-latest.json"
    if not report.is_file():
        return {"suite": suite, "available": False, "reports_dir": str(paths.reports)}
    data = json.loads(report.read_text(encoding="utf-8"))
    return {
        "suite": suite,
        "available": True,
        "overall": data.get("overall"),
        "dimensions": data.get("dimensions"),
        "created_at": data.get("created_at"),
    }
