# ADR-0003 — Training backend on consumer hardware

- **Status:** accepted (not yet executed)
- **Date:** 2026-11-04

## Context

We want to adapt `Qwen/Qwen3-1.7B-Base` with LoRA on a laptop with 8 cores, an
integrated GPU and ~20 GiB RAM, without a CUDA device.

## Options

| Option | Verdict |
|---|---|
| PyTorch CPU + Transformers + PEFT/TRL, `use_cpu=True` | **chosen** (scaffolded) |
| PyTorch + Vulkan | Vulkan autograd is not a supported training path; a 2026 issue reports `nn.Linear` training failures |
| DirectML | Windows-only, patchy op coverage, optimistic memory reporting |
| ROCm on 680M | Not on the supported matrix |
| QLoRA with bitsandbytes | CUDA-oriented; CPU support unvalidated here |
| Full fine-tuning | Out of scope: 1.7B params in FP32 ≈ 6.9 GB weights plus optimiser state |

## Evidence

- Transformers documents CPU as a first-class training backend and
  `TrainingArguments(use_cpu=True)`.
- `llama.cpp` Vulkan gives us *inference*; that is not evidence for autograd.
- Estimator in `hcs_therapy/train.py` computes weights + gradients + optimiser +
  activations. For 1.7B LoRA at r=8, batch 1, 1024 tokens, the realistic floor is
  ~8–9 GiB, which fits but leaves no room for a browser with 40 tabs.

## Decision

- Training is an **optional extra** (`pip install .[train]`); the runtime never
  imports torch.
- Default config: LoRA r=8/alpha=16, batch 1, grad-accum 8, seq 1024, FP32 unless
  a correctness check allows BF16, gradient checkpointing on, `num_workers=0`.
- The trainer refuses to start if the memory estimate exceeds the measured safe
  budget, and says which knob to change.
- Every run records dataset hash, config, seed, package versions and peak RSS.
- A run trained on `engineering-smoke` rows is marked non-promotable.

## Consequences

- Step time will be slow; the first milestone is a 10–30 step smoke run, not a
  quality result.
- Promotion requires an A/B evaluation without a safety regression, which needs
  the local suite plus human review.

## Rollback

The trainer is a separate module behind a CLI subcommand. If CPU training proves
impractical, the product keeps inference, evaluation and dataset gating, and the
capability is documented as desktop/CLI-only with an external machine.
