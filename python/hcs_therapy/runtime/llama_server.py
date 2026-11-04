"""llama.cpp sidecar lifecycle.

We do not embed llama.cpp: we supervise an official ``llama-server`` binary that
ships with the desktop bundle. This module owns process start, readiness,
health, log capture and — critically — guaranteed shutdown.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from ..paths import Paths, repo_root

LOOPBACK = "127.0.0.1"
ENV_BINARY = "HCS_LLAMA_SERVER"


class RuntimeError_(RuntimeError):
    """Runtime/sidecar failure."""


def find_server_binary(paths: Paths | None = None, explicit: str | None = None) -> Path | None:
    """Locate ``llama-server`` in a documented order. Returns None if absent."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    env = os.environ.get(ENV_BINARY)
    if env:
        candidates.append(Path(env))
    if paths is not None:
        candidates.append(paths.runtime / "llama-server.exe")
        candidates.append(paths.runtime / "llama-server")
    candidates.append(repo_root() / "runtime" / "llama-server.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    found = shutil.which("llama-server")
    return Path(found) if found else None


def free_port(preferred: int | None = None) -> int:
    """Pick a loopback port that is actually bindable right now."""
    if preferred is not None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((LOOPBACK, preferred))
                return preferred
            except OSError:
                pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((LOOPBACK, 0))
        return int(probe.getsockname()[1])


@dataclass
class ServerConfig:
    model_path: Path
    context: int = 4096
    n_gpu_layers: int = 0
    threads: int | None = None
    batch: int = 512
    ubatch: int = 512
    flash_attention: bool = False
    port: int | None = None
    extra_args: list[str] = field(default_factory=list)
    #: `llama-server` needs an API key when it is reachable by another local
    #: process; we always set one so an unprivileged local process cannot use it.
    api_key: str | None = None

    def command(self, binary: Path) -> list[str]:
        port = self.port or 8081
        threads = self.threads or max(1, (os.cpu_count() or 4) // 2)
        args = [
            str(binary),
            "--model",
            str(self.model_path),
            "--host",
            LOOPBACK,
            "--port",
            str(port),
            "--ctx-size",
            str(self.context),
            "--n-gpu-layers",
            str(self.n_gpu_layers),
            "--threads",
            str(threads),
            "--batch-size",
            str(self.batch),
            "--ubatch-size",
            str(self.ubatch),
            "--no-webui",
        ]
        if self.flash_attention:
            args.extend(["--flash-attn", "on"])
        if self.api_key:
            args.extend(["--api-key", self.api_key])
        args.extend(self.extra_args)
        return args


@dataclass
class ServerStatus:
    running: bool
    port: int | None
    pid: int | None
    healthy: bool
    model: str | None
    exit_code: int | None = None
    error: str | None = None


class LlamaServer:
    """Owns exactly one llama-server process."""

    def __init__(self, binary: Path, config: ServerConfig, paths: Paths) -> None:
        self.binary = binary
        self.config = config
        self.paths = paths
        self._process: subprocess.Popen[bytes] | None = None
        self._log_handle = None
        self._log_path: Path | None = None

    # -- lifecycle ---------------------------------------------------------
    def start(self, ready_timeout: float = 180.0) -> None:
        if self._process is not None and self._process.poll() is None:
            raise RuntimeError_("llama-server is already running")
        if not self.binary.is_file():
            raise RuntimeError_(f"llama-server binary not found at {self.binary}")
        if not self.config.model_path.is_file():
            raise RuntimeError_(f"model file not found at {self.config.model_path}")

        self.config.port = self.config.port or free_port()
        self.paths.logs.mkdir(parents=True, exist_ok=True)
        self._log_path = self.paths.logs / f"llama-server-{self.config.port}.log"
        self._log_handle = self._log_path.open("wb")

        creationflags = 0
        if os.name == "nt":
            # New process group so we can terminate the tree we created and
            # nothing else.
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        self._process = subprocess.Popen(
            self.config.command(self.binary),
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=str(self.config.model_path.parent),
            creationflags=creationflags,
        )
        try:
            self.wait_ready(ready_timeout)
        except Exception:
            self.stop()
            raise

    def wait_ready(self, timeout: float = 180.0, interval: float = 0.4) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError_(
                    f"llama-server exited early with code {self._process.returncode}; "
                    f"see {self._log_path}"
                )
            if self._health_ok():
                return
            time.sleep(interval)
        raise RuntimeError_(f"llama-server did not become ready within {timeout:.0f}s")

    def _health_ok(self) -> bool:
        if self.config.port is None:
            return False
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = urllib.request.Request(
            f"http://{LOOPBACK}:{self.config.port}/health", headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:  # noqa: S310 loopback
                return response.status == 200
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    def stop(self, timeout: float = 15.0) -> None:
        process, self._process = self._process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        check=False,
                    )
                else:
                    process.kill()
                with contextlib.suppress(subprocess.TimeoutExpired):  # pragma: no cover
                    process.wait(timeout=5)
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None

    def status(self) -> ServerStatus:
        running = self._process is not None and self._process.poll() is None
        return ServerStatus(
            running=running,
            port=self.config.port,
            pid=self._process.pid if self._process else None,
            healthy=self._health_ok() if running else False,
            model=str(self.config.model_path),
            exit_code=self._process.returncode if self._process else None,
            error=None if running else "not running",
        )

    def tail_log(self, lines: int = 40) -> str:
        if self._log_path is None or not self._log_path.is_file():
            return ""
        data = self._log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(data[-lines:])

    def __enter__(self) -> LlamaServer:
        self.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.stop()


def probe_backend(binary: Path, timeout: float = 20.0) -> dict[str, str]:
    """Ask the binary which devices it can see, without loading a model."""
    try:
        completed = subprocess.run(
            [str(binary), "--list-devices"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": str(completed.returncode),
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"returncode": "-1", "stdout": "", "stderr": str(exc)}
