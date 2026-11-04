"""Command-line surface. One documented entry point, machine-readable output."""

from __future__ import annotations

import argparse
import contextlib
import json
import secrets
import sys
import time
from pathlib import Path
from typing import Any

from . import CREDIT, PRODUCT_NAME, __version__
from .agent.policy import BudgetState, LoopBudget, PolicyDenied, PolicyGate
from .agent.tools import ToolError, build_registry
from .datasets import (
    check_leakage,
    load_dataset_manifests,
    scan_jsonl,
    validated_training_records,
)
from .hardware import detect as detect_hardware
from .licensing import generate as generate_attribution
from .models.manifest import ManifestError, load_license_manifest
from .models.store import ModelStore, StoreError
from .paths import Paths, repo_root
from .paths import paths as resolve_paths
from .profiles import QWEN3_1_7B, ProfileName
from .profiles import assess as assess_profile
from .runtime.llama_server import (
    LlamaServer,
    ServerConfig,
    find_server_binary,
    free_port,
    probe_backend,
)
from .safety import (
    assess as assess_crisis,
)
from .safety import (
    render_resources,
    scan_output,
)
from .storage import Database
from .svg import SceneError, SvgError, render_scene, sanitize_svg

EXIT_OK = 0
EXIT_FAIL = 1


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def _emit(payload: Any, as_json: bool) -> None:
    if as_json:
        _print_json(payload)
    else:
        print(_humanise(payload))


