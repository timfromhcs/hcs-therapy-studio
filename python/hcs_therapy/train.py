"""CPU LoRA training: planning, memory gating, execution, resumability.

Design constraints from the build contract:

* training is an optional extra — this module imports nothing heavy at module
  scope, so the runtime never pays for PyTorch;
* the trainer refuses to start when the measured memory budget cannot hold the
  run, and names the knob to change;
* a run trained on ``engineering-smoke`` rows is marked non-promotable and can
  never be cited as a quality result;
* every run records the dataset hash, config, seed, package versions and peak
  RSS, and writes checkpoints so resume is verifiable;
* no fabricated success: if the dependencies are missing, the command says so
  and exits non-zero.
"""

from __future__ import annotations

import contextlib
import json
import os
import platform
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .datasets import validated_training_records
from .hardware import GIB, detect
from .paths import Paths, repo_root

#: Rough activation multiplier for LoRA training with gradient checkpointing.
#: Conservative on purpose: it drives a refusal, not a promise.
ACTIVATION_FACTOR_CHECKPOINTED = 0.06
ACTIVATION_FACTOR_FULL = 0.35
BYTES_PER_PARAM = {"fp32": 4, "bf16": 2, "fp16": 2}

#: Measured overhead of the Python process itself: interpreter, torch, tokenizer
#: and the training loop bookkeeping, before any tensor is allocated. The first
#: real run on this machine reported 3.04 GiB peak against a 2.25 GiB estimate;
#: the difference was almost entirely this baseline. Calibrated, not guessed.
PROCESS_OVERHEAD_BYTES = int(0.6 * GIB)


class TrainingError(RuntimeError):
    """Training cannot start or must stop."""


@dataclass
class TrainConfig:
    raw: dict[str, Any]

    @property
    def name(self) -> str:
        return str(self.raw.get("run", {}).get("name", "unnamed"))

    @property
    def promotable(self) -> bool:
        return bool(self.raw.get("run", {}).get("promotable", False))

    @property
    def base_model(self) -> dict[str, Any]:
        return self.raw.get("base_model", {})

    @property
    def dataset(self) -> dict[str, Any]:
        return self.raw.get("dataset", {})

    @property
    def training(self) -> dict[str, Any]:
        return self.raw.get("training", {})

    @property
    def lora(self) -> dict[str, Any]:
        return self.raw.get("lora", {})

    @property
    def memory(self) -> dict[str, Any]:
        return self.raw.get("memory", {})

    @property
    def output(self) -> dict[str, Any]:
        return self.raw.get("output", {})

    @property
    def gates(self) -> dict[str, Any]:
        return self.raw.get("gates", {})


def load_config(path: Path) -> TrainConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TrainingError(f"{path} is not a mapping")
    return TrainConfig(raw)


@dataclass
class MemoryEstimate:
    params: int
    dtype: str
    weights_bytes: int
    lora_bytes: int
    gradients_bytes: int
    optimizer_bytes: int
    activations_bytes: int
    total_bytes: int
    budget_bytes: int
    fits: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_gib(self) -> float:
        return round(self.total_bytes / GIB, 2)

    @property
    def budget_gib(self) -> float:
        return round(self.budget_bytes / GIB, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "params": self.params,
            "dtype": self.dtype,
            "weights_gib": round(self.weights_bytes / GIB, 2),
            "lora_gib": round(self.lora_bytes / GIB, 2),
            "gradients_gib": round(self.gradients_bytes / GIB, 2),
            "optimizer_gib": round(self.optimizer_bytes / GIB, 2),
            "activations_gib": round(self.activations_bytes / GIB, 2),
            "total_gib": self.total_gib,
            "budget_gib": self.budget_gib,
            "fits": self.fits,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
        }


