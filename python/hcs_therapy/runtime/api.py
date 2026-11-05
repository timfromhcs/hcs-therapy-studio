"""Loopback-only local HTTP API.

Security posture (build contract §8.4):

* binds ``127.0.0.1`` explicitly — never ``0.0.0.0``;
* every endpoint except ``/health`` and ``/version`` requires a per-launch
  bearer token generated with :func:`secrets.token_urlsafe`;
* CORS is an explicit allow-list; a hostile browser origin is rejected, not
  merely denied credentials;
* request bodies are size-capped and parsed as strict JSON;
* side-effecting routes require a confirmation flag in the body and produce an
  audit row with metadata only;
* prompts and journal content never appear in the log file.
"""

from __future__ import annotations

import contextlib
import json
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .. import __version__
from ..hardware import HardwareReport, detect
from ..knowledge import KnowledgeBase, citations_in, missing_citations
from ..models.store import ModelStore, StoreError
from ..paths import Paths
from ..profiles import Assessment
from ..profiles import assess as assess_profile
from ..safety import (
    analyse_register,
    fallback_after_scan,
    register_anchor,
    resolve_region,
    resources_dict,
    scan_output,
    system_prompt,
)
from ..safety import (
    assess as assess_crisis,
)
from ..safety import (
    decide as decide_policy,
)
from ..storage import Database
from .llama_server import LOOPBACK, LlamaServer, find_server_binary

MAX_BODY_BYTES = 1024 * 1024
DEFAULT_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://hcs-therapy-studio.vercel.app",
    "tauri://localhost",
)

Route = tuple[str, re.Pattern[str], str]


@dataclass
class ServerConfig:
    paths: Paths
    token: str
    origins: tuple[str, ...] = DEFAULT_ORIGINS
    hardware: HardwareReport | None = None
    profile: Assessment | None = None
    model_id: str | None = None
    backend_port: int | None = None
    backend_key: str | None = None
    locale: str = "de"
    region: str | None = None
    encrypt: bool = True
    # Qwen3-class models emit a long private reasoning phase before the first
    # visible token. Measured on this machine: 13.3 s of silence for a single
    # German reply, versus 0.5 s with thinking disabled. A conversation partner
    # that pauses for 13 seconds is unusable, and the scratchpad is not a reply
    # (AGENTS.md §6.5), so it is off by default and configurable.
    thinking: bool = False
    state: dict[str, Any] = field(default_factory=dict)


