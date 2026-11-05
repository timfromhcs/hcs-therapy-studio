"""Register anchoring must be measurable, not just asserted.

The anchoring paragraph is a prompt change. A prompt change without an A/B is a
hope, so the API accepts ``hcs.no_register_anchor`` to switch it off per request
and the measurement script compares both arms.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from hcs_therapy.runtime.api import serve


class PanelBackend:
    """Returns a scripted answer per user message, so both arms are comparable."""

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
                answer = "Du kannst das langsam angehen. Wenn Sie möchten, warten wir."
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
    backend = PanelBackend()
    running = serve(
        paths,
        port=0,
        locale="de",
        region="DE",
        encrypt=True,
        backend_port=backend.port,
        backend_key="k",
    )
    yield running, backend
    running.stop()
    backend.stop()


def _post(url: str, body: dict, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.loads(response.read())


def test_anchoring_is_added_when_the_user_writes_du(setup) -> None:
    running, backend = setup
    payload = _post(
        f"{running.url}/v1/chat/completions",
        {"messages": [{"role": "user", "content": "Kannst du mir helfen?"}]},
        running.token,
    )
    system = backend.received[-1]["messages"][0]["content"]
    assert "durchgehend mit \"du\"" in system
    assert payload["hcs"]["register"]["anchored"] is True


def test_anchoring_is_added_when_the_user_writes_sie(setup) -> None:
    running, backend = setup
    _post(
        f"{running.url}/v1/chat/completions",
        {"messages": [{"role": "user", "content": "Können Sie mir helfen?"}]},
        running.token,
    )
    system = backend.received[-1]["messages"][0]["content"]
    assert "durchgehend mit \"Sie\"" in system


def test_a_message_without_a_signal_gets_the_default_anchor(setup) -> None:
    """No register in the message: the app's own "du" is the anchor.

    Measured before this default existed: one of five real requests mixed ``du``
    and ``Sie`` in a single answer. The default closes that case.
    """
    running, backend = setup
    payload = _post(
        f"{running.url}/v1/chat/completions",
        {"messages": [{"role": "user", "content": "Ich habe schlecht geschlafen."}]},
        running.token,
    )
    system = backend.received[-1]["messages"][0]["content"]
    assert 'durchgehend mit "du"' in system
    assert "keine Anrede" in system
    assert payload["hcs"]["register"]["anchored"] is True


def test_the_anchor_can_be_switched_off_for_an_a_b_comparison(setup) -> None:
    """Without this switch the prompt change could not be measured at all."""
    running, backend = setup
    payload = _post(
        f"{running.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "Kannst du mir helfen?"}],
            "hcs": {"no_register_anchor": True},
        },
        running.token,
    )
    system = backend.received[-1]["messages"][0]["content"]
    assert "durchgehend mit" not in system
    assert payload["hcs"]["register"]["anchored"] is False


def test_a_mixed_answer_is_reported_as_a_violation(setup) -> None:
    """The scripted backend mixes du and Sie; the payload must say so."""
    running, _ = setup
    payload = _post(
        f"{running.url}/v1/chat/completions",
        {"messages": [{"role": "user", "content": "Kannst du mir helfen?"}]},
        running.token,
    )
    register = payload["hcs"]["register"]
    assert register["mixed"] is True
    assert register["violated_anchor"] is True
    assert register["du_forms"] >= 1
    assert register["sie_forms"] >= 1
    assert "Anredebruch" in register["advice"]


def test_the_private_hcs_envelope_never_reaches_the_model(setup) -> None:
    running, backend = setup
    _post(
        f"{running.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "Kannst du mir helfen?"}],
            "hcs": {"no_register_anchor": True, "region": "DE", "locale": "de"},
        },
        running.token,
    )
    assert "hcs" not in backend.received[-1]


def test_english_requests_get_no_german_anchor(setup) -> None:
    running, backend = setup
    _post(
        f"{running.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "Can you help me?"}],
            "hcs": {"locale": "en"},
        },
        running.token,
    )
    system = backend.received[-1]["messages"][0]["content"]
    assert "durchgehend mit" not in system
