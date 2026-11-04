"""Training planner: memory gating, data gating, geometry resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from hcs_therapy.train import (
    PROCESS_OVERHEAD_BYTES,
    TrainingError,
    estimate_memory,
    load_config,
    plan_training,
)


def _config(tmp_path: Path, **overrides) -> Path:
    raw = {
        "run": {"name": "unit", "promotable": False},
        "base_model": {"id": "qwen3-0.6b-base", "revision": "a" * 40},
        "dataset": {"directory": "datasets/train", "allow_smoke": True, "max_seq_length": 512},
        "training": {
            "batch_size": 1,
            "gradient_accumulation_steps": 4,
            "gradient_checkpointing": True,
            "max_steps": 2,
            "precision": "auto_safe",
        },
        "lora": {"r": 8, "alpha": 16},
        "memory": {"max_ram_fraction": 0.6, "reserve_gib": 1.0, "refuse_on_insufficient": True},
        "output": {},
        "gates": {"require_reviewed_data": True},
    }
    for key, value in overrides.items():
        raw[key] = {**raw.get(key, {}), **value}
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return path


def _record(status: str = "engineering-smoke") -> dict:
    return {
        "id": "r1",
        "lang": "de",
        "source_id": "hcs-synthetic-seed",
        "license": "Apache-2.0",
        "task": "support_turn",
        "messages": [
            {"role": "user", "content": "Mir geht es heute schwer."},
            {"role": "assistant", "content": "Das klingt belastend. Magst du erzählen?"},
        ],
        "review": {"status": status, "reviewer_role": "project-authors"},
    }


@pytest.fixture
def dataset_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "datasets" / "train"
    directory.mkdir(parents=True)
    (directory / "seed.jsonl").write_text(json.dumps(_record()) + "\n", encoding="utf-8")
    return tmp_path


def test_load_config_reads_yaml(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    assert config.name == "unit"
    assert config.promotable is False


def test_estimate_includes_process_overhead(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    estimate = estimate_memory(
        config, params=596_000_000, hidden_size=1024, n_layers=28, available_ram=12 * 1024**3
    )
    assert estimate.params == 596_000_000
    assert estimate.total_bytes >= PROCESS_OVERHEAD_BYTES
    assert any("process overhead" in reason for reason in estimate.reasons)
    assert estimate.fits is True


def test_estimate_refuses_when_budget_is_tiny(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    estimate = estimate_memory(
        config, params=1_720_000_000, hidden_size=2048, n_layers=28, available_ram=2 * 1024**3
    )
    assert estimate.fits is False
    assert estimate.total_gib > estimate.budget_gib


def test_fp32_is_larger_than_bf16(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    fp32 = estimate_memory(
        config, params=596_000_000, hidden_size=1024, n_layers=28, available_ram=64 * 1024**3
    )
    bf16_config = load_config(_config(tmp_path, training={"precision": "bf16"}))
    bf16 = estimate_memory(
        bf16_config, params=596_000_000, hidden_size=1024, n_layers=28,
        available_ram=64 * 1024**3,
    )
    assert fp32.weights_bytes > bf16.weights_bytes
    assert bf16.dtype == "bf16"


def test_plan_accepts_smoke_data_only_with_allow_smoke(tmp_path: Path, dataset_dir: Path) -> None:
    config = load_config(_config(tmp_path))
    plan = plan_training(config, root=dataset_dir, available_ram=64 * 1024**3)
    assert plan.smoke_only is True
    assert plan.records
    assert plan.problems == []

    strict = load_config(_config(tmp_path, dataset={"allow_smoke": False}))
    strict_plan = plan_training(strict, root=dataset_dir, available_ram=64 * 1024**3)
    assert strict_plan.problems
    assert "engineering-smoke" in strict_plan.problems[0]


def test_promotable_run_refuses_smoke_data(tmp_path: Path, dataset_dir: Path) -> None:
    config = load_config(_config(tmp_path, run={"promotable": True}))
    plan = plan_training(config, root=dataset_dir, available_ram=64 * 1024**3)
    assert plan.can_run is False
    assert any("reviewed data" in problem for problem in plan.problems)


def test_plan_without_data_refuses(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    plan = plan_training(config, root=tmp_path, available_ram=64 * 1024**3)
    assert plan.can_run is False
    assert any("no trainable records" in problem for problem in plan.problems)


def test_plan_geometry_comes_from_manifest_when_available(tmp_path: Path, dataset_dir: Path, paths) -> None:
    """The estimate must use the real model size, not a hardcoded 1.7B default."""
    models = paths.models / "qwen3-0.6b-base"
    models.mkdir(parents=True, exist_ok=True)
    (models / "config.json").write_text(
        json.dumps(
            {
                "hidden_size": 1024,
                "num_hidden_layers": 28,
                "intermediate_size": 3072,
                "vocab_size": 151936,
            }
        ),
        encoding="utf-8",
    )
    config = load_config(_config(tmp_path))
    plan = plan_training(config, root=dataset_dir, paths=paths, available_ram=16 * 1024**3)
    assert plan.memory.params == 596049920, "manifest geometry must win over the fallback"


def test_dataset_hash_is_recorded(tmp_path: Path, dataset_dir: Path) -> None:
    config = load_config(_config(tmp_path))
    plan = plan_training(config, root=dataset_dir)
    assert "seed.jsonl" in plan.dataset_hashes
    assert len(plan.dataset_hashes["seed.jsonl"]) == 64


def test_plan_serialises_for_the_cli(tmp_path: Path, dataset_dir: Path) -> None:
    config = load_config(_config(tmp_path))
    payload = plan_training(config, root=dataset_dir, available_ram=64 * 1024**3).to_dict()
    assert payload["run"] == "unit"
    assert "memory" in payload
    assert json.loads(json.dumps(payload))


def test_training_error_is_a_runtime_error() -> None:
    assert issubclass(TrainingError, RuntimeError)
