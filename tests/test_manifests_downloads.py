"""Manifest and downloader integrity rules."""

from __future__ import annotations

import hashlib
import io
import urllib.request
from pathlib import Path

import pytest
import yaml

from hcs_therapy.models.downloader import (
    ChecksumError,
    DownloadError,
    SizeMismatchError,
    download_file,
    sha256_file,
)
from hcs_therapy.models.manifest import ManifestError, load_manifest_file, parse_manifest

REVISION = "a" * 40
DIGEST = "b" * 64


def _raw(**overrides):
    base = {
        "id": "test-model-q4",
        "kind": "model",
        "name": "Test Model",
        "publisher": "Test Publisher",
        "source_url": "https://example.invalid/model",
        "revision": REVISION,
        "license_spdx": "Apache-2.0",
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
        "files": [
            {
                "name": "weights.gguf",
                "url": f"https://example.invalid/resolve/{REVISION}/weights.gguf",
                "sha256": DIGEST,
                "size_bytes": 1234,
            }
        ],
        "approved": False,
    }
    base.update(overrides)
    return base


def test_valid_manifest_parses() -> None:
    manifest = parse_manifest(_raw())
    assert manifest.validate() == []
    assert manifest.total_size_bytes == 1234


@pytest.mark.parametrize(
    "override,needle",
    [
        ({"revision": "main"}, "pinned"),
        ({"license_spdx": "CC-BY-NC-4.0"}, "not on the default allow-list"),
        ({"license_spdx": "unknown"}, "rejected"),
        ({"source_url": "http://example.invalid"}, "https"),
        ({"files": []}, "at least one file"),
        ({"approved": True}, "reviewed_by"),
        (
            {
                "files": [
                    {
                        "name": "weights.gguf",
                        "url": "https://example.invalid/resolve/main/weights.gguf",
                        "sha256": DIGEST,
                    }
                ]
            },
            "pinned revision",
        ),
        (
            {
                "files": [
                    {"name": "w.gguf", "url": "https://x/y", "sha256": "short"}
                ]
            },
            "sha256",
        ),
    ],
)
def test_manifest_rejections(override: dict, needle: str) -> None:
    problems = " ".join(parse_manifest(_raw(**override)).validate())
    assert needle in problems


def test_approved_manifest_needs_reviewer_and_date() -> None:
    manifest = parse_manifest(
        _raw(approved=True, reviewed_by="automated-audit", reviewed_at="2026-11-04")
    )
    assert manifest.validate() == []


def test_manifest_file_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "m.yaml"
    path.write_text(yaml.safe_dump(_raw()), encoding="utf-8")
    manifest = load_manifest_file(path)
    assert manifest.id == "test-model-q4"


def test_bad_yaml_raises(tmp_path: Path) -> None:
    path = tmp_path / "m.yaml"
    path.write_text("id: [unclosed", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest_file(path)


# ---------------------------------------------------------------------------
# downloader
# ---------------------------------------------------------------------------


class FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes, status: int = 200) -> None:
        super().__init__(payload)
        self.status = status

    def __enter__(self):  # noqa: D105
        return self

    def __exit__(self, *exc):  # noqa: D105
        self.close()


def _patch_transport(monkeypatch: pytest.MonkeyPatch, payload: bytes, status: int = 200):
    seen: dict[str, str] = {}

    def fake_urlopen(request, timeout=None):
        seen["range"] = request.headers.get("Range", "")
        seen["url"] = request.full_url
        return FakeResponse(payload, status)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return seen


PAYLOAD = b"model-bytes" * 100
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


def test_download_verifies_and_promotes(tmp_path: Path, monkeypatch) -> None:
    _patch_transport(monkeypatch, PAYLOAD)
    result = download_file(
        "https://example.invalid/f.bin",
        tmp_path / "f.bin",
        expected_sha256=PAYLOAD_SHA,
        expected_size=len(PAYLOAD),
    )
    assert result.sha256 == PAYLOAD_SHA
    assert (tmp_path / "f.bin").read_bytes() == PAYLOAD
    assert not (tmp_path / "f.bin.part").exists()


def test_checksum_mismatch_leaves_nothing(tmp_path: Path, monkeypatch) -> None:
    _patch_transport(monkeypatch, PAYLOAD)
    with pytest.raises(ChecksumError):
        download_file(
            "https://example.invalid/f.bin",
            tmp_path / "f.bin",
            expected_sha256="0" * 64,
        )
    assert not (tmp_path / "f.bin").exists()
    assert not (tmp_path / "f.bin.part").exists()


def test_size_mismatch_is_rejected(tmp_path: Path, monkeypatch) -> None:
    _patch_transport(monkeypatch, PAYLOAD)
    with pytest.raises(SizeMismatchError):
        download_file(
            "https://example.invalid/f.bin",
            tmp_path / "f.bin",
            expected_sha256=PAYLOAD_SHA,
            expected_size=len(PAYLOAD) + 1,
        )


def test_http_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DownloadError, match="HTTPS"):
        download_file("http://example.invalid/f", tmp_path / "f", expected_sha256=PAYLOAD_SHA)


def test_resume_sends_range_header(tmp_path: Path, monkeypatch) -> None:
    part = tmp_path / "f.bin.part"
    part.write_bytes(PAYLOAD[:50])
    tail = PAYLOAD[50:]
    seen = _patch_transport(monkeypatch, tail, status=206)
    result = download_file(
        "https://example.invalid/f.bin",
        tmp_path / "f.bin",
        expected_sha256=PAYLOAD_SHA,
    )
    assert seen["range"] == "bytes=50-"
    assert result.resumed_from_bytes == 50
    assert (tmp_path / "f.bin").read_bytes() == PAYLOAD


def test_server_ignoring_range_restarts_cleanly(tmp_path: Path, monkeypatch) -> None:
    part = tmp_path / "f.bin.part"
    part.write_bytes(b"garbage-prefix")
    _patch_transport(monkeypatch, PAYLOAD, status=200)
    download_file(
        "https://example.invalid/f.bin",
        tmp_path / "f.bin",
        expected_sha256=PAYLOAD_SHA,
    )
    assert (tmp_path / "f.bin").read_bytes() == PAYLOAD


def test_existing_valid_file_is_not_redownloaded(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "f.bin"
    target.write_bytes(PAYLOAD)

    def explode(*args, **kwargs):
        raise AssertionError("must not download a file that already matches its hash")

    monkeypatch.setattr(urllib.request, "urlopen", explode)
    result = download_file("https://example.invalid/f.bin", target, expected_sha256=PAYLOAD_SHA)
    assert result.size_bytes == len(PAYLOAD)


def test_corrupted_existing_file_is_replaced(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "f.bin"
    target.write_bytes(b"corrupt")
    _patch_transport(monkeypatch, PAYLOAD)
    download_file("https://example.invalid/f.bin", target, expected_sha256=PAYLOAD_SHA)
    assert sha256_file(target) == PAYLOAD_SHA
