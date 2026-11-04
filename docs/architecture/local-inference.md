# Local inference profile

## Why the profile is computed, not configured

A fixed "use all GPU layers, 8K context" default is how local tools OOM a laptop.
This project measures, then decides, then explains.

`hcs_therapy.profiles.assess()` computes:

```
ram_budget  = available_ram * 0.62 - 1.6 GiB          # reserve for OS + UI
heap_budget = device_local_heap * 0.75
budget      = min(heap_budget, ram_budget)            # iGPU: shared memory!
kv_per_tok  = 2 * layers * kv_heads * head_dim * bytes
need(ctx)   = model_bytes + kv_per_tok * ctx
```

Qwen3-1.7B geometry (verified against upstream `config.json`):
28 layers, 8 KV heads, head_dim 128 → **114,688 bytes/token** at f16 KV.
That is 224 MiB at 2048 tokens and 1.75 GiB at 16384 — the reason context is not
free.

Policies:

| Condition | Profile | gpu layers |
|---|---|---|
| no usable Vulkan | `SAFE_CPU` | 0 |
| `need(ctx)` ≤ budget | `VULKAN_BALANCED` | -1 (all) |
| `0.7*model + KV(2048)` ≤ budget | `VULKAN_LOW_MEMORY` | `layers // 2` |
| otherwise | `SAFE_CPU` | 0 |

## Observed on the development machine

A real `hcs-therapy doctor --json` output:

```json
{
  "profile": "VULKAN_BALANCED",
  "backend": "vulkan",
  "n_gpu_layers": -1,
  "context": 2048,
  "estimated_runtime_gib": 1.27,
  "budget_gib": 1.29,
  "reasons": [
    "available RAM 4.66 GiB of 19.79 GiB; CPU commit budget 1.29 GiB (62% minus 1.6 GiB reserve)",
    "Vulkan device 'AMD Radeon(TM) Graphics' (integrated-gpu, Vulkan 1.4.315) with 9.35 GiB device-local memory; offload budget 1.29 GiB",
    "integrated GPU: device memory is shared with system RAM, so the budget is the lower of the GPU heap share and the safe RAM commit",
    "full offload fits: 1.27 GiB needed at 2048 tokens within a 1.29 GiB budget"
  ]
}
```

Note the context: 2048, not 16384. The 9.35 GiB heap is shared; only 4.66 GiB was
actually free while a browser and IDE were running. An earlier version of this
code returned `VULKAN_BALANCED, ctx 16384` because it treated the heap as
dedicated VRAM — that bug was found by `test_integrated_gpu_budget_is_limited_by_system_ram`
and fixed.

## Sidecar lifecycle

```
find_server_binary() → free_port() → Popen(new process group)
  → poll /health until 200 (timeout 180 s) → ready
  → on error: read log tail, stop(), raise with the path to the log
stop(): terminate → wait 15 s → taskkill /T /F on Windows → close log
```

Guarantees:

- The process group is ours; we never kill unrelated processes.
- `--host 127.0.0.1` and `--api-key` are always set, so another local process
  cannot quietly use our model server.
- Logs go to `<data>/logs/llama-server-<port>.log`, no content logging by us.

## CPU backend

Selected automatically when Vulkan is missing or the budget does not fit. Threads
default to `cpu_count // 2` because using every thread while the UI is running
makes both slower. Context shrinks before the model does.

## What is *not* claimed

- No tokens/second figure is published: `runtime smoke` has not been executed on
  this device yet (no pinned binary, no model installed).
- No claim that Vulkan is faster than CPU here. That requires the throughput
  comparison from milestone M1.