class StudioState:
    """Everything a request handler may touch."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.paths = config.paths.ensure()
        self.store = ModelStore(self.paths)
        self.hardware = config.hardware or detect()
        self.db = Database(self.paths, encrypt=config.encrypt)
        self.knowledge = KnowledgeBase(self.paths, key=self.db.key)
        if config.profile is None:
            geometry = None
            model_bytes = int(1.05 * 1024**3)
            if config.model_id:
                try:
                    manifest = self.store.manifest(config.model_id)
                    model_bytes = manifest.total_size_bytes or model_bytes
                    if manifest.geometry:
                        from ..profiles import ModelGeometry

                        geometry = ModelGeometry(
                            n_layers=manifest.geometry.n_layers,
                            n_kv_heads=manifest.geometry.n_kv_heads,
                            head_dim=manifest.geometry.head_dim,
                            n_params=manifest.geometry.n_params,
                        )
                except StoreError:
                    pass
            from ..profiles import QWEN3_1_7B

            config.profile = assess_profile(
                self.hardware, geometry or QWEN3_1_7B, model_bytes
            )
        self.profile = config.profile
        self.backend = LlamaServer(
            binary=find_server_binary(self.paths) or Path("llama-server"),
            config=_backend_config(config, self),
            paths=self.paths,
        )
        self._lock = threading.Lock()

    # -- helpers -----------------------------------------------------------
    def backend_healthy(self) -> bool:
        """Probe the inference backend over HTTP.

        The API does not own the sidecar process: ``serve --start-backend`` owns
        it, and a user may run their own. Ownership is irrelevant here — what
        matters is whether the port answers.
        """
        port = self.config.backend_port
        if not port:
            return False
        headers = {}
        if self.config.backend_key:
            headers["Authorization"] = f"Bearer {self.config.backend_key}"
        request = urllib.request.Request(
            f"http://{LOOPBACK}:{port}/health", headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:  # noqa: S310 loopback
                return response.status == 200
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    def device_report(self) -> dict[str, Any]:
        return {
            "hardware": self.hardware.to_dict(redact=True),
            "profile": self.profile.to_dict() if self.profile else None,
        }

    def models_report(self) -> dict[str, Any]:
        installed = {m.id: m for m in self.store.installed()}
        items = []
        for manifest in self.store.manifests():
            model = installed.get(manifest.id)
            items.append(
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "publisher": manifest.publisher,
                    "quantisation": manifest.quantisation,
                    "license_spdx": manifest.license_spdx,
                    "license_url": manifest.license_url,
                    "size_bytes": manifest.total_size_bytes,
                    "approved": manifest.approved,
                    "installed": model is not None,
                    "installed_path": model.primary_path().as_posix() if model else None,
                }
            )
        return {"models": items}

    def close(self) -> None:
        self.backend.stop()
        self.knowledge.close()
        self.db.close()


def _backend_config(config: ServerConfig, state: StudioState):
    from .llama_server import ServerConfig as LlamaConfig

    model_path = Path("llama-server-not-installed")
    if config.model_id:
        with contextlib.suppress(StoreError):
            model_path = state.store.primary_path(config.model_id)
    return LlamaConfig(
        model_path=model_path,
        context=state.profile.context if state.profile else 4096,
        n_gpu_layers=state.profile.n_gpu_layers if state.profile else 0,
        port=config.backend_port,
        api_key=config.backend_key,
    )


ROUTES: list[Route] = [
    ("GET", re.compile(r"^/health$"), "health"),
    ("GET", re.compile(r"^/version$"), "version"),
    ("GET", re.compile(r"^/api/device/profile$"), "device_profile"),
    ("GET", re.compile(r"^/api/models$"), "models_list"),
    ("GET", re.compile(r"^/api/storage/usage$"), "storage_usage"),
    ("GET", re.compile(r"^/api/safety/resources$"), "safety_resources"),
    ("GET", re.compile(r"^/api/audit$"), "audit_list"),
    ("GET", re.compile(r"^/api/journal$"), "journal_list"),
    ("POST", re.compile(r"^/api/journal$"), "journal_create"),
    ("DELETE", re.compile(r"^/api/journal/(?P<id>[A-Za-z0-9_]+)$"), "journal_delete"),
    ("GET", re.compile(r"^/api/knowledge/stats$"), "knowledge_stats"),
    ("GET", re.compile(r"^/api/knowledge/documents$"), "knowledge_documents"),
    ("GET", re.compile(r"^/api/knowledge/search$"), "knowledge_search"),
    ("POST", re.compile(r"^/api/knowledge/reindex$"), "knowledge_reindex"),
    ("POST", re.compile(r"^/api/data/export$"), "data_export"),
    ("POST", re.compile(r"^/api/data/wipe$"), "data_wipe"),
    ("GET", re.compile(r"^/api/runtime/status$"), "runtime_status"),
    ("GET", re.compile(r"^/v1/models$"), "openai_models"),
    ("POST", re.compile(r"^/v1/chat/completions$"), "chat_completions"),
]


def make_handler(state: StudioState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = f"HCS-Therapy-Studio/{__version__}"
        protocol_version = "HTTP/1.1"

        # -- plumbing ------------------------------------------------------
        def log_message(self, fmt: str, *args) -> None:  # noqa: A003
            """Silence the default stderr log: it would contain request paths."""
            return

        def _cors(self) -> str | None:
            origin = self.headers.get("Origin")
            if not origin:
                return None
            if origin_allowed(origin, state.config.origins):
                return origin
            return None

        def _send_json(self, status: int, payload: dict, origin: str | None = None) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(body)

        def _authorised(self) -> bool:
            header = self.headers.get("Authorization", "")
            token = header[7:].strip() if header.lower().startswith("bearer ") else ""
            if not token:
                token = self.headers.get("X-HCS-Token", "").strip()
            return bool(token) and secrets.compare_digest(token, state.config.token)

        def _read_json(self) -> tuple[dict, str | None]:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                return {}, "request body too large"
            if length <= 0:
                return {}, None
            raw = self.rfile.read(length)
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {}, "body must be valid UTF-8 JSON"
            if not isinstance(parsed, dict):
                return {}, "body must be a JSON object"
            return parsed, None

        def _drain_body(self) -> None:
            """Consume a request body we are not going to parse.

            If the server answers and closes while the client is still sending a
            body, Windows raises WSAECONNABORTED (10053) on the client instead of
            delivering the response. Draining the body first is what makes a 401
            or a 403 readable by the caller.
            """
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except (TypeError, ValueError):
                return
            remaining = min(max(length, 0), MAX_BODY_BYTES)
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 65536))
                if not chunk:
                    break
                remaining -= len(chunk)

        def _dispatch(self, method: str) -> None:
            origin = self._cors()
            if self.headers.get("Origin") and origin is None:
                # Reject hostile browser origins outright, not just credentials.
                self._drain_body()
                self._send_json(HTTPStatus.FORBIDDEN, {"error": "origin not allowed"})
                return
            if method == "OPTIONS":
                self.send_response(HTTPStatus.NO_CONTENT)
                if origin:
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
                    self.send_header(
                        "Access-Control-Allow-Headers",
                        "Authorization, Content-Type, X-HCS-Token, X-HCS-Confirm",
                    )
                    self.send_header("Vary", "Origin")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            path = self.path.split("?", 1)[0]
            query = {
                key: values[-1]
                for key, values in parse_qs(urlsplit(self.path).query).items()
            }
            for route_method, pattern, name in ROUTES:
                if route_method != method:
                    continue
                match = pattern.match(path)
                if not match:
                    continue
                if name not in ("health", "version") and not self._authorised():
                    self._drain_body()
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorised"}, origin)
                    return
                body, error = self._read_json()
                if error:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": error}, origin)
                    return
                if name == "chat_completions" and body.get("stream") is True:
                    self._stream_chat(state, body, origin)
                    return
                handler = getattr(state, name)
                try:
                    result = handler(body, {**match.groupdict(), **query})
                except StoreError as exc:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)}, origin)
                    return
                except PermissionError as exc:
                    self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)}, origin)
                    return
                except Exception as exc:  # noqa: BLE001 - never leak a traceback to a client
                    state.db.audit("request_failed", "error", summary=type(exc).__name__)
                    self._send_json(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        {"error": f"{type(exc).__name__}: {exc}"},
                        origin,
                    )
                    return
                if result is None:
                    self._send_json(HTTPStatus.OK, {"ok": True}, origin)
                elif isinstance(result, tuple):
                    status, payload = result
                    self._send_json(int(status), payload, origin)
                else:
                    self._send_json(HTTPStatus.OK, result, origin)
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"}, origin)

        # -- streaming -----------------------------------------------------
        def _sse_open(self, origin: str | None) -> None:
            """Open an SSE response with connection-close framing.

            ``Content-Length`` is impossible for a stream, and implementing
            chunked framing by hand for one endpoint buys nothing: HTTP/1.1
            allows a response delimited by connection close. The trade-off is one
            connection per message, which is exactly what this workload is.
            """
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("X-Content-Type-Options", "nosniff")
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.close_connection = True

        def _sse_send(self, payload: dict, event: str | None = None) -> bool:
            try:
                if event:
                    self.wfile.write(f"event: {event}\n".encode())
                self.wfile.write(f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode())
                self.wfile.flush()
                return True
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                # The user pressed stop. Not an error, and the caller must stop
                # doing work for a client that is gone.
                return False

        def _stream_chat(self, state: StudioState, body: dict, origin: str | None) -> None:
            messages = body.get("messages")
            if not isinstance(messages, list) or not messages:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "messages must be a non-empty list"},
                    origin,
                )
                return
            last_user = ""
            for message in reversed(messages):
                if isinstance(message, dict) and message.get("role") == "user":
                    content = message.get("content")
                    if isinstance(content, str):
                        last_user = content
                    elif isinstance(content, list):
                        last_user = " ".join(
                            part.get("text", "") for part in content if isinstance(part, dict)
                        )
                    break

            started = time.monotonic()
            # The crisis gate runs before the stream opens, so no token can ever
            # precede the safety decision.
            assessment = assess_crisis(last_user)
            decision = decide_policy(
                assessment,
                locale=_resolve_locale(state, body),
                region=_resolve_region(state, body),
                attentive=_attentive_for(body),
            )

            self._sse_open(origin)
            if decision.override_text is not None:
                state.db.audit(
                    "crisis_gate_stream",
                    "ok",
                    summary=f"{decision.mode} categories={','.join(assessment.categories)}",
                )
                text = decision.override_text
                # Emit in paragraph-sized slices so the UI path is identical to a
                # model answer; the badge tells the truth about who wrote it.
                for piece in _split_for_stream(text):
                    if not self._sse_send({"delta": piece}):
                        return
                self._sse_send(
                    {
                        "policy_mode": decision.mode,
                        "resources_shown": decision.show_resources,
                        "scope_label": decision.scope_label,
                        "model_bypassed": True,
                        "output_guard_ok": True,
                        "output_guard_categories": [],
                        "ttft_ms": round((time.monotonic() - started) * 1000, 1),
                        "tokens_per_second": None,
                        "streamed": True,
                    },
                    event="hcs",
                )
                self._sse_send({"done": True})
                return

            if not state.backend_healthy():
                self._sse_send(
                    {
                        "error": "local model backend is not running",
                        "hint": "start it with: hcs-therapy serve --start-backend",
                    },
                    event="error",
                )
                self._sse_send({"done": True})
                return

            outbound = {key: value for key, value in body.items() if key not in ("hcs",)}
            if not state.config.thinking:
                outbound.setdefault("chat_template_kwargs", {"enable_thinking": False})
            outbound["stream"] = True
            turn_locale = _resolve_locale(state, body)
            anchored = _anchor_for(body, last_user, turn_locale)
            grounded = system_prompt(turn_locale, register=anchored)
            if decision.system_suffix:
                # The session-level carry-over only exists if it reaches the prompt.
                grounded = f"{grounded}\n\n{decision.system_suffix}"
            system_messages: list[dict[str, Any]] = [
                {"role": "system", "content": grounded}
            ]
            knowledge_meta: dict[str, Any] | None = None
            allowed_citations: list[int] = []
            options = body.get("hcs")
            options = options if isinstance(options, dict) else {}
            if options.get("use_knowledge") and last_user:
                try:
                    requested = int(options.get("knowledge_k") or 4)
                except (TypeError, ValueError):
                    requested = 4
                hits = state.knowledge.search(last_user, k=max(1, min(requested, 10)))
                block = state.knowledge.context_block(hits)
                if block:
                    system_messages.append({"role": "system", "content": block})
                allowed_citations = [hit.chunk_id for hit in hits]
                knowledge_meta = {
                    "requested": True,
                    "hits": len(hits),
                    "chunk_ids": allowed_citations,
                    "empty_reason": None
                    if hits
                    else "no indexed passage shares a word or trigram with the message",
                }
            outbound["messages"] = [*system_messages, *messages]

            url = f"http://{LOOPBACK}:{state.config.backend_port}/v1/chat/completions"
            headers = {"Content-Type": "application/json"}
            if state.config.backend_key:
                headers["Authorization"] = f"Bearer {state.config.backend_key}"
            request = urllib.request.Request(
                url, data=json.dumps(outbound).encode("utf-8"), headers=headers
            )
            first_token_at: float | None = None
            first_activity_at: float | None = None
            reasoning_chars = 0
            announced = 0
            pieces: list[str] = []
            token_count = 0
            failure: str | None = None
            try:
                response = urllib.request.urlopen(request, timeout=600)  # noqa: S310 loopback
            except (urllib.error.URLError, OSError) as exc:
                self._sse_send({"error": f"backend request failed: {exc}"}, event="error")
                self._sse_send({"done": True})
                return

            try:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content") or ""
                    reasoning = delta.get("reasoning_content") or ""
                    if reasoning and not piece:
                        # Qwen3-class models think before they answer. The
                        # scratchpad is not shown — a chain of thought is not a
                        # reply, and AGENTS.md §6.5 keeps it out of the product —
                        # but the user must not stare at a dead screen either.
                        if first_activity_at is None:
                            first_activity_at = time.monotonic()
                        reasoning_chars += len(reasoning)
                        if reasoning_chars - announced >= 24:
                            announced = reasoning_chars
                            if not self._sse_send(
                                {"phase": "thinking", "chars": reasoning_chars},
                                event="phase",
                            ):
                                failure = "client disconnected"
                                break
                        continue
                    if not piece:
                        continue
                    if first_activity_at is None:
                        first_activity_at = time.monotonic()
                    if first_token_at is None:
                        first_token_at = time.monotonic()
                    pieces.append(piece)
                    token_count += 1
                    if not self._sse_send({"delta": piece}):
                        failure = "client disconnected"
                        break
            except (urllib.error.URLError, OSError) as exc:
                failure = f"{type(exc).__name__}: {exc}"
            finally:
                with contextlib.suppress(Exception):
                    response.close()

            text = "".join(pieces)
            if not text and reasoning_chars:
                failure = (
                    "the model spent its whole token budget on reasoning and never "
                    "produced a visible answer; raise max_tokens"
                )
            guard = scan_output(text)
            if not guard.ok:
                fallback = fallback_after_scan(state.config.locale)
                if not self._sse_send({"replace": fallback}):
                    return
                text = fallback
            elapsed = time.monotonic() - started
            meta: dict[str, Any] = {
                "policy_mode": decision.mode,
                "resources_shown": False,
                "scope_label": decision.scope_label,
                "model_bypassed": False,
                "output_guard_ok": guard.ok,
                "output_guard_categories": guard.categories,
                "register": _register_meta(text, anchored),
                "attentive": bool(decision.attentive),
                "ttft_ms": None
                if first_token_at is None
                else round((first_token_at - started) * 1000, 1),
                "first_activity_ms": None
                if first_activity_at is None
                else round((first_activity_at - started) * 1000, 1),
                "reasoning_chars": reasoning_chars,
                "tokens_per_second": None
                if first_token_at is None or elapsed <= 0
                else round(token_count / max(elapsed, 1e-6), 2),
                "streamed": True,
            }
            if failure:
                meta["stream_error"] = failure
            if knowledge_meta is not None:
                unverified = missing_citations(text, allowed_citations)
                knowledge_meta["citations_used"] = len(citations_in(text))
                knowledge_meta["unverified_citations"] = unverified
                knowledge_meta["citations_ok"] = not unverified
                meta["knowledge"] = knowledge_meta
            state.db.audit(
                "chat_completion_stream",
                "ok" if guard.ok else "guard_tripped",
                summary=f"chars={len(text)} mode={decision.mode}",
            )
            self._sse_send(meta, event="hcs")
            self._sse_send({"done": True})

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")
        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def do_DELETE(self) -> None:  # noqa: N802
            self._dispatch("DELETE")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._dispatch("OPTIONS")

    return Handler


def _split_for_stream(text: str, *, size: int = 90) -> list[str]:
    """Chop a deterministic answer into word-aligned slices for the SSE path.

    The crisis response is not a model token stream, but the client should not
    need two rendering paths: emitting it in slices keeps one code path in the
    UI while the ``model_bypassed`` flag says who actually wrote it.
    """
    words = text.split(" ")
    slices: list[str] = []
    buffer = ""
    for word in words:
        candidate = f"{buffer} {word}".lstrip() if buffer else word
        if len(candidate) > size and buffer:
            slices.append(buffer + " ")
            buffer = word
        else:
            buffer = candidate
    if buffer:
        slices.append(buffer)
    return slices or [text]


def origin_allowed(origin: str, allow_list: tuple[str, ...]) -> bool:
    """Loopback origins on any port, plus explicit remote/tauri entries.

    A strict string match breaks every local dev server whose port is dynamic
    (Vite picks 4173 for preview, 5173 for dev, 5174 if the first is taken). The
    security boundary is the bearer token and the loopback bind, not the port
    number — but a remote origin must still be rejected.
    """
    if origin in allow_list:
        return True
    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https"):
        return False
    return (parts.hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}


def _require_confirmation(body: dict, action: str) -> None:
    if body.get("confirmed") is not True:
        raise PermissionError(
            f"{action} requires explicit confirmation: send {{\"confirmed\": true}}"
        )


# --- request handlers are attached to StudioState so routes stay declarative --
def _health(self: StudioState, body: dict, params: dict) -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "local_only": True,
        "model_loaded": self.backend_healthy(),
    }


def _version(self: StudioState, body: dict, params: dict) -> dict:
    return {
        "version": __version__,
        "product": "HCS Therapy Studio",
        "credit": "Made with love by hcsmedia and timfromhcs",
        "api": 1,
    }


def _device_profile(self: StudioState, body: dict, params: dict) -> dict:
    return self.device_report()


def _models_list(self: StudioState, body: dict, params: dict) -> dict:
    return self.models_report()


def _storage_usage(self: StudioState, body: dict, params: dict) -> dict:
    return {**self.store.disk_usage(), "root": str(self.paths.root)}


def _safety_resources(self: StudioState, body: dict, params: dict) -> dict:
    return resources_dict()


def _audit_list(self: StudioState, body: dict, params: dict) -> dict:
    return {"events": self.db.audit_events()}


def _journal_list(self: StudioState, body: dict, params: dict) -> dict:
    return {"entries": self.db.journal_entries()}


def _journal_create(self: StudioState, body: dict, params: dict) -> dict:
    _require_confirmation(body, "creating a journal entry")
    text = body.get("body")
    if not isinstance(text, str) or not text.strip():
        return (HTTPStatus.BAD_REQUEST, {"error": "body must be a non-empty string"})
    entry_id = self.db.add_journal_entry(
        text,
        title=body.get("title"),
        mood=body.get("mood") if isinstance(body.get("mood"), int) else None,
        tags=[str(t) for t in (body.get("tags") or [])][:20],
    )
    self.db.audit("journal_create", "ok", summary=f"entry length {len(text)}")
    return {"id": entry_id}


def _journal_delete(self: StudioState, body: dict, params: dict) -> dict:
    _require_confirmation(body, "deleting a journal entry")
    self.db.delete_journal_entry(params["id"])
    self.db.audit("journal_delete", "ok", summary=params["id"])
    return {"deleted": params["id"]}


def _knowledge_stats(self: StudioState, body: dict, params: dict) -> dict:
    return self.knowledge.stats()


def _knowledge_documents(self: StudioState, body: dict, params: dict) -> dict:
    return {"documents": self.knowledge.documents()}


def _knowledge_search(self: StudioState, body: dict, params: dict) -> dict:
    query = str(params.get("q") or body.get("q") or "").strip()
    if not query:
        return (HTTPStatus.BAD_REQUEST, {"error": "q is required"})
    try:
        k = int(params.get("k") or body.get("k") or 5)
        lam = float(params.get("lambda") or body.get("lambda") or 0.7)
    except (TypeError, ValueError):
        return (HTTPStatus.BAD_REQUEST, {"error": "k and lambda must be numbers"})
    k = max(1, min(k, 20))
    lam = max(0.0, min(lam, 1.0))
    hits = self.knowledge.search(query, k=k, lam=lam)
    self.db.audit("knowledge_search", "ok", summary=f"hits={len(hits)} k={k}")
    return {
        "query": query,
        "hits": [hit.to_dict() for hit in hits],
        "retriever": "bm25-word + bm25-trigram + rrf(60) + mmr",
        "empty_reason": None if hits else "no chunk shares a word or trigram with the query",
    }


def _knowledge_reindex(self: StudioState, body: dict, params: dict) -> dict:
    """Re-index the journal. Explicit, confirmed, and counted."""
    _require_confirmation(body, "re-indexing your journal into the knowledge base")
    entries = self.db.journal_entries()
    indexed = 0
    for entry in entries:
        text = f"{entry.get('title') or ''}\n\n{entry.get('body') or ''}".strip()
        if not text:
            continue
        self.knowledge.add_document(
            source="journal",
            title=entry.get("title"),
            text=text,
            doc_id=f"journal_{entry['id']}",
        )
        indexed += 1
    self.db.audit("knowledge_reindex", "ok", summary=f"documents={indexed}")
    return {"indexed": indexed, "stats": self.knowledge.stats()}


def _data_export(self: StudioState, body: dict, params: dict) -> dict:
    _require_confirmation(body, "exporting personal data")
    data = self.db.export_all()
    self.paths.exports.mkdir(parents=True, exist_ok=True)
    import time

    target = self.paths.exports / f"export-{time.strftime('%Y%m%d-%H%M%S')}.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    self.db.audit("data_export", "ok", summary=target.name)
    return {"path": str(target)}


def _data_wipe(self: StudioState, body: dict, params: dict) -> dict:
    """Delete all user content. Destructive, so it needs explicit confirmation."""
    _require_confirmation(body, "deleting all content")
    counts = self.db.wipe_user_content()
    self.db.audit("data_wipe", "ok", summary=json.dumps(counts))
    return {"deleted": counts}


def _runtime_status(self: StudioState, body: dict, params: dict) -> dict:
    return {
        "backend": {
            **self.backend.status().__dict__,
            "healthy": self.backend_healthy(),
            "port": self.config.backend_port,
        },
        "profile": self.profile.to_dict() if self.profile else None,
    }


def _openai_models(self: StudioState, body: dict, params: dict) -> dict:
    return {
        "object": "list",
        "data": [
            {
                "id": manifest.id,
                "object": "model",
                "owned_by": manifest.publisher,
                "created": 0,
            }
            for manifest in self.store.manifests()
        ],
    }


def _attentive_for(body: dict) -> bool:
    """Whether this turn follows a crisis hand-off in the same conversation.

    The client keeps the counter, because the server deliberately stores no
    conversation. This can only make a turn *more* careful, so a client that lies
    gains nothing except a slightly gentler reply; it cannot weaken the gate.
    """
    options = body.get("hcs")
    return bool(isinstance(options, dict) and options.get("attentive") is True)


def _anchor_for(body: dict, last_user: str, locale: str) -> str | None:
    """The register instruction for this turn, or ``None``.

    ``hcs.no_register_anchor`` disables it per request. That exists for one reason:
    without it there is no way to measure whether the anchoring *does* anything,
    and an unmeasured prompt change is exactly the kind of claim this project does
    not make.
    """
    options = body.get("hcs")
    if isinstance(options, dict) and options.get("no_register_anchor") is True:
        return None
    return register_anchor(last_user, locale=locale)


def _register_meta(answer: str, anchored: str | None) -> dict[str, Any]:
    """How the reply addresses the person, and whether that held.

    Detection only. Rewriting German register means rewriting verb conjugation, and
    a pronoun substitution would produce wrong German - so the product surfaces the
    violation instead of silently mangling the sentence.
    """
    report = analyse_register(answer)
    return {
        **report.to_dict(),
        "anchored": anchored is not None,
        "violated_anchor": anchored is not None and report.mixed,
    }


def _resolve_locale(self: StudioState, body: dict) -> str:
    """Answer language for this turn: the UI language, if it is one we ship.

    The server default is a launch flag; the browser knows what the user is
    actually reading. Accepting ``hcs.locale`` keeps the interface and the
    answer in one language instead of producing a German crisis template inside
    an English UI. Anything other than the two shipped locales is ignored rather
    than passed through.
    """
    options = body.get("hcs")
    if isinstance(options, dict):
        candidate = options.get("locale")
        if isinstance(candidate, str) and candidate.lower()[:2] in ("de", "en"):
            return candidate.lower()[:2]
    return self.config.locale


def _resolve_region(self: StudioState, body: dict) -> str | None:
    """Region for this turn.

    The browser holds the user's region in localStorage and the server holds a
    launch default. If the server ignored the client, the crisis card (drawn from
    localStorage) and the crisis *message* (drawn from the server) could show two
    different answers — the worst possible inconsistency in this product.

    The client value is therefore accepted, but only as a *lookup key*: it is
    resolved through the verified pack table, so an unknown or hostile value
    degrades to the "no verified pack" fallback instead of inventing a hotline.
    """
    options = body.get("hcs")
    if isinstance(options, dict):
        candidate = options.get("region")
        if isinstance(candidate, str) and candidate.strip():
            pack = resolve_region(candidate)
            return None if pack.region == "UNKNOWN" else pack.region
    return self.config.region


def _chat_completions(self: StudioState, body: dict, params: dict) -> Any:
    """Crisis-gated chat endpoint.

    The crisis gate runs on the last user message *before* the model is used.
    When it fires, the deterministic response is returned and no generation
    happens at all.
    """
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return (HTTPStatus.BAD_REQUEST, {"error": "messages must be a non-empty list"})
    last_user = ""
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                last_user = content
            elif isinstance(content, list):
                last_user = " ".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            break

    assessment = assess_crisis(last_user)
    decision = decide_policy(
        assessment,
        locale=_resolve_locale(self, body),
        region=_resolve_region(self, body),
        attentive=_attentive_for(body),
    )
    if decision.override_text is not None:
        self.db.audit(
            "crisis_gate",
            "ok",
            summary=f"{decision.mode} categories={','.join(assessment.categories)}",
        )
        payload = {
            "id": "chatcmpl-crisis",
            "object": "chat.completion",
            "created": 0,
            "model": "hcs-safety-policy",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": decision.override_text},
                    "finish_reason": "stop",
                }
            ],
            "hcs": {
                "policy_mode": decision.mode,
                "resources_shown": decision.show_resources,
                "scope_label": decision.scope_label,
                "model_bypassed": True,
                "attentive": True,
            },
        }
        return (HTTPStatus.OK, payload)

    if not self.backend_healthy():
        return (
            HTTPStatus.SERVICE_UNAVAILABLE,
            {
                "error": "local model backend is not running",
                "hint": "start it with: hcs-therapy serve --start-backend",
                "profile": self.profile.to_dict() if self.profile else None,
            },
        )

    outbound = {key: value for key, value in body.items() if key != "hcs"}
    if not self.config.thinking:
        outbound.setdefault("chat_template_kwargs", {"enable_thinking": False})
    turn_locale = _resolve_locale(self, body)
    anchored = _anchor_for(body, last_user, turn_locale)
    prompt = system_prompt(turn_locale, register=anchored)
    if decision.system_suffix:
        prompt = f"{prompt}\n\n{decision.system_suffix}"
    hcs_options = body.get("hcs")
    hcs_options = hcs_options if isinstance(hcs_options, dict) else {}
    system_messages = [{"role": "system", "content": prompt}]
    knowledge_meta: dict[str, Any] | None = None
    allowed_citations: list[int] = []
    if hcs_options.get("use_knowledge") and last_user:
        try:
            requested = int(hcs_options.get("knowledge_k") or 4)
        except (TypeError, ValueError):
            requested = 4
        hits = self.knowledge.search(last_user, k=max(1, min(requested, 10)))
        if hits:
            block = self.knowledge.context_block(hits)
            if block:
                system_messages.append({"role": "system", "content": block})
            allowed_citations = [hit.chunk_id for hit in hits]
        knowledge_meta = {
            "requested": True,
            "hits": len(hits),
            "chunk_ids": allowed_citations,
            "empty_reason": None
            if hits
            else "no indexed passage shares a word or trigram with the message",
        }
    outbound["messages"] = [*system_messages, *messages]
    url = f"http://{LOOPBACK}:{self.config.backend_port}/v1/chat/completions"
    data = json.dumps(outbound).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if self.config.backend_key:
        headers["Authorization"] = f"Bearer {self.config.backend_key}"

    try:
        response = urllib.request.urlopen(  # noqa: S310 loopback only
            urllib.request.Request(url, data=data, headers=headers), timeout=600
        )
    except (urllib.error.URLError, OSError) as exc:
        return (HTTPStatus.BAD_GATEWAY, {"error": f"backend request failed: {exc}"})

    raw = response.read()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return (HTTPStatus.BAD_GATEWAY, {"error": "backend returned non-JSON"})

    text = ""
    choices = parsed.get("choices") or []
    if choices:
        text = (choices[0].get("message") or {}).get("content") or ""
    guard = scan_output(text)
    parsed["hcs"] = {
        "policy_mode": decision.mode,
        "resources_shown": False,
        "scope_label": decision.scope_label,
        "model_bypassed": False,
        "output_guard_ok": guard.ok,
        "output_guard_categories": guard.categories,
        "register": _register_meta(text, anchored),
        "attentive": bool(decision.attentive),
    }
    if knowledge_meta is not None:
        cited = citations_in(text)
        unverified = missing_citations(text, allowed_citations)
        knowledge_meta["citations_used"] = len(cited)
        knowledge_meta["unverified_citations"] = unverified
        knowledge_meta["citations_ok"] = not unverified
        parsed["hcs"]["knowledge"] = knowledge_meta
    if not guard.ok:
        from ..safety import fallback_after_scan

        parsed["hcs"]["original_flagged"] = True
        if choices:
            choices[0].setdefault("message", {})["content"] = fallback_after_scan(self.config.locale)
    self.db.audit(
        "chat_completion",
        "ok" if guard.ok else "guard_tripped",
        summary=f"chars={len(text)} mode={decision.mode}",
    )
    return (HTTPStatus.OK, parsed)


def attach(state_cls: type[StudioState]) -> None:
    """Bind the handler functions to :class:`StudioState`."""
    for func in (
        _health,
        _version,
        _device_profile,
        _models_list,
        _storage_usage,
        _safety_resources,
        _audit_list,
        _journal_list,
        _journal_create,
        _journal_delete,
        _knowledge_stats,
        _knowledge_documents,
        _knowledge_search,
        _knowledge_reindex,
        _data_export,
        _data_wipe,
        _runtime_status,
        _openai_models,
        _chat_completions,
    ):
        setattr(state_cls, func.__name__[1:], func)


attach(StudioState)


class StudioHTTPServer(ThreadingHTTPServer):
    """Server that treats a client hanging up as normal, not as an error.

    A browser cancels in-flight requests constantly (navigation, abort). Without
    this, every cancel dumps a traceback to the console, which trains users to
    ignore real errors.
    """

    daemon_threads = True

    # On Windows SO_REUSEADDR lets a *second* process bind the same port, so an
    # old instance silently keeps serving while the new one believes it owns the
    # port. Refuse the bind instead.
    allow_reuse_address = False

    def handle_error(self, request, client_address) -> None:
        import sys

        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


@dataclass
class RunningServer:
    httpd: ThreadingHTTPServer
    state: StudioState
    token: str
    port: int

    @property
    def url(self) -> str:
        return f"http://{LOOPBACK}:{self.port}"

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.state.close()


def serve(
    paths: Paths,
    *,
    port: int = 8765,
    model_id: str | None = None,
    backend_port: int | None = None,
    backend_key: str | None = None,
    locale: str = "de",
    region: str | None = None,
    encrypt: bool = True,
    token: str | None = None,
) -> RunningServer:
    """Start the local API. Returns a handle; call ``stop()`` to shut down."""
    config = ServerConfig(
        paths=paths,
        token=token or secrets.token_urlsafe(32),
        model_id=model_id,
        backend_port=backend_port,
        backend_key=backend_key or secrets.token_urlsafe(24),
        locale=locale,
        region=region,
        encrypt=encrypt,
    )
    state = StudioState(config)
    handler = make_handler(state)
    httpd = StudioHTTPServer((LOOPBACK, port), handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, name="hcs-api", daemon=True)
    thread.start()
    return RunningServer(httpd, state, config.token, httpd.server_address[1])
