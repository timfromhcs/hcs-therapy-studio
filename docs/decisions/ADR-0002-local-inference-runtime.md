# ADR-0002 — Local inference runtime

- **Status:** accepted
- **Date:** 2026-11-04

## Context

The target machine is a Ryzen 7 7735HS with a Radeon 680M iGPU (RDNA 2, 12 CU,
shared memory), Windows 11, ~20 GiB RAM. We need text inference with GPU
acceleration where it is real, and a CPU path that is not a crash fallback.

## Options

| Option | Verdict |
|---|---|
| `llama.cpp` / `llama-server`, Vulkan build + CPU fallback | **chosen** |
| ONNX Runtime DirectML | Windows-specific, weaker ecosystem for quantised LLMs, extra conversion step |
| PyTorch + Vulkan | experimental; a 2026 issue reports Vulkan autograd/`nn.Linear` training limits, and inference tooling is immature |
| ROCm | the Windows compatibility matrix does not list Radeon 680M |
| WebLLM only | browser-bound; cannot run the desktop product |
| CUDA-based stacks | no NVIDIA hardware |

## Evidence

- Measured on this machine: `vulkan-1.dll` loads, `vkCreateInstance` succeeds and
  one physical device is enumerated — `AMD Radeon(TM) Graphics`,
  `integrated-gpu`, Vulkan 1.4.315, 9.35 GiB device-local heap.
- That heap is *shared* system RAM. A naive `heap * 0.75` budget over-commits the
  machine, which is why `profiles.vram_budget()` returns
  `min(heap_share, ram_budget)` for integrated devices.
- `llama.cpp` ships a documented Vulkan build path and OpenAI-compatible
  `/v1/chat/completions`, so the UI and SDK do not need a bespoke protocol.
- The loader returns a non-zero `VkResult` from `vkGetPhysicalDeviceProperties`
  while writing a valid struct. The probe therefore validates struct content and
  records the anomaly instead of trusting the code. This is documented in
  `hardware._describe_vulkan_device`.

## Decision

Supervise an official `llama-server` binary as a sidecar process. Never link it.
Selected profile comes from measured free RAM and the device geometry, and every
decision is reported with its numbers.

## Consequences

- Quantisation format is GGUF. Model manifests pin SHA-256 and geometry.
- The CPU backend is a first-class profile (`SAFE_CPU`), selected whenever
  Vulkan is unavailable or the budget does not fit.
- We must pin and hash the binary we ship; the licence entry for the runtime is
  currently `approved: false` until a specific build is pinned.
- No inference claim may be made until `runtime smoke` passes on the target.

## Rollback

The runtime sits behind `hcs_therapy/runtime/llama_server.py` and the OpenAI
compatible API. Swapping engines means implementing the same two calls:
`/health` and `/v1/chat/completions`.
