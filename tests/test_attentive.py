"""Session-level attentiveness must reach the prompt, not just a report field.

A single-turn gate forgets a crisis immediately, which is how an app ends up
replying "great, let's plan your week" two messages after someone said they wanted
to die. These tests prove the carry-over changes the request the model receives.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

import pytest

from hcs_therapy.runtime.api import serve


class Recorder:
    """Records the last request the API forwarded to the model."""

    def __init__(self) -> None:
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
                answer = "Ich verstehe. Wie geht es dir gerade?"
                body = json.dumps(
                    {"choices": [{"message": {"role": "assistant", "content": answer}}]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def setup(paths):
    recorder = Recorder()
    running = serve(
        paths,
        port=0,
        locale="de",
        region="DE",
        encrypt=True,
        backend_port=recorder.port,
        backend_key="k",
    )
    yield running, recorder
    running.stop()
    recorder.stop()


def _post(url: str, body: dict, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.loads(response.read())


def test_an_attentive_turn_carries_the_suffix_into_the_prompt(setup) -> None:
    running, recorder = setup
    payload = _post(
        f"{running.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "Ich habe mit meiner Schwester telefoniert."}],
            "hcs": {"attentive": True},
        },
        running.token,
    )
    system = recorder.received[-1]["messages"][0]["content"]
    assert "earlier in this conversation" in system.lower()
    assert payload["hcs"]["attentive"] is True
    assert payload["hcs"]["model_bypassed"] is False


def test_an_ordinary_turn_has_no_suffix(setup) -> None:
    running, recorder = setup
    payload = _post(
        f"{running.url}/v1/chat/completions",
        {"messages": [{"role": "user", "content": "Ich habe schlecht geschlafen."}]},
        running.token,
    )
    system = recorder.received[-1]["messages"][0]["content"]
    assert "earlier in this conversation" not in system.lower()
    assert payload["hcs"]["attentive"] is False


def test_the_crisis_turn_itself_reports_attentive(setup) -> None:
    running, recorder = setup
    before = len(recorder.received)
    payload = _post(
        f"{running.url}/v1/chat/completions",
        {"messages": [{"role": "user", "content": "Ich bringe mich heute Nacht um."}]},
        running.token,
    )
    assert payload["hcs"]["attentive"] is True
    assert payload["hcs"]["model_bypassed"] is True
    assert len(recorder.received) == before, "the model must not be called for a crisis turn"


def test_attentive_cannot_disable_the_gate(setup) -> None:
    """The flag only makes a turn more careful; it must never make it less safe."""
    running, recorder = setup
    before = len(recorder.received)
    payload = _post(
        f"{running.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "Ich bringe mich heute Nacht um."}],
            "hcs": {"attentive": False},
        },
        running.token,
    )
    assert payload["hcs"]["model_bypassed"] is True
    assert payload["hcs"]["resources_shown"] is True
    assert len(recorder.received) == before


def test_the_attentive_flag_never_reaches_the_model(setup) -> None:
    running, recorder = setup
    _post(
        f"{running.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "Es geht gerade."}],
            "hcs": {"attentive": True, "region": "DE", "locale": "de"},
        },
        running.token,
    )
    assert "hcs" not in recorder.received[-1]