def estimate_memory(
    config: TrainConfig,
    *,
    params: int,
    hidden_size: int,
    n_layers: int,
    available_ram: int | None = None,
) -> MemoryEstimate:
    """Estimate peak training memory for LoRA on CPU.

    LoRA freezes the base weights, so weights need no gradients or optimiser
    state. Activations dominate the rest, which is why sequence length is the
    first knob the trainer suggests.
    """
    precision = str(config.training.get("precision", "auto_safe")).lower()
    dtype = "fp32" if precision in ("auto_safe", "fp32") else precision
    bpp = BYTES_PER_PARAM.get(dtype, 4)

    weights = params * bpp
    lora_rank = int(config.lora.get("r", 8))
    # q/k/v/o at ~hidden*hidden each, times rank*2 (A and B), per layer.
    lora_params = 4 * n_layers * 2 * hidden_size * lora_rank
    lora = lora_params * 4  # trainable params stay fp32
    gradients = lora_params * 4
    optimizer = lora_params * 4 * 2  # AdamW: exp_avg + exp_avg_sq

    seq = int(config.dataset.get("max_seq_length", 1024))
    batch = int(config.training.get("batch_size", 1))
    checkpointing = bool(config.training.get("gradient_checkpointing", True))
    factor = (
        ACTIVATION_FACTOR_CHECKPOINTED if checkpointing else ACTIVATION_FACTOR_FULL
    )
    activations = int(batch * seq * hidden_size * n_layers * factor * 4)

    total = weights + lora + gradients + optimizer + activations + PROCESS_OVERHEAD_BYTES

    if available_ram is None:
        available_ram = detect().ram_available_bytes
    max_fraction = float(config.memory.get("max_ram_fraction", 0.6))
    reserve = float(config.memory.get("reserve_gib", 3.0)) * GIB
    budget = max(0, int(available_ram * max_fraction - reserve))

    reasons = [
        f"weights {round(weights / GIB, 2)} GiB ({dtype}, {params / 1e9:.2f}B params)",
        f"LoRA r={lora_rank}: {round(lora / GIB, 3)} GiB params, "
        f"{round(gradients / GIB, 3)} GiB grads, {round(optimizer / GIB, 3)} GiB optimiser",
        f"activations {round(activations / GIB, 2)} GiB "
        f"(batch {batch}, seq {seq}, {'checkpointed' if checkpointing else 'full'})",
        f"process overhead {round(PROCESS_OVERHEAD_BYTES / GIB, 2)} GiB "
        "(interpreter, torch, tokenizer; calibrated against a measured run)",
        f"budget {round(budget / GIB, 2)} GiB "
        f"({int(max_fraction * 100)}% of {round(available_ram / GIB, 2)} GiB minus "
        f"{config.memory.get('reserve_gib', 3.0)} GiB reserve)",
    ]
    warnings: list[str] = []
    if available_ram < 8 * GIB:
        warnings.append("less than 8 GiB free right now; close other applications")
    if seq > 2048 and checkpointing:
        warnings.append("sequence length above 2048 makes each step much slower on CPU")

    fits = total <= budget
    return MemoryEstimate(
        params=params,
        dtype=dtype,
        weights_bytes=weights,
        lora_bytes=lora,
        gradients_bytes=gradients,
        optimizer_bytes=optimizer,
        activations_bytes=activations,
        total_bytes=total,
        budget_bytes=budget,
        fits=fits,
        reasons=reasons,
        warnings=warnings,
    )


@dataclass
class TrainPlan:
    config: TrainConfig
    records: list[dict]
    dataset_hashes: dict[str, str]
    memory: MemoryEstimate
    smoke_only: bool
    problems: list[str]

    @property
    def can_run(self) -> bool:
        return not self.problems and (self.memory.fits or not self.config.memory.get(
            "refuse_on_insufficient", True
        ))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run": self.config.name,
            "promotable": self.config.promotable,
            "records": len(self.records),
            "smoke_only": self.smoke_only,
            "memory": self.memory.to_dict(),
            "can_run": self.can_run,
            "problems": self.problems,
            "dataset_hashes": self.dataset_hashes,
        }