def _humanise(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> int:
    hardware = detect_hardware()
    if args.no_vulkan:
        hardware.vulkan.devices = []
        hardware.vulkan.device_count = 0
        hardware.vulkan.instance_created = False
        hardware.vulkan.error = "disabled with --no-vulkan"

    store = ModelStore(resolve_paths(args.home))
    profile = assess_profile(hardware, QWEN3_1_7B)
    installed = [m.id for m in store.installed()]
    binary = find_server_binary(resolve_paths(args.home))

    payload = {
        "product": PRODUCT_NAME,
        "version": __version__,
        "credit": CREDIT,
        "python": sys.version.split()[0],
        "hardware": hardware.to_dict(redact=True),
        "profile": profile.to_dict(),
        "runtime": {
            "llama_server": str(binary) if binary else None,
            "backend_probe": probe_backend(binary) if (binary and args.probe) else None,
        },
        "models": {"installed": installed, "count": len(installed)},
        "paths": resolve_paths(args.home).as_dict(),
        "checks": _doctor_checks(hardware, binary, installed),
    }
    if args.json:
        _print_json(payload)
        return EXIT_OK if all(c["ok"] for c in payload["checks"] if c["required"]) else EXIT_FAIL

    hw = payload["hardware"]
    lines = [
        f"{PRODUCT_NAME} {__version__}  ({CREDIT})",
        "",
        f"OS          : {hw['os_name']} {hw['os_version']} ({hw['architecture']})",
        f"CPU         : {hw['cpu_name']} · {hw['cpu_cores']} cores · SIMD {', '.join(hw['cpu_simd']) or 'n/a'}",
        f"RAM         : {hw['ram_available_gib']} GiB free of {hw['ram_total_gib']} GiB",
        f"GPU         : {', '.join(g['name'] for g in hw['gpus']) or 'none detected'}",
        "Vulkan      : "
        + (
            f"{hw['vulkan']['devices'][0]['name']} ({hw['vulkan']['devices'][0]['device_type']}, "
            f"Vulkan {hw['vulkan']['devices'][0]['api_version']}, "
            f"{hw['vulkan']['devices'][0]['device_local_memory_gib']} GiB device-local)"
            if hw["vulkan"]["devices"]
            else f"not usable ({hw['vulkan'].get('error') or 'no device'})"
        ),
        f"Profile     : {payload['profile']['profile']} · ctx {payload['profile']['context']} · "
        f"{payload['profile']['n_gpu_layers']} GPU layers",
        f"llama-server: {payload['runtime']['llama_server'] or 'NOT FOUND'}",
        f"Models      : {', '.join(installed) if installed else 'none installed'}",
        f"Data dir    : {payload['paths']['root']}",
        "",
        "Checks:",
    ]
    for check in payload["checks"]:
        mark = "OK  " if check["ok"] else ("FAIL" if check["required"] else "WARN")
        lines.append(f"  [{mark}] {check['name']}: {check['detail']}")
    print("\n".join(lines))
    return EXIT_OK if all(c["ok"] for c in payload["checks"] if c["required"]) else EXIT_FAIL


def _doctor_checks(hardware, binary: Path | None, installed: list[str]) -> list[dict]:
    checks = [
        {
            "name": "python",
            "ok": sys.version_info >= (3, 11),
            "required": True,
            "detail": f"Python {sys.version.split()[0]}",
        },
        {
            "name": "ram",
            "ok": hardware.ram_total_bytes >= 8 * 1024**3,
            "required": True,
            "detail": f"{hardware.ram_total_gib} GiB total",
        },
        {
            "name": "disk",
            "ok": max(hardware.disk_free_bytes.values() or [0]) >= 4 * 1024**3,
            "required": True,
            "detail": "largest free volume "
            + f"{round(max(hardware.disk_free_bytes.values() or [0]) / 1024**3, 1)} GiB",
        },
        {
            "name": "llama-server",
            "ok": binary is not None,
            "required": False,
            "detail": str(binary) if binary else "not installed; inference unavailable until bundled",
        },
        {
            "name": "model",
            "ok": bool(installed),
            "required": False,
            "detail": ", ".join(installed) if installed else "no model installed",
        },
        {
            "name": "vulkan",
            "ok": hardware.vulkan.usable,
            "required": False,
            "detail": hardware.vulkan.devices[0].name
            if hardware.vulkan.devices
            else (hardware.vulkan.error or "no device"),
        },
    ]
    return checks


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------


def cmd_models(args: argparse.Namespace) -> int:
    paths = resolve_paths(args.home)
    store = ModelStore(paths)
    if args.models_command == "list":
        installed = {m.id: m for m in store.installed()}
        rows = []
        for manifest in store.manifests():
            rows.append(
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "publisher": manifest.publisher,
                    "quantisation": manifest.quantisation,
                    "license": manifest.license_spdx,
                    "size_gib": round(manifest.total_size_bytes / 1024**3, 2),
                    "approved": manifest.approved,
                    "installed": manifest.id in installed,
                }
            )
        payload = {"models": rows, "count": len(rows)}
        if args.json:
            _print_json(payload)
        elif not rows:
            print("No model manifests found in models/manifests.")
        else:
            for row in rows:
                state = "installed" if row["installed"] else "not installed"
                approval = "approved" if row["approved"] else "NOT APPROVED"
                print(
                    f"{row['id']:38} {row['size_gib']:>6} GiB  {row['license']:<12} "
                    f"{approval:<13} {state}"
                )
        return EXIT_OK

    if args.models_command == "verify":
        targets = (
            [m.id for m in store.installed()] if args.all else [args.model_id]
        )
        if not targets:
            print("nothing installed to verify")
            return EXIT_OK
        results = [store.verify(model_id, deep=args.deep) for model_id in targets]
        payload = {
            "results": [
                {"model": r.model_id, "ok": r.ok, "checked": r.checked, "problems": r.problems}
                for r in results
            ]
        }
        if args.json:
            _print_json(payload)
        else:
            for r in results:
                print(f"{r.model_id}: {'OK' if r.ok else 'FAILED'} ({r.checked} file(s) checked)")
                for problem in r.problems:
                    print(f"  - {problem}")
        return EXIT_OK if all(r.ok for r in results) else EXIT_FAIL

    if args.models_command == "install":
        manifest = store.manifest(args.model_id)
        if not args.accept_license:
            print(
                f"{manifest.name} is licensed under {manifest.license_spdx}.\n"
                f"Read {manifest.license_url} and re-run with --accept-license."
            )
            return EXIT_FAIL
        last = {"shown": -1}

        def progress(done: int, total: int | None) -> None:
            if total:
                percent = int(done * 100 / total)
                if percent // 10 != last["shown"] // 10:
                    last["shown"] = percent
                    print(f"  {percent:3d}%  {done / 1024**3:.2f} / {total / 1024**3:.2f} GiB")

        try:
            results = store.install(
                args.model_id,
                accept_license=True,
                allow_unapproved=args.allow_unapproved,
                progress=progress if not args.json else None,
            )
        except StoreError as exc:
            print(f"install failed: {exc}")
            return EXIT_FAIL
        payload = {
            "model": args.model_id,
            "files": [
                {
                    "path": str(r.path),
                    "size_bytes": r.size_bytes,
                    "sha256": r.sha256,
                    "throughput_mib_s": r.throughput_mib_s,
                }
                for r in results
            ],
        }
        _emit(payload, args.json)
        return EXIT_OK

    if args.models_command == "remove":
        try:
            store.remove(args.model_id)
        except StoreError as exc:
            print(f"remove failed: {exc}")
            return EXIT_FAIL
        print(f"removed {args.model_id}")
        return EXIT_OK

    raise SystemExit("unknown models subcommand")


