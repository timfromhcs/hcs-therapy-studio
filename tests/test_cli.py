"""CLI surface: exit codes, JSON output, real checks (no fake passes)."""

from __future__ import annotations

import json

import pytest

from hcs_therapy.cli import main


def _json_out(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_version_flag(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_doctor_json_is_real_and_parseable(capsys) -> None:
    code = main(["doctor", "--json"])
    payload = _json_out(capsys)
    assert code == 0
    assert payload["hardware"]["cpu_name"]
    assert payload["profile"]["reasons"]
    assert payload["paths"]["root"]
    required = [c for c in payload["checks"] if c["required"]]
    assert all(c["ok"] for c in required)


def test_doctor_reports_missing_runtime_as_warning_not_error(capsys) -> None:
    code = main(["doctor", "--json"])
    payload = _json_out(capsys)
    runtime_check = next(c for c in payload["checks"] if c["name"] == "llama-server")
    assert runtime_check["required"] is False
    assert code == 0  # a missing optional component must not fail the doctor


def test_doctor_no_vulkan_uses_cpu_profile(capsys) -> None:
    main(["doctor", "--json", "--no-vulkan"])
    payload = _json_out(capsys)
    assert payload["profile"]["profile"] == "SAFE_CPU"
    assert payload["profile"]["backend"] == "cpu"


def test_models_list_finds_manifests(capsys) -> None:
    code = main(["models", "list", "--json"])
    payload = _json_out(capsys)
    assert code == 0
    ids = [row["id"] for row in payload["models"]]
    assert "qwen3-1.7b-gguf-q8-0" in ids
    entry = next(row for row in payload["models"] if row["id"] == "qwen3-1.7b-gguf-q8-0")
    assert entry["approved"] is True
    assert entry["installed"] is False


def test_models_install_requires_licence_acceptance(capsys) -> None:
    code = main(["models", "install", "qwen3-1.7b-gguf-q8-0"])
    out = capsys.readouterr().out
    assert code == 1
    assert "accept-license" in out
    assert "Apache-2.0" in out


def test_models_verify_requires_installation(capsys) -> None:
    code = main(["models", "verify", "qwen3-1.7b-gguf-q8-0", "--json"])
    payload = _json_out(capsys)
    assert code == 1
    assert payload["results"][0]["ok"] is False


def test_models_remove_unknown_fails(capsys) -> None:
    assert main(["models", "remove", "nope"]) == 1


def test_runtime_status_without_binary(capsys) -> None:
    code = main(["runtime", "status", "--json"])
    payload = _json_out(capsys)
    assert code == 1
    assert payload["binary"] is None
    assert payload["profile"]


def test_eval_run_echo_provider(capsys, tmp_path) -> None:
    code = main(["eval", "run", "--suite", "hcs-core", "--provider", "echo", "--json", "--out", str(tmp_path)])
    payload = _json_out(capsys)
    assert payload["suite"] == "hcs-core"
    assert payload["results"]
    assert "dimensions" in payload
    assert code in (0, 1)


def test_eval_compare_reports_regression(capsys, tmp_path) -> None:
    baseline = {
        "suite": "hcs-core",
        "dimensions": {"listening": {"mean": 0.9}},
    }
    candidate = {
        "suite": "hcs-core",
        "dimensions": {"listening": {"mean": 0.1}},
    }
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(baseline), encoding="utf-8")
    c.write_text(json.dumps(candidate), encoding="utf-8")
    code = main(["eval", "compare", "--baseline", str(b), "--candidate", str(c), "--json"])
    payload = _json_out(capsys)
    assert code == 1
    assert payload["verdict"] == "regression"


def test_data_validate_passes_on_shipped_corpus(capsys) -> None:
    code = main(["data", "validate", "--json"])
    payload = _json_out(capsys)
    assert code == 0, payload["problems"]
    assert payload["manifests"] >= 1
    assert payload["smoke_records"] >= 10
    assert payload["trainable_records"] == 0, "smoke data must never count as trainable"
    assert any("engineering-smoke" in note for note in payload["notes"])


def test_data_scan_reports_ok(capsys, repo_root) -> None:
    code = main(["data", "scan", str(repo_root / "datasets" / "train" / "seed-smoke.jsonl"), "--json"])
    payload = _json_out(capsys)
    assert code == 0
    assert payload["ok"] is True
    assert payload["records"] >= 10
    assert payload["pii_hits"] == []


def test_data_leakage_clean(capsys) -> None:
    code = main(["data", "leakage", "--json"])
    payload = _json_out(capsys)
    assert code == 0
    assert payload["leaks"] == []


def test_safety_assess_normal(capsys) -> None:
    code = main(["safety", "assess", "Ich hatte einen langen Tag.", "--json"])
    payload = _json_out(capsys)
    assert code == 0
    assert payload["level"] == "NONE"


def test_safety_assess_crisis_includes_verified_resources(capsys) -> None:
    code = main(
        ["safety", "assess", "Ich bringe mich um", "--region", "DE", "--json"]
    )
    payload = _json_out(capsys)
    assert code == 0
    assert payload["level"] in {"ELEVATED", "IMMINENT"}
    assert "0800 111 0 111" in payload["resources"]


def test_safety_scan_trips_on_diagnosis(capsys) -> None:
    code = main(["safety", "scan", "You have depression.", "--json"])
    payload = _json_out(capsys)
    assert code == 1
    assert payload["ok"] is False
    assert "diagnosis_claim" in payload["categories"]


def test_license_verify_passes(capsys) -> None:
    code = main(["license", "verify", "--json"])
    payload = _json_out(capsys)
    assert code == 0, payload["problems"]
    assert payload["approved"] >= 7
    assert "cbt-bench" in payload["unapproved"]


def test_license_generate_writes_attribution(capsys, repo_root) -> None:
    code = main(["license", "generate", "--json"])
    _json_out(capsys)
    assert code == 0
    for name in ("THIRD_PARTY_NOTICES.md", "MODEL_ATTRIBUTION.md", "SBOM.spdx.json"):
        assert (repo_root / name).is_file(), name
    # External references must appear, and rejected assets must be marked.
    notices = (repo_root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "Qwen3-1.7B" in notices
    assert "not approved" in notices


def test_svg_sanitize_cli(capsys, tmp_path) -> None:
    svg = tmp_path / "in.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<script>alert(1)</script><rect width="5" height="5"/></svg>',
        encoding="utf-8",
    )
    out = tmp_path / "out.svg"
    code = main(["svg", "sanitize", str(svg), "--out", str(out)])
    assert code == 0
    content = out.read_text(encoding="utf-8")
    assert "script" not in content
    assert "rect" in content


def test_svg_sanitize_rejects_doctype(capsys, tmp_path) -> None:
    svg = tmp_path / "bad.svg"
    svg.write_text('<!DOCTYPE svg><svg/>', encoding="utf-8")
    assert main(["svg", "sanitize", str(svg)]) == 1


def test_agent_tools_listing(capsys) -> None:
    code = main(["agent", "tools", "--json"])
    payload = _json_out(capsys)
    assert code == 0
    names = [t["name"] for t in payload["tools"]]
    assert "get_local_time" in names
    assert "run_command" not in names


def test_agent_call_and_audit(capsys) -> None:
    assert main(["agent", "call", "get_local_time", "--json"]) == 0
    payload = _json_out(capsys)
    assert payload["ok"] is True
    assert main(["agent", "audit", "--json"]) == 0
    events = _json_out(capsys)["events"]
    assert any(e["tool"] == "get_local_time" for e in events)


def test_agent_call_rejects_bad_args(capsys) -> None:
    assert main(["agent", "call", "search_local_knowledge_base", "--args", "{}"]) == 1


def test_unknown_command_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["nonsense"])
    assert exc.value.code == 2


def test_missing_subcommand_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
