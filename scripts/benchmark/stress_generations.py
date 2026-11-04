"""Repeated-generation stress test — the M1 gate.

Runs N short generations against a live sidecar and records:
  * failures (crash, timeout, empty output),
  * latency percentiles and tokens/second,
  * peak working set of the server process,
  * the exact profile and model revision used.

Usage:
    python scripts/benchmark/stress_generations.py --backend vulkan --count 100
    python scripts/benchmark/stress_generations.py --backend cpu --count 20 --json

Exit code is 0 only when every generation produced non-empty text.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import statistics
import time
import urllib.error
import urllib.request
from ctypes import wintypes

from hcs_therapy.hardware import detect
from hcs_therapy.models.store import ModelStore
from hcs_therapy.paths import paths as resolve_paths
from hcs_therapy.profiles import QWEN3_1_7B, ModelGeometry, ProfileName, assess
from hcs_therapy.runtime.llama_server import (
    LlamaServer,
    ServerConfig,
    find_server_binary,
    free_port,
)


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def working_set_gib(pid: int) -> float | None:
    if not hasattr(ctypes, "windll"):
        return None
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if ctypes.WinDLL("psapi").GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return round(counters.WorkingSetSize / 1024**3, 2)
        return None
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def one_completion(port: int, prompt: str, max_tokens: int, timeout: float) -> tuple[int, float]:
    payload = {
        "model": "local",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": False,
    }
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 loopback
        body = json.loads(response.read())
    elapsed = time.monotonic() - started
    tokens = int((body.get("usage") or {}).get("completion_tokens") or 0)
    message = (body.get("choices") or [{}])[0].get("message") or {}
    # Reasoners spend the first tokens in reasoning_content; either stream counts.
    generated = (message.get("content") or "") + (message.get("reasoning_content") or "")
    if not generated.strip():
        raise RuntimeError("empty completion")
    return tokens, elapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["auto", "cpu", "vulkan"], default="auto")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--max-tokens", type=int, default=48)
    parser.add_argument("--model")
    parser.add_argument("--prompt", default="Antworte mit einem kurzen Satz auf Deutsch.")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = resolve_paths().ensure()
    store = ModelStore(data)
    binary = find_server_binary(data)
    if binary is None:
        print("llama-server not installed; run scripts/bootstrap/fetch_llama_server.ps1")
        return 2

    model_id = args.model or next((m.id for m in store.installed() if m.id.endswith("gguf-q8-0")), None)
    if model_id is None:
        print("no GGUF model installed; run: hcs-therapy models install qwen3-1.7b-gguf-q8-0 --accept-license")
        return 2

    model_path = store.primary_path(model_id)
    manifest = store.manifest(model_id)
    geometry = QWEN3_1_7B
    if manifest.geometry:
        geometry = ModelGeometry(
            n_layers=manifest.geometry.n_layers,
            n_kv_heads=manifest.geometry.n_kv_heads,
            head_dim=manifest.geometry.head_dim,
            n_params=manifest.geometry.n_params,
        )

    hardware = detect()
    assessment = assess(hardware, geometry, model_path.stat().st_size)
    if args.backend == "cpu":
        assessment.backend = "cpu"
        assessment.n_gpu_layers = 0
        assessment.profile = ProfileName.SAFE_CPU
    elif args.backend == "vulkan" and not hardware.vulkan.usable:
        print("Vulkan requested but no usable device")
        return 2

    config = ServerConfig(
        model_path=model_path,
        context=min(assessment.context, 4096),
        n_gpu_layers=assessment.n_gpu_layers,
        port=free_port(),
    )
    server = LlamaServer(binary, config, data)
    report: dict = {
        "model": model_id,
        "model_revision": manifest.revision,
        "backend": assessment.backend,
        "profile": assessment.profile.value,
        "n_gpu_layers": assessment.n_gpu_layers,
        "context": config.context,
        "count": args.count,
        "hardware": {
            "cpu": hardware.cpu_name,
            "ram_gib": hardware.ram_total_gib,
            "vulkan_devices": [d.name for d in hardware.vulkan.devices],
        },
    }

    latencies: list[float] = []
    tokens_total = 0
    failures: list[str] = []
    started = time.monotonic()
    try:
        server.start(ready_timeout=args.timeout)
        report["load_seconds"] = round(time.monotonic() - started, 2)
        for index in range(args.count):
            try:
                tokens, elapsed = one_completion(
                    config.port, args.prompt, args.max_tokens, args.timeout
                )
                latencies.append(elapsed)
                tokens_total += tokens
            except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
                failures.append(f"#{index + 1}: {type(exc).__name__}: {exc}")
                if len(failures) >= 3:
                    failures.append("aborting after 3 failures")
                    break
        status = server.status()
        report["pid_working_set_gib"] = working_set_gib(status.pid) if status.pid else None
    finally:
        server.stop()

    wall = time.monotonic() - started
    report.update(
        {
            "completed": len(latencies),
            "failed": len(failures),
            "failures": failures[:10],
            "wall_seconds": round(wall, 2),
            "tokens_total": tokens_total,
            "tokens_per_second": round(tokens_total / wall, 2) if wall > 0 else None,
            "latency_ms": {
                "mean": round(statistics.fmean(latencies) * 1000, 1) if latencies else None,
                "p50": round(statistics.median(latencies) * 1000, 1) if latencies else None,
                "max": round(max(latencies) * 1000, 1) if latencies else None,
            },
            "ok": not failures and len(latencies) == args.count,
        }
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            f"{report['model']} · {report['backend']} · {report['profile']} · "
            f"ctx {report['context']} · {report['completed']}/{report['count']} ok"
        )
        print(f"load {report.get('load_seconds')} s · wall {report['wall_seconds']} s · "
              f"{report['tokens_per_second']} tok/s")
        print(f"latency {report['latency_ms']}")
        print(f"server working set: {report.get('pid_working_set_gib')} GiB")
        for failure in failures[:10]:
            print("  FAIL " + failure)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