# ---------------------------------------------------------------------------
# runtime
# ---------------------------------------------------------------------------


def cmd_runtime(args: argparse.Namespace) -> int:
    paths = resolve_paths(args.home)
    store = ModelStore(paths)
    binary = find_server_binary(paths, getattr(args, "binary", None))
    if args.runtime_command == "status":
        profile = assess_profile(detect_hardware(), QWEN3_1_7B)
        payload = {
            "binary": str(binary) if binary else None,
            "profile": profile.to_dict(),
            "installed": [m.id for m in store.installed()],
        }
        _emit(payload, args.json)
        return EXIT_OK if binary else EXIT_FAIL

    if args.runtime_command == "smoke":
        return _runtime_smoke(args, paths, store, binary)

    raise SystemExit("unknown runtime subcommand")


def _first_gguf_model(store: ModelStore) -> str | None:
    """First installed model whose weights llama.cpp can actually load."""
    for model in store.installed():
        try:
            if model.primary_path().suffix.lower() == ".gguf":
                return model.id
        except (StopIteration, ValueError):
            continue
    return None


def _runtime_smoke(args, paths: Paths, store: ModelStore, binary: Path | None) -> int:
    if binary is None:
        print(
            "llama-server binary not found. Set HCS_LLAMA_SERVER or place it in "
            f"{paths.runtime}",
            file=sys.stderr,
        )
        return EXIT_FAIL
    model_id = args.model or _first_gguf_model(store)
    if model_id is None:
        print(
            "no GGUF model installed. llama.cpp cannot load safetensors; run: "
            "hcs-therapy models list, then models install <gguf-id> --accept-license",
            file=sys.stderr,
        )
        return EXIT_FAIL
    try:
        model_path = store.primary_path(model_id)
    except StoreError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAIL
    if model_path.suffix.lower() != ".gguf":
        print(
            f"{model_id} is not a GGUF file ({model_path.name}); llama-server cannot load it",
            file=sys.stderr,
        )
        return EXIT_FAIL

    hardware = detect_hardware()
    manifest = None
    with contextlib.suppress(StoreError):
        manifest = store.manifest(model_id)
    geometry = QWEN3_1_7B
    if manifest and manifest.geometry:
        from .profiles import ModelGeometry

        geometry = ModelGeometry(
            n_layers=manifest.geometry.n_layers,
            n_kv_heads=manifest.geometry.n_kv_heads,
            head_dim=manifest.geometry.head_dim,
        )
    assessment = assess_profile(hardware, geometry, model_path.stat().st_size)
    if args.backend == "cpu":
        assessment.backend = "cpu"
        assessment.n_gpu_layers = 0
        assessment.profile = ProfileName.SAFE_CPU
    elif args.backend == "vulkan" and not hardware.vulkan.usable:
        print("requested Vulkan but no usable Vulkan device was detected", file=sys.stderr)
        return EXIT_FAIL

    config = ServerConfig(
        model_path=model_path,
        context=min(assessment.context, 4096),
        n_gpu_layers=assessment.n_gpu_layers,
        port=free_port(),
        api_key=secrets.token_urlsafe(24),
    )
    server = LlamaServer(binary, config, paths)
    started = time.monotonic()
    report: dict[str, Any] = {
        "model": model_id,
        "backend": assessment.backend,
        "profile": assessment.profile.value,
        "context": config.context,
        "n_gpu_layers": config.n_gpu_layers,
        "speed_ok": False,
    }
    try:
        server.start(ready_timeout=args.timeout)
        report["load_seconds"] = round(time.monotonic() - started, 2)
        first_token = None
        tokens = 0
        text_parts: list[str] = []
        request_started = time.monotonic()
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": args.prompt}],
            "max_tokens": args.max_tokens,
            "temperature": 0.2,
            "stream": False,
        }
        import urllib.request

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        request = urllib.request.Request(
            f"http://127.0.0.1:{config.port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=args.timeout) as response:  # noqa: S310
            body = json.loads(response.read())
        elapsed = time.monotonic() - request_started
        message = (body.get("choices") or [{}])[0].get("message") or {}
        # Qwen3-class models emit a separate reasoning stream. A short budget can
        # be entirely consumed there, so both fields count as real generation.
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""
        generated = content or reasoning
        usage = body.get("usage") or {}
        tokens = int(usage.get("completion_tokens") or 0)
        text_parts.append(generated)
        report.update(
            {
                "first_token_seconds": round(first_token, 3) if first_token else None,
                "completion_tokens": tokens,
                "seconds": round(elapsed, 2),
                "tokens_per_second": round(tokens / elapsed, 2) if elapsed > 0 and tokens else None,
                "usage": usage,
                "sample": generated[:280],
                "has_reasoning_stream": bool(reasoning),
                "speed_ok": bool(generated.strip()),
            }
        )
        _emit(report, args.json)
        return EXIT_OK if report["speed_ok"] else EXIT_FAIL
    except Exception as exc:  # noqa: BLE001
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["server_log_tail"] = server.tail_log(25)
        _emit(report, args.json)
        return EXIT_FAIL
    finally:
        server.stop()


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


def cmd_serve(args: argparse.Namespace) -> int:
    from .runtime.api import serve

    paths = resolve_paths(args.home).ensure()
    store = ModelStore(paths)
    backend = None
    backend_port = None
    backend_key = None
    model_id = args.model or (_first_gguf_model(store) if args.start_backend else None)

    if args.start_backend:
        binary = find_server_binary(paths)
        if binary is None:
            print(
                "cannot start the backend: llama-server is not installed. "
                "Run scripts/bootstrap/fetch_llama_server.ps1",
                file=sys.stderr,
            )
            return EXIT_FAIL
        if model_id is None:
            print("cannot start the backend: no GGUF model installed", file=sys.stderr)
            return EXIT_FAIL
        model_path = store.primary_path(model_id)
        hardware = detect_hardware()
        assessment = assess_profile(hardware, QWEN3_1_7B, model_path.stat().st_size)
        backend_key = secrets.token_urlsafe(24)
        backend_port = free_port()
        backend = LlamaServer(
            binary,
            ServerConfig(
                model_path=model_path,
                context=assessment.context,
                n_gpu_layers=assessment.n_gpu_layers,
                port=backend_port,
                api_key=backend_key,
            ),
            paths,
        )
        print(
            f"starting backend: {model_id} | {assessment.profile.value} | "
            f"ctx {assessment.context} | {assessment.n_gpu_layers} GPU layers",
            flush=True,
        )
        try:
            backend.start(ready_timeout=args.timeout)
        except Exception as exc:  # noqa: BLE001 - report, do not traceback at the user
            print(f"backend failed to start: {exc}", file=sys.stderr)
            return EXIT_FAIL

    try:
        running = serve(
            paths,
            port=args.port,
            model_id=model_id,
            backend_port=backend_port,
            backend_key=backend_key,
            locale=args.locale,
            region=args.region,
            encrypt=not args.no_encrypt,
        )
    except OSError as exc:
        if backend is not None:
            backend.stop()
        print(f"cannot bind 127.0.0.1:{args.port}: {exc}", file=sys.stderr)
        return EXIT_FAIL

    token_file = paths.root / "api-token.txt"
    token_file.write_text(running.token, encoding="utf-8")
    print(f"local API on {running.url}")
    print(f"backend: {'running' if backend is not None else 'not started'}")
    print(f"token: {running.token}")
    print(f"token file: {token_file}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        running.stop()
        if backend is not None:
            backend.stop()
        print("\nstopped")
    return EXIT_OK


# ---------------------------------------------------------------------------
# eval
# ---------------------------------------------------------------------------


def cmd_eval(args: argparse.Namespace) -> int:
    from .evals import build_suite, compare_reports, run_suite, suite_names, write_report

    paths = resolve_paths(args.home)
    if args.eval_command == "suites":
        _emit({"local_suites": suite_names()}, args.json)
        return EXIT_OK

    if args.eval_command == "compare":
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
        result = compare_reports(baseline, candidate)
        _emit(result, args.json)
        return EXIT_OK if result["verdict"] == "no_regression" else EXIT_FAIL

    if args.eval_command != "run":
        raise SystemExit("unknown eval subcommand")

    checks = build_suite(args.suite)
    if args.provider == "echo":
        provider = lambda messages: messages[-1]["content"]  # noqa: E731
        provider_name = "echo"
        model_id = None
    else:
        provider, provider_name, model_id = _local_provider(args, paths)

    report = run_suite(
        checks,
        provider,
        name=args.suite,
        provider_name=provider_name,
        model_id=model_id,
        repo=repo_root(),
        notes=[
            "Local suite only. External benchmarks are not bundled and must be run "
            "through their own authorised runners.",
        ],
    )
    target = write_report(report, Path(args.out) if args.out else paths.reports)
    payload = report.to_dict()
    payload["report_path"] = str(target)
    if args.json:
        _print_json(payload)
    else:
        print(f"{report.suite}: overall {report.overall:.3f} over {len(report.results)} checks")
        for dimension, stats in report.dimensions.items():
            print(f"  {dimension:16} mean {stats['mean']:.3f}  n={stats['n']}")
        print(f"report: {target}")
    fails = [r for r in report.results if r.score.value < 0.5]
    return EXIT_OK if not fails else EXIT_FAIL


def _local_provider(args, paths: Paths):
    import urllib.request

    store = ModelStore(paths)
    model_id = args.model or next((m.id for m in store.installed()), None)
    if model_id is None:
        raise SystemExit("no model installed; use --provider echo or install a model")
    binary = find_server_binary(paths)
    if binary is None:
        raise SystemExit("llama-server not found")
    hardware = detect_hardware()
    assessment = assess_profile(hardware, QWEN3_1_7B, store.primary_path(model_id).stat().st_size)
    config = ServerConfig(
        model_path=store.primary_path(model_id),
        context=min(assessment.context, 4096),
        n_gpu_layers=assessment.n_gpu_layers,
        port=free_port(),
    )
    server = LlamaServer(binary, config, paths)
    server.start(ready_timeout=args.timeout)

    from .safety import system_prompt

    def provider(messages: list[dict[str, str]]) -> str:
        payload = {
            "model": model_id,
            "messages": [{"role": "system", "content": system_prompt(args.locale)}, *messages],
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
            "stream": False,
        }
        request = urllib.request.Request(
            f"http://127.0.0.1:{config.port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=args.timeout) as response:  # noqa: S310
            body = json.loads(response.read())
        if not body.get("choices"):
            return ""
        return (body["choices"][0].get("message") or {}).get("content") or ""

    import atexit

    atexit.register(server.stop)
    return provider, "local-llama-server", model_id


# ---------------------------------------------------------------------------
# data / safety / licensing / svg / agent
# ---------------------------------------------------------------------------


def cmd_data(args: argparse.Namespace) -> int:
    root = repo_root()
    if args.data_command == "validate":
        directory = Path(args.dir) if args.dir else root / "datasets" / "manifests"
        manifests = load_dataset_manifests(directory)
        problems: list[str] = []
        for manifest in manifests:
            problems.extend(f"{manifest.id}: {p}" for p in manifest.validate())
        known_sources = {m.id for m in manifests}
        accept_dir = root / "datasets" / "train"
        notes: list[str] = []
        scans = []
        if accept_dir.is_dir():
            for path in sorted(accept_dir.glob("*.jsonl")):
                scan = scan_jsonl(path, known_sources)
                scans.append(scan)
                problems.extend(f"{path.name}:{p.line}: {p.problem}" for p in scan.problems)
                problems.extend(f"{path.name}:{line}: PII {kind}" for line, kind in scan.pii_hits)
                if scan.smoke_only:
                    notes.append(
                        f"{path.name}: engineering-smoke data; trainable only with an explicit "
                        "smoke flag and never promotable"
                    )
        strict, strict_notes = validated_training_records(accept_dir, known_sources) if accept_dir.is_dir() else ([], [])
        smoke, _ = (
            validated_training_records(accept_dir, known_sources, allow_smoke=True)
            if accept_dir.is_dir()
            else ([], [])
        )
        notes.extend(n for n in strict_notes if "engineering-smoke" in n)
        payload = {
            "manifests": len(manifests),
            "problems": problems,
            "notes": notes,
            "files": [s.to_dict() for s in scans],
            "trainable_records": len(strict),
            "smoke_records": len(smoke),
            "ok": not problems,
        }
        _emit(payload, args.json)
        return EXIT_OK if payload["ok"] else EXIT_FAIL

    if args.data_command == "scan":
        scan = scan_jsonl(Path(args.path))
        _emit(scan.to_dict(), args.json)
        return EXIT_OK if scan.ok else EXIT_FAIL

    if args.data_command == "leakage":
        root_dir = repo_root()
        train_files = sorted((root_dir / "datasets" / "train").glob("*.jsonl"))
        eval_files = sorted(
            list((root_dir / "evals" / "holdout").glob("*.jsonl"))
            + list((root_dir / "evals" / "external").glob("*.jsonl"))
            + list((root_dir / "evals" / "hcs_local").glob("*.jsonl"))
        )
        problems = check_leakage(train_files, eval_files)
        payload = {
            "train_files": [p.name for p in train_files],
            "eval_files": [p.name for p in eval_files],
            "leaks": problems,
            "ok": not problems,
        }
        _emit(payload, args.json)
        return EXIT_OK if payload["ok"] else EXIT_FAIL

    raise SystemExit("unknown data subcommand")


def cmd_safety(args: argparse.Namespace) -> int:
    if args.safety_command == "assess":
        result = assess_crisis(args.text)
        payload = result.to_dict()
        if payload["show_resources"]:
            payload["resources"] = render_resources(args.region, args.locale)
        _emit(payload, args.json)
        return EXIT_OK

    if args.safety_command == "scan":
        result = scan_output(args.text)
        _emit(result.to_dict(), args.json)
        return EXIT_OK if result.ok else EXIT_FAIL

    if args.safety_command == "resources":
        from .safety import resources_dict

        _emit(resources_dict(), True)
        return EXIT_OK

    raise SystemExit("unknown safety subcommand")


def cmd_license(args: argparse.Namespace) -> int:
    root = repo_root()
    if args.license_command == "verify":
        entries = load_license_manifest(root / "licenses" / "manifest.yaml")
        problems: list[str] = []
        for entry in entries:
            problems.extend(entry.validate())
        unapproved = [e.id for e in entries if not e.approved]
        payload = {
            "entries": len(entries),
            "approved": len(entries) - len(unapproved),
            "unapproved": unapproved,
            "problems": problems,
            "ok": not problems,
        }
        _emit(payload, args.json)
        return EXIT_OK if payload["ok"] else EXIT_FAIL

    if args.license_command == "generate":
        written = generate_attribution(root)
        _emit({"written": [str(p) for p in written]}, args.json)
        return EXIT_OK

    raise SystemExit("unknown license subcommand")


def cmd_svg(args: argparse.Namespace) -> int:
    if args.svg_command == "sanitize":
        data = Path(args.path).read_text(encoding="utf-8") if args.path else sys.stdin.read()
        try:
            result = sanitize_svg(data)
        except SvgError as exc:
            print(f"rejected: {exc}", file=sys.stderr)
            return EXIT_FAIL
        if args.out:
            Path(args.out).write_text(result.svg, encoding="utf-8")
        _emit({"removed": result.removed, "clean": result.clean, "svg": result.svg if not args.out else None}, args.json)
        return EXIT_OK

    if args.svg_command == "render":
        scene = json.loads(Path(args.path).read_text(encoding="utf-8")) if args.path else json.loads(sys.stdin.read())
        try:
            svg = render_scene(scene)
        except SceneError as exc:
            print(f"rejected: {exc}", file=sys.stderr)
            return EXIT_FAIL
        if args.out:
            Path(args.out).write_text(svg, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(svg)
        return EXIT_OK

    raise SystemExit("unknown svg subcommand")


def cmd_train(args: argparse.Namespace) -> int:
    from .train import TrainingError, load_config, plan_training, run_training

    paths = resolve_paths(args.home).ensure()
    try:
        config = load_config(Path(args.config))
    except (OSError, TrainingError) as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return EXIT_FAIL
    plan = plan_training(config, root=repo_root(), paths=paths)
    if args.train_command == "plan":
        _emit(plan.to_dict(), args.json)
        return EXIT_OK if plan.can_run else EXIT_FAIL

    if args.train_command == "smoke":
        if args.base_model_path:
            base_model = Path(args.base_model_path)
        else:
            base_id = str(config.base_model.get("id", ""))
            base_model = paths.models / base_id
        try:
            result = run_training(
                plan,
                paths,
                base_model_path=base_model,
                steps_override=args.steps,
                resume=args.resume,
            )
        except TrainingError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return EXIT_FAIL
        _emit(result.to_dict(), args.json)
        return EXIT_OK

    raise SystemExit("unknown train subcommand")


def cmd_agent(args: argparse.Namespace) -> int:
    paths = resolve_paths(args.home).ensure()
    db = Database(paths, encrypt=True)
    try:
        registry = build_registry(paths)
        if args.agent_command == "tools":
            _emit({"tools": registry.describe()}, args.json)
            return EXIT_OK
        if args.agent_command == "call":
            gate = PolicyGate(registry, db)
            state = BudgetState(LoopBudget())
            try:
                outcome = gate.execute(
                    args.tool,
                    json.loads(args.args) if args.args else {},
                    state=state,
                    approved=args.approve,
                )
            except (PolicyDenied, ToolError, json.JSONDecodeError) as exc:
                print(f"denied: {exc}", file=sys.stderr)
                return EXIT_FAIL
            _emit(outcome, args.json)
            return EXIT_OK
        if args.agent_command == "audit":
            _emit({"events": db.audit_events()}, args.json)
            return EXIT_OK
        raise SystemExit("unknown agent subcommand")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hcs-therapy",
        description=f"{PRODUCT_NAME} — local-first wellbeing studio. {CREDIT}",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--home", help="override the local data directory")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="detect hardware, profile and runtime")
    doctor.add_argument("--json", action="store_true")
    doctor.add_argument("--no-vulkan", action="store_true", help="pretend Vulkan is unavailable")
    doctor.add_argument("--probe", action="store_true", help="ask llama-server for its device list")
    doctor.set_defaults(func=cmd_doctor)

    models = sub.add_parser("models", help="model manifests and local store")
    models_sub = models.add_subparsers(dest="models_command", required=True)
    m_list = models_sub.add_parser("list")
    m_list.add_argument("--json", action="store_true")
    m_verify = models_sub.add_parser("verify")
    m_verify.add_argument("model_id", nargs="?")
    m_verify.add_argument("--all", action="store_true")
    m_verify.add_argument("--deep", action="store_true", default=True)
    m_verify.add_argument("--json", action="store_true")
    m_install = models_sub.add_parser("install")
    m_install.add_argument("model_id")
    m_install.add_argument("--accept-license", action="store_true")
    m_install.add_argument("--allow-unapproved", action="store_true")
    m_install.add_argument("--json", action="store_true")
    m_remove = models_sub.add_parser("remove")
    m_remove.add_argument("model_id")
    m_remove.add_argument("--json", action="store_true")
    models.set_defaults(func=cmd_models)

    runtime = sub.add_parser("runtime", help="inference runtime control")
    runtime_sub = runtime.add_subparsers(dest="runtime_command", required=True)
    r_status = runtime_sub.add_parser("status")
    r_status.add_argument("--json", action="store_true")
    r_smoke = runtime_sub.add_parser("smoke")
    r_smoke.add_argument("--model")
    r_smoke.add_argument("--backend", choices=["auto", "cpu", "vulkan"], default="auto")
    r_smoke.add_argument("--binary")
    r_smoke.add_argument("--prompt", default="Say hello in one short sentence.")
    r_smoke.add_argument("--max-tokens", type=int, default=64)
    r_smoke.add_argument("--timeout", type=float, default=300.0)
    r_smoke.add_argument("--json", action="store_true")
    runtime.set_defaults(func=cmd_runtime)

    serve = sub.add_parser("serve", help="start the loopback-only local API")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--model")
    serve.add_argument("--locale", default="de")
    serve.add_argument("--region")
    serve.add_argument("--no-encrypt", action="store_true")
    serve.add_argument(
        "--start-backend",
        action="store_true",
        help="also start llama-server with the first installed GGUF model",
    )
    serve.add_argument("--timeout", type=float, default=600.0)
    serve.set_defaults(func=cmd_serve)

    ev = sub.add_parser("eval", help="evaluation suites")
    ev_sub = ev.add_subparsers(dest="eval_command", required=True)
    ev_run = ev_sub.add_parser("run")
    ev_run.add_argument("--suite", default="hcs-core")
    ev_run.add_argument("--provider", choices=["echo", "local"], default="echo")
    ev_run.add_argument("--model")
    ev_run.add_argument("--out")
    ev_run.add_argument("--max-tokens", type=int, default=256)
    ev_run.add_argument("--temperature", type=float, default=0.2)
    ev_run.add_argument("--timeout", type=float, default=300.0)
    ev_run.add_argument("--locale", default="de")
    ev_run.add_argument("--json", action="store_true")
    ev_cmp = ev_sub.add_parser("compare")
    ev_cmp.add_argument("--baseline", required=True)
    ev_cmp.add_argument("--candidate", required=True)
    ev_cmp.add_argument("--json", action="store_true")
    ev_suites = ev_sub.add_parser("suites")
    ev_suites.add_argument("--json", action="store_true")
    ev.set_defaults(func=cmd_eval)

    data = sub.add_parser("data", help="dataset manifests and scans")
    data_sub = data.add_subparsers(dest="data_command", required=True)
    d_val = data_sub.add_parser("validate")
    d_val.add_argument("--dir")
    d_val.add_argument("--json", action="store_true")
    d_scan = data_sub.add_parser("scan")
    d_scan.add_argument("path")
    d_scan.add_argument("--json", action="store_true")
    d_leak = data_sub.add_parser("leakage")
    d_leak.add_argument("--json", action="store_true")
    data.set_defaults(func=cmd_data)

    safety = sub.add_parser("safety", help="crisis assessment and output guard")
    safety_sub = safety.add_subparsers(dest="safety_command", required=True)
    s_assess = safety_sub.add_parser("assess")
    s_assess.add_argument("text")
    s_assess.add_argument("--region")
    s_assess.add_argument("--locale", default="de")
    s_assess.add_argument("--json", action="store_true")
    s_scan = safety_sub.add_parser("scan")
    s_scan.add_argument("text")
    s_scan.add_argument("--json", action="store_true")
    s_res = safety_sub.add_parser("resources")
    s_res.add_argument("--json", action="store_true")
    safety.set_defaults(func=cmd_safety)

    lic = sub.add_parser("license", help="licence manifest and attribution")
    lic_sub = lic.add_subparsers(dest="license_command", required=True)
    l_verify = lic_sub.add_parser("verify")
    l_verify.add_argument("--json", action="store_true")
    l_gen = lic_sub.add_parser("generate")
    l_gen.add_argument("--json", action="store_true")
    lic.set_defaults(func=cmd_license)

    svg = sub.add_parser("svg", help="sanitise SVG or render a scene")
    svg_sub = svg.add_subparsers(dest="svg_command", required=True)
    s_san = svg_sub.add_parser("sanitize")
    s_san.add_argument("path", nargs="?")
    s_san.add_argument("--out")
    s_san.add_argument("--json", action="store_true")
    s_ren = svg_sub.add_parser("render")
    s_ren.add_argument("path", nargs="?")
    s_ren.add_argument("--out")
    s_ren.add_argument("--json", action="store_true")
    svg.set_defaults(func=cmd_svg)

    train = sub.add_parser("train", help="CPU LoRA training (optional extra)")
    train_sub = train.add_subparsers(dest="train_command", required=True)
    t_plan = train_sub.add_parser("plan", help="validate data + estimate memory, run nothing")
    t_plan.add_argument("--config", default="configs/train/cpu-lora-smoke.yaml")
    t_plan.add_argument("--json", action="store_true")
    t_smoke = train_sub.add_parser("smoke", help="execute the configured run")
    t_smoke.add_argument("--config", default="configs/train/cpu-lora-smoke.yaml")
    t_smoke.add_argument("--base-model-path", help="local path to the base checkpoint")
    t_smoke.add_argument("--steps", type=int)
    t_smoke.add_argument("--resume", action="store_true")
    t_smoke.add_argument("--json", action="store_true")
    train.set_defaults(func=cmd_train)

    agent = sub.add_parser("agent", help="local tool registry")
    agent_sub = agent.add_subparsers(dest="agent_command", required=True)
    a_tools = agent_sub.add_parser("tools")
    a_tools.add_argument("--json", action="store_true")
    a_call = agent_sub.add_parser("call")
    a_call.add_argument("tool")
    a_call.add_argument("--args", default="{}")
    a_call.add_argument("--approve", action="store_true")
    a_call.add_argument("--json", action="store_true")
    a_audit = agent_sub.add_parser("audit")
    a_audit.add_argument("--json", action="store_true")
    agent.set_defaults(func=cmd_agent)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ManifestError as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return EXIT_FAIL
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
