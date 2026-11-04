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
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .. import __version__
from ..hardware import HardwareReport, detect
from ..models.store import ModelStore, StoreError
from ..paths import Paths
from ..profiles import Assessment
from ..profiles import assess as assess_profile
from ..safety import (
    assess as assess_crisis,
)
from ..safety import (
    decide as decide_policy,
)
from ..safety import (
    resources_dict,
    scan_output,
    system_prompt,
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
    state: dict[str, Any] = field(default_factory=dict)


class StudioState:
    """Everything a request handler may touch."""

    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.paths = config.paths.ensure()
        self.store = ModelStore(self.paths)
        self.hardware = config.hardware or detect()
        self.db = Database(self.paths, encrypt=config.encrypt)
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

        def _dispatch(self, method: str) -> None:
            origin = self._cors()
            if self.headers.get("Origin") and origin is None:
                # Reject hostile browser origins outright, not just credentials.
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
            for route_method, pattern, name in ROUTES:
                if route_method != method:
                    continue
                match = pattern.match(path)
                if not match:
                    continue
                if name not in ("health", "version") and not self._authorised():
                    self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorised"}, origin)
                    return
                body, error = self._read_json()
                if error:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": error}, origin)
                    return
                handler = getattr(state, name)
                try:
                    result = handler(body, dict(match.groupdict()))
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

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def do_DELETE(self) -> None:  # noqa: N802
            self._dispatch("DELETE")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._dispatch("OPTIONS")

    return Handler


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
        assessment, locale=self.config.locale, region=self.config.region
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

    outbound = dict(body)
    prompt = system_prompt(self.config.locale)
    outbound["messages"] = [{"role": "system", "content": prompt}, *messages]
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
    }
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