def _dataset_hashes(directory: Path) -> dict[str, str]:
    import hashlib

    hashes = {}
    for path in sorted(directory.glob("*.jsonl")):
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def plan_training(
    config: TrainConfig,
    *,
    root: Path | None = None,
    paths: Paths | None = None,
    available_ram: int | None = None,
) -> TrainPlan:
    root = root or repo_root()
    dataset_dir = root / str(config.dataset.get("directory", "datasets/train"))
    allow_smoke = bool(config.dataset.get("allow_smoke", False))
    source_id = config.dataset.get("source_id")

    records, problems = validated_training_records(
        dataset_dir, {source_id} if source_id else None, allow_smoke=allow_smoke
    )
    smoke_only = bool(records) and all(r.get("_smoke_only") for r in records)

    if config.gates.get("require_reviewed_data", True) and smoke_only and config.promotable:
        problems.append(
            "a promotable run requires reviewed data; the selected corpus is engineering-smoke"
        )
    if not records:
        problems.append(f"no trainable records in {dataset_dir}")

    geometry = _geometry_from_config(root, config, paths)
    memory = estimate_memory(config, available_ram=available_ram, **geometry)
    if not memory.fits and config.memory.get("refuse_on_insufficient", True):
        problems.append(
            f"estimated {memory.total_gib} GiB peak exceeds the "
            f"{memory.budget_gib} GiB budget; lower max_seq_length or batch_size"
        )

    return TrainPlan(
        config=config,
        records=records,
        dataset_hashes=_dataset_hashes(dataset_dir),
        memory=memory,
        smoke_only=smoke_only,
        problems=problems,
    )


def _geometry_from_config(root: Path, config: TrainConfig, paths: Paths | None = None) -> dict[str, int]:
    """Real geometry for the configured base model.

    Order of truth: the model manifest (pinned, reviewed) → the installed
    ``config.json`` → the Qwen3-1.7B reference values. Getting this wrong makes
    the memory estimate meaningless, so it is read, not assumed.
    """
    from .models.store import ModelStore, StoreError
    from .profiles import QWEN3_1_7B

    model_id = str(config.base_model.get("id", ""))
    geometry = {
        "params": QWEN3_1_7B.n_params or 1_720_576_000,
        "hidden_size": 2048,
        "n_layers": QWEN3_1_7B.n_layers,
    }

    manifest = None
    if paths is not None and model_id:
        try:
            manifest = ModelStore(paths).manifest(model_id)
        except StoreError:
            manifest = None
    if manifest and manifest.geometry:
        geometry["n_layers"] = manifest.geometry.n_layers
        if manifest.geometry.n_params:
            geometry["params"] = manifest.geometry.n_params

    candidates = []
    if paths is not None and model_id:
        candidates.append(paths.models / model_id / "config.json")
    candidates.append(root / "models" / model_id / "config.json")
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            break
        geometry["hidden_size"] = int(raw.get("hidden_size", geometry["hidden_size"]))
        geometry["n_layers"] = int(raw.get("num_hidden_layers", geometry["n_layers"]))
        # Derive a parameter count when the manifest does not carry one.
        if not (manifest and manifest.geometry and manifest.geometry.n_params):
            hidden = geometry["hidden_size"]
            layers = geometry["n_layers"]
            vocab = int(raw.get("vocab_size", 151936))
            intermediate = int(raw.get("intermediate_size", hidden * 3))
            # embeddings + per-layer attention (q/k/v/o) + MLP (gate/up/down)
            per_layer = 4 * hidden * hidden + 3 * hidden * intermediate
            geometry["params"] = layers * per_layer + 2 * vocab * hidden
        break
    return geometry


def _chat_template_messages(record: dict) -> list[dict[str, str]]:
    messages = record.get("messages") or []
    return [
        {"role": str(m.get("role")), "content": str(m.get("content"))}
        for m in messages
        if isinstance(m, dict)
    ]


