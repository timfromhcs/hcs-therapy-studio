"""The region the user sees and the region in the message must be the same one.

The web client keeps the selected region in localStorage; the server keeps a
launch default. If they can disagree, the crisis card and the crisis *message*
show different numbers — the worst possible inconsistency in this product, and
one that only shows up when someone is in trouble.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from hcs_therapy.runtime.api import serve


@pytest.fixture
def api(paths):
    running = serve(paths, port=0, locale="de", encrypt=True)
    yield running
    running.stop()


def _post(url: str, body: dict, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:  # pragma: no cover - surfaced as a test failure
        raise AssertionError(exc.read().decode("utf-8", "replace")) from exc


def _crisis_body(region: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "messages": [{"role": "user", "content": "Ich bringe mich heute Nacht um."}],
    }
    if region is not None:
        body["hcs"] = {"region": region}
    return body


def _answer(payload: dict) -> str:
    return payload["choices"][0]["message"]["content"]


def test_client_region_reaches_the_crisis_message(api) -> None:
    payload = _post(f"{api.url}/v1/chat/completions", _crisis_body("DE"), api.token)
    text = _answer(payload)
    assert payload["hcs"]["model_bypassed"] is True
    assert "112" in text
    assert "Telefonseelsorge" in text
    assert "Örtlicher Notruf" not in text, "a verified DE pack must not degrade to the fallback"


def test_a_different_client_region_gives_that_region(api) -> None:
    payload = _post(f"{api.url}/v1/chat/completions", _crisis_body("UK"), api.token)
    text = _answer(payload)
    assert "999" in text or "111" in text
    assert "Telefonseelsorge" not in text


def test_no_region_falls_back_without_inventing_a_number(api) -> None:
    payload = _post(f"{api.url}/v1/chat/completions", _crisis_body(None), api.token)
    text = _answer(payload)
    assert "Örtlicher Notruf" in text
    assert "112" in text, "the EU number is the only one safe to name without a pack"


def test_an_unknown_region_degrades_to_the_fallback(api) -> None:
    """A hostile or stale client value must not select an arbitrary hotline."""
    payload = _post(f"{api.url}/v1/chat/completions", _crisis_body("XX"), api.token)
    text = _answer(payload)
    assert "Örtlicher Notruf" in text
    assert "Telefonseelsorge" not in text


def test_the_crisis_message_is_single_language(api) -> None:
    """A German answer containing an English line reads as a broken template."""
    payload = _post(f"{api.url}/v1/chat/completions", _crisis_body(None), api.token)
    text = _answer(payload)
    for english in ("Immediate help", "local emergency", "your local", "crisis service and cannot"):
        assert english not in text, f"English leaked into a German response: {english!r}"


def test_the_english_locale_answer_is_english(api) -> None:
    payload = _post(
        f"{api.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "I am going to kill myself tonight."}],
            "hcs": {"region": "UK", "locale": "en"},
        },
        api.token,
    )
    text = _answer(payload)
    assert "Immediate" in text or "emergency" in text.lower()
    assert "Sofort erreichbar" not in text


def test_an_unsupported_locale_is_ignored_not_passed_through(api) -> None:
    payload = _post(
        f"{api.url}/v1/chat/completions",
        {
            "messages": [{"role": "user", "content": "Ich bringe mich heute Nacht um."}],
            "hcs": {"region": "DE", "locale": "xx-YY"},
        },
        api.token,
    )
    assert "Sofort erreichbar" in _answer(payload)
