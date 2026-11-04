"""Local API: auth, CORS, confirmation gate, crisis bypass, headers."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from hcs_therapy.runtime.api import serve


@pytest.fixture
def api(paths):
    running = serve(paths, port=0, locale="de", region="DE", encrypt=True)
    yield running
    running.stop()


def _request(
    url: str, *, method: str = "GET", body: dict | None = None, token: str | None = None,
    origin: str | None = None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if origin:
        headers["Origin"] = origin
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            payload = json.loads(response.read() or b"{}")
            return response.status, payload, dict(response.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            payload = {"raw": raw.decode("utf-8", "replace")}
        return exc.code, payload, dict(exc.headers)


def test_health_needs_no_token(api) -> None:
    status, payload, headers = _request(f"{api.url}/health")
    assert status == 200
    assert payload["status"] == "ok"
    assert payload["local_only"] is True
    assert headers.get("X-Content-Type-Options") == "nosniff"


def test_version_endpoint(api) -> None:
    status, payload, _ = _request(f"{api.url}/version")
    assert status == 200
    assert payload["product"] == "HCS Therapy Studio"
    assert "hcsmedia" in payload["credit"]


def test_protected_endpoint_requires_token(api) -> None:
    status, payload, _ = _request(f"{api.url}/api/models")
    assert status == 401
    assert "unauthorised" in payload["error"]


def test_wrong_token_is_rejected(api) -> None:
    status, _, _ = _request(f"{api.url}/api/models", token="nope")
    assert status == 401


def test_token_grants_access(api) -> None:
    status, payload, _ = _request(f"{api.url}/api/models", token=api.token)
    assert status == 200
    assert "models" in payload


def test_hostile_origin_is_refused(api) -> None:
    status, payload, _ = _request(
        f"{api.url}/api/models", token=api.token, origin="https://evil.example"
    )
    assert status == 403
    assert "origin" in payload["error"].lower()


def test_allowed_origin_is_echoed(api) -> None:
    status, _, headers = _request(
        f"{api.url}/api/models", token=api.token, origin="http://localhost:5173"
    )
    assert status == 200
    assert headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"


def test_device_profile_is_redacted(api) -> None:
    status, payload, _ = _request(f"{api.url}/api/device/profile", token=api.token)
    assert status == 200
    assert payload["hardware"]["redacted"] is True
    assert "machine_name_hash" not in payload["hardware"]
    assert payload["profile"]["profile"]


def test_journal_requires_confirmation(api) -> None:
    status, payload, _ = _request(
        f"{api.url}/api/journal",
        method="POST",
        body={"body": "geheim"},
        token=api.token,
    )
    assert status == 403
    assert "confirmation" in payload["error"]


def test_journal_create_list_delete(api) -> None:
    status, created, _ = _request(
        f"{api.url}/api/journal",
        method="POST",
        body={"body": "Eintrag mit Inhalt", "mood": 3, "confirmed": True},
        token=api.token,
    )
    assert status == 200
    entry_id = created["id"]

    status, listing, _ = _request(f"{api.url}/api/journal", token=api.token)
    assert any(entry["id"] == entry_id for entry in listing["entries"])

    status, deleted, _ = _request(
        f"{api.url}/api/journal/{entry_id}",
        method="DELETE",
        body={"confirmed": True},
        token=api.token,
    )
    assert status == 200
    assert deleted["deleted"] == entry_id


def test_export_requires_confirmation_and_writes_file(api) -> None:
    status, _, _ = _request(f"{api.url}/api/data/export", method="POST", body={}, token=api.token)
    assert status == 403

    status, payload, _ = _request(
        f"{api.url}/api/data/export", method="POST", body={"confirmed": True}, token=api.token
    )
    assert status == 200
    from pathlib import Path

    assert Path(payload["path"]).is_file()


def test_crisis_message_bypasses_the_model(api) -> None:
    status, payload, _ = _request(
        f"{api.url}/v1/chat/completions",
        method="POST",
        body={
            "messages": [
                {"role": "user", "content": "Ich bringe mich heute Abend um, ich habe die Tabletten schon."}
            ]
        },
        token=api.token,
    )
    assert status == 200
    assert payload["hcs"]["model_bypassed"] is True
    assert payload["hcs"]["policy_mode"] == "crisis_imminent"
    content = payload["choices"][0]["message"]["content"]
    assert "0800 111 0 111" in content
    assert "112" in content


def test_normal_message_without_backend_returns_503(api) -> None:
    status, payload, _ = _request(
        f"{api.url}/v1/chat/completions",
        method="POST",
        body={"messages": [{"role": "user", "content": "Ich hatte einen langen Tag."}]},
        token=api.token,
    )
    assert status == 503
    assert "backend" in payload["error"]


def test_empty_messages_rejected(api) -> None:
    status, payload, _ = _request(
        f"{api.url}/v1/chat/completions", method="POST", body={"messages": []}, token=api.token
    )
    assert status == 400


def test_crisis_events_are_audited_without_content(api) -> None:
    _request(
        f"{api.url}/v1/chat/completions",
        method="POST",
        body={"messages": [{"role": "user", "content": "I want to kill myself tonight."}]},
        token=api.token,
    )
    status, payload, _ = _request(f"{api.url}/api/audit", token=api.token)
    assert status == 200
    events = payload["events"]
    assert any(e["event"] == "crisis_gate" for e in events)
    joined = json.dumps(events)
    assert "kill myself" not in joined


def test_unknown_route_404(api) -> None:
    status, _, _ = _request(f"{api.url}/nope", token=api.token)
    assert status == 404


def test_storage_usage(api) -> None:
    status, payload, _ = _request(f"{api.url}/api/storage/usage", token=api.token)
    assert status == 200
    assert payload["models_count"] == 0


def test_safety_resources_endpoint(api) -> None:
    status, payload, _ = _request(f"{api.url}/api/safety/resources", token=api.token)
    assert status == 200
    assert "DE" in payload["packs"]
    assert payload["reviewed_at"]