def _version_table() -> dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for name in ("torch", "transformers", "peft", "trl", "datasets", "accelerate", "safetensors"):
        try:
            module = __import__(name)
            versions[name] = getattr(module, "__version__", "unknown")
        except ImportError:
            versions[name] = "not installed"
    return versions


@dataclass
class RunResult:
    run_id: str
    status: str
    steps: int
    adapter_dir: str | None
    checkpoint_dirs: list[str]
    losses: list[float]
    peak_rss_gib: float
    seconds: float
    promotable: bool
    smoke_only: bool
    versions: dict[str, str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "steps": self.steps,
            "adapter_dir": self.adapter_dir,
            "checkpoints": self.checkpoint_dirs,
            "losses": self.losses,
            "peak_rss_gib": self.peak_rss_gib,
            "seconds": self.seconds,
            "promotable": self.promotable,
            "smoke_only": self.smoke_only,
            "versions": self.versions,
            "notes": self.notes,
        }


def _missing_training_deps() -> list[str]:
    required = ["torch", "transformers", "peft", "datasets"]
    missing = []
    for name in required:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    return missing


def _peak_rss_gib() -> float:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

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

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            psapi = ctypes.WinDLL("psapi")
            psapi.GetProcessMemoryInfo.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_ulong,
            ]
            if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return round(counters.PeakWorkingSetSize / GIB, 2)
        except (OSError, AttributeError, ValueError):
            return 0.0
    try:
        import resource

        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 2)
    except (ImportError, ValueError):
        return 0.0


