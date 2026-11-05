"""Streaming chat: SSE framing, crisis-before-token, abort, knowledge injection.

The backend is faked with a local HTTP server so the test proves the *proxy's*
behaviour — framing, ordering, gate placement — without needing a 1.8 GB model
in the loop. A separate, real measurement lives in ``status.md``.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from hcs_therapy.runtime.api import _split_for_stream, serve


class FakeBackend:
    """A minimal OpenAI-compatible SSE endpoint."""

    def __init__(self, pieces: list[str], *, status: int = 200) -> None:
        self.pieces = pieces
        self.status = status
        self.received: list[dict[str, Any]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt, *args) -> None:  # noqa: A003
                return

            def do_GET(self) -> None:  # noqa: N802
                body = b'{"status":"ok"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                outer.received.append(json.loads(self.rfile.read(length) or b"{}"))
                if outer.status != 200:
                    self.send_response(outer.status)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
                for piece in outer.pieces:
                    frame = {
                        "choices": [{"delta": {"content": piece}, "index": 0}],
                    }
                    self.wfile.write(f"data: {json.dumps(frame)}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def backend():
    server = FakeBackend(["Hallo", ", ich", " bin hier."])
    yield server
    server.stop()


@pytest.fixture
def streaming_api(paths, backend):
    running = serve(
        paths,
        port=0,
        locale="de",
        region="DE",
        encrypt=True,
        backend_port=backend.port,
        backend_key="test-key",
    )
    yield running
    running.stop()


def _stream(url: str, body: dict, token: str) -> str:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        assert response.headers.get("Content-Type", "").startswith("text/event-stream")
        return response.read().decode("utf-8")


def _events(raw: str) -> list[tuple[str | None, dict]]:
    events: list[tuple[str | None, dict]] = []
    name: str | None = None
    for line in raw.splitlines():
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            payload = line[5:].strip()
            events.append((name, json.loads(payload)))
            name = None
    return events


# --- the real stream ------------------------------------------------------


def test_stream_emits_deltas_then_meta_then_done(streaming_api, backend) -> None:
    raw = _stream(
        f"{streaming_api.url}/v1/chat/completions",
        {"messages": [{"role": "user", "content": "Hallo"}], "stream": True},
        streaming_api.token,
    )
    events = _events(raw)
    deltas = [payload["delta"] for name, payload in events if "delta" in payload]
    assert "".join(deltas) == "Hallo, ich bin hier."
    meta = next(payload for name, payload in events if name == "hcs")
    assert meta["model_bypassed"] is False
    assert meta["streamed"] is True
    assert meta["ttft_ms"] is not None and meta["ttft_ms"] >= 0
    assert events[-1][1].get("done") is True


def test_stream_forwards_a_system_prompt_and_never_the_hcs_envelope(
    streaming_api, backend
) -> None:
    _stream(
        f"{streaming_api.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "Hallo"}],
            "stream": True,
            "hcs": {"use_knowledge": False},
            "temperature": 0.4,
        },
        streaming_api.token,
    )
    sent = backend.received[-1]
    assert sent["stream"] is True
    assert sent["temperature"] == 0.4
    assert "hcs" not in sent, "the private envelope must not reach the sidecar"
    assert sent["messages"][0]["role"] == "system"
    assert sent["messages"][-1]["content"] == "Hallo"


def test_the_crisis_gate_runs_before_any_token(streaming_api, backend) -> None:
    """The single most important ordering property of the whole endpoint."""
    before = len(backend.received)
    raw = _stream(
        f"{streaming_api.url}/v1/chat/completions",
        {
            "messages": [
                {"role": "user", "content": "Ich bringe mich heute Nacht um."}
            ],
            "stream": True,
        },
        streaming_api.token,
    )
    events = _events(raw)
    meta = next(payload for name, payload in events if name == "hcs")
    assert meta["model_bypassed"] is True
    assert meta["policy_mode"] == "crisis_imminent"
    assert len(backend.received) == before, "the model must not be called at all"


def test_the_crisis_stream_still_carries_usable_text(streaming_api) -> None:
    raw = _stream(
        f"{streaming_api.url}/v1/chat/completions",
        {"messages": [{"role": "user", "content": "Ich will nicht mehr leben."}], "stream": True},
        streaming_api.token,
    )
    text = "".join(
        payload["delta"] for _, payload in _events(raw) if "delta" in payload
    )
    assert len(text) > 100
    assert "Telefonseelsorge" in text or "112" in text


def test_stream_reports_a_dead_backend_as_an_event(paths) -> None:
    running = serve(paths, port=0, locale="de", encrypt=True, backend_port=1, backend_key="x")
    try:
        raw = _stream(
            f"{running.url}/v1/chat/completions",
            {"messages": [{"role": "user", "content": "Hallo"}], "stream": True},
            running.token,
        )
        events = _events(raw)
        assert any(name == "error" for name, _ in events)
        assert events[-1][1].get("done") is True
    finally:
        running.stop()


def test_stream_requires_a_token(streaming_api) -> None:
    """The 401 must be readable, not a connection reset.

    A server that answers and closes without draining the request body makes
    Windows report WSAECONNABORTED (10053) instead of the response, so the caller
    never learns why it failed.
    """
    request = urllib.request.Request(
        f"{streaming_api.url}/v1/chat/completions",
        data=json.dumps({"messages": [{"role": "user", "content": "x"}], "stream": True}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as info:
        urllib.request.urlopen(request, timeout=10)  # noqa: S310
    assert info.value.code == 401
    assert "unauthorised" in json.loads(info.value.read())["error"]


def test_stream_rejects_an_empty_message_list(streaming_api) -> None:
    request = urllib.request.Request(
        f"{streaming_api.url}/v1/chat/completions",
        data=json.dumps({"messages": [], "stream": True}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {streaming_api.token}",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=10)  # noqa: S310
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        assert exc.code == 400
    else:  # pragma: no cover
        raise AssertionError("an empty message list must be rejected")


# --- pieces ---------------------------------------------------------------


def test_split_for_stream_keeps_every_word() -> None:
    text = "Ein kurzer Satz mit einigen Wörtern, der in Stücke zerlegt wird."
    slices = _split_for_stream(text, size=20)
    assert len(slices) > 1
    assert " ".join(slices).split() == text.split()


def test_split_for_stream_handles_a_short_answer() -> None:
    assert _split_for_stream("ok", size=100) == ["ok"]


def test_split_for_stream_of_an_empty_string_still_yields_something() -> None:
    assert _split_for_stream("", size=10) == [""]
