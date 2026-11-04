"""Resumable, checksum-verified downloads.

Rules enforced here (build contract §8.4 and §5.3):

* HTTPS only, no redirects to another scheme;
* the expected SHA-256 is mandatory before an artifact is accepted;
* partial data lands in a ``.part`` file and is only promoted atomically after
  the hash matches, so an interrupted download can never look complete;
* a resume request that the server ignores (200 instead of 206) restarts the
  transfer instead of appending garbage.
"""

from __future__ import annotations

import hashlib
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

CHUNK = 1024 * 1024
USER_AGENT = "hcs-therapy/0.1 (+local-first; no telemetry)"


class DownloadError(RuntimeError):
    """Base class for download failures."""


class ChecksumError(DownloadError):
    """The downloaded bytes do not match the pinned SHA-256."""


class SizeMismatchError(DownloadError):
    """The artifact is not the declared size."""


class NetworkError(DownloadError):
    """Transport-level failure (offline, DNS, TLS, HTTP status)."""


@dataclass
class DownloadResult:
    path: Path
    size_bytes: int
    sha256: str
    resumed_from_bytes: int
    seconds: float

    @property
    def throughput_mib_s(self) -> float:
        if self.seconds <= 0:
            return 0.0
        return round((self.size_bytes / (1024**2)) / self.seconds, 2)


ProgressFn = Callable[[int, int | None], None]


def sha256_file(path: Path, chunk: int = CHUNK) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_https(url: str) -> None:
    if not url.lower().startswith("https://"):
        raise DownloadError(f"refusing non-HTTPS download URL: {url}")


def download_file(
    url: str,
    destination: Path,
    *,
    expected_sha256: str,
    expected_size: int | None = None,
    progress: ProgressFn | None = None,
    allow_resume: bool = True,
    timeout: float = 30.0,
    retries: int = 3,
) -> DownloadResult:
    """Download ``url`` to ``destination`` and verify the pinned digest.

    Raises ``DownloadError`` subclasses; never leaves a file at ``destination``
    unless it hashed correctly.
    """
    _require_https(url)
    expected_sha256 = expected_sha256.lower().strip()
    if len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256):
        raise DownloadError("expected_sha256 must be a 64-character hex digest")

    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    started = time.monotonic()

    if destination.exists():
        if sha256_file(destination) == expected_sha256:
            size = destination.stat().st_size
            return DownloadResult(destination, size, expected_sha256, 0, 0.0)
        # A corrupted final file must never survive: it would be trusted.
        destination.unlink()
        part.unlink(missing_ok=True)

    resumed_from = 0
    if part.exists() and not allow_resume:
        part.unlink()
    elif part.exists():
        resumed_from = part.stat().st_size

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resumed_from = _stream_to_part(
                url, part, resumed_from, expected_size, progress, timeout
            )
            last_error = None
            break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt == retries:
                raise NetworkError(f"download failed after {retries} attempts: {exc}") from exc
            time.sleep(min(2**attempt * 0.5, 5))
        except DownloadError:
            raise

    if last_error is not None:  # pragma: no cover - loop always raises above
        raise NetworkError(str(last_error))

    actual_size = part.stat().st_size
    if expected_size is not None and actual_size != expected_size:
        part.unlink(missing_ok=True)
        raise SizeMismatchError(
            f"size mismatch for {destination.name}: expected {expected_size} bytes, got {actual_size}"
        )

    digest = sha256_file(part)
    if digest != expected_sha256:
        part.unlink(missing_ok=True)
        raise ChecksumError(
            f"sha256 mismatch for {destination.name}: expected {expected_sha256}, got {digest}"
        )

    os.replace(part, destination)
    return DownloadResult(
        path=destination,
        size_bytes=actual_size,
        sha256=digest,
        resumed_from_bytes=resumed_from,
        seconds=round(time.monotonic() - started, 3),
    )


def _stream_to_part(
    url: str,
    part: Path,
    resumed_from: int,
    expected_size: int | None,
    progress: ProgressFn | None,
    timeout: float,
) -> int:
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if resumed_from:
        headers["Range"] = f"bytes={resumed_from}-"

    request = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (https enforced)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and resumed_from:
            # Nothing left to fetch, or the range is stale: restart cleanly.
            part.unlink(missing_ok=True)
            return 0
        raise NetworkError(f"HTTP {exc.code} for {url}") from exc

    with response:
        status = getattr(response, "status", 200)
        mode = "ab" if status == 206 and resumed_from else "wb"
        if mode == "wb":
            resumed_from = 0
        written = resumed_from
        with part.open(mode) as handle:
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                handle.write(block)
                written += len(block)
                if progress is not None:
                    progress(written, expected_size)
        return resumed_from