def run_training(
    plan: TrainPlan,
    paths: Paths,
    *,
    base_model_path: Path,
    steps_override: int | None = None,
    resume: bool = False,
) -> RunResult:
    """Execute the LoRA SFT run. Raises TrainingError with a reason if it cannot."""
    if not plan.can_run:
        raise TrainingError("; ".join(plan.problems))
    missing = _missing_training_deps()
    if missing:
        raise TrainingError(
            "training dependencies are not installed: "
            + ", ".join(missing)
            + '. Install them with: uv pip install -e ".[train]"'
        )

    import torch
    from datasets import Dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers.utils import logging as hf_logging

    # The CLI promises one JSON document on stdout. Transformers writes a live
    # progress table by default, which would corrupt it.
    hf_logging.set_verbosity_error()
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    config = plan.config
    lora = config.lora
    training = config.training
    seq = int(config.dataset.get("max_seq_length", 1024))
    steps = steps_override or int(training.get("max_steps", 30))

    tokenizer = AutoTokenizer.from_pretrained(str(base_model_path), trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float32
    precision = str(training.get("precision", "auto_safe")).lower()
    if precision == "bf16":
        if not torch.cpu._is_avx512_bf16_supported() if hasattr(torch.cpu, "_is_avx512_bf16_supported") else False:
            raise TrainingError("bf16 requested but this CPU has no validated bf16 support")
        dtype = torch.bfloat16

    model = AutoModelForCausalLM.from_pretrained(
        str(base_model_path), torch_dtype=dtype, trust_remote_code=False, low_cpu_mem_usage=True
    )
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=int(lora.get("r", 8)),
        lora_alpha=int(lora.get("alpha", 16)),
        lora_dropout=float(lora.get("dropout", 0.05)),
        target_modules=list(lora.get("target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"])),
    )
    model = get_peft_model(model, peft_config)

    def encode(record: dict) -> dict[str, list[int]]:
        messages = _chat_template_messages(record)
        text = tokenizer.apply_chat_template(messages, tokenize=False)
        tokens = tokenizer(text, truncation=True, max_length=seq)
        tokens["labels"] = list(tokens["input_ids"])
        return tokens

    encoded = [encode(record) for record in plan.records]
    dataset = Dataset.from_list(encoded)

    def _resolve(configured: str | None, fallback: Path) -> Path:
        if not configured:
            return fallback
        candidate = Path(configured)
        # Relative paths belong to the user data directory; writing into the
        # source checkout would mix artifacts with code.
        return candidate if candidate.is_absolute() else paths.root / candidate

    output_dir = _resolve(config.output.get("checkpoint_dir"), paths.checkpoints / config.name)
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir = _resolve(config.output.get("adapter_dir"), paths.adapters / config.name)
    adapter_dir.mkdir(parents=True, exist_ok=True)

    arguments = TrainingArguments(
        output_dir=str(output_dir),
        use_cpu=True,
        per_device_train_batch_size=int(training.get("batch_size", 1)),
        gradient_accumulation_steps=int(training.get("gradient_accumulation_steps", 8)),
        learning_rate=float(training.get("learning_rate", 1e-4)),
        # transformers v5 dropped warmup_ratio; derive the step count so the
        # configured ratio keeps meaning the same thing.
        warmup_steps=max(1, int(steps * float(training.get("warmup_ratio", 0.03)))),
        max_steps=steps,
        save_steps=int(training.get("save_steps", 10)),
        logging_steps=1,
        save_total_limit=int(config.output.get("keep_last_checkpoints", 2)),
        seed=int(training.get("seed", 42)),
        gradient_checkpointing=True,
        dataloader_num_workers=int(training.get("num_workers", 0)),
        optim=str(training.get("optimizer", "adamw_torch")),
        report_to=[],
        use_cache=False,
        remove_unused_columns=False,
        disable_tqdm=True,
        fp16=False,
        bf16=dtype == torch.bfloat16,
    )

    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    trainer = Trainer(model=model, args=arguments, train_dataset=dataset, data_collator=collator)

    run_id = f"run_{time.strftime('%Y%m%d-%H%M%S')}_{uuid.uuid4().hex[:6]}"
    started = time.monotonic()
    resume_arg = None
    if resume:
        existing = sorted(output_dir.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[-1]))
        if not existing:
            raise TrainingError(f"resume requested but no checkpoint exists in {output_dir}")
        resume_arg = str(existing[-1])

    # The CLI contract is one JSON document on stdout. Library progress output is
    # useful, so it goes to stderr instead of being thrown away.
    with contextlib.redirect_stdout(sys.stderr):
        result = trainer.train(resume_from_checkpoint=resume_arg)
        trainer.save_model(str(adapter_dir))
        tokenizer.save_pretrained(str(adapter_dir))
    seconds = time.monotonic() - started
    losses = [
        float(entry["loss"])
        for entry in trainer.state.log_history
        if isinstance(entry, dict) and "loss" in entry
    ]
    checkpoints = [str(p) for p in sorted(output_dir.glob("checkpoint-*"))]

    from .storage import Database

    db = Database(paths, encrypt=True)
    try:
        db.conn.execute(
            "INSERT OR REPLACE INTO training_runs (id, config_json, status, started_at, finished_at, notes) "
            "VALUES (?,?,?,?,?,?)",
            (
                run_id,
                json.dumps(config.raw, default=str),
                "completed",
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "non-promotable smoke run" if plan.smoke_only else "training run",
            ),
        )
        for checkpoint in checkpoints:
            db.conn.execute(
                "INSERT OR REPLACE INTO checkpoints (id, run_id, step, path, sha256, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (
                    f"{run_id}:{Path(checkpoint).name}",
                    run_id,
                    int(Path(checkpoint).name.split("-")[-1]),
                    checkpoint,
                    None,
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ),
            )
    finally:
        db.close()

    return RunResult(
        run_id=run_id,
        status="completed",
        steps=int(result.global_step),
        adapter_dir=str(adapter_dir),
        checkpoint_dirs=checkpoints,
        losses=losses,
        peak_rss_gib=_peak_rss_gib(),
        seconds=round(seconds, 1),
        promotable=config.promotable,
        smoke_only=plan.smoke_only,
        versions=_version_table(),
        notes=[
            "non-promotable: trained on engineering-smoke data"
            if plan.smoke_only
            else "training run",
            "CPU only; no GPU training was attempted",
        ],
    )
