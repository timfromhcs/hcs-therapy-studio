# M4 — first-token latency on the streaming path

Measured 2026-11-04 on the development machine. Command:

```powershell
.\.venv\Scripts\hcs-therapy.exe runtime bench --backend vulkan --n 5 --max-tokens 48 --json
```

Runtime: `llama.cpp` b12102 · Model: `qwen3-1.7b-gguf-q8-0` (sha256 `061b54da…cb1a`) ·
Profile: `VULKAN_BALANCED`

## Result

| Metric | Value |
|---|---|
| Load | 6.32 s |
| First token of any kind, p50 | **0.199 s** |
| First token of any kind, p95 | 0.669 s |
| Mean throughput | 28.17 tok/s |
| Failed requests | 0 / 5 |

Per-request first-activity times: 0.201, 0.168, 0.786, 0.199, 0.172 s. The 0.786 s outlier is
the third request; the cache is warm but the scheduler is not perfectly steady on an
integrated GPU that shares memory bandwidth with the CPU.

## The number that mattered

`Qwen3` emits a private reasoning stream before its visible answer. Measured end-to-end in
the browser against the production bundle with the reasoning phase **left on**:

| | First visible character |
|---|---|
| reasoning phase on (default template) | **13.31 s** |
| reasoning phase off (`enable_thinking: false`) | **0.12 s** |

13.3 seconds of silence is not a slow interface, it is an unusable one, and the scratchpad
is not a reply. The studio therefore sets
`chat_template_kwargs = {"enable_thinking": false}` on the conversational path
(`ServerConfig.thinking`, default `False`, overridable).

Measured after the change, in Chromium at 1440 × 900: first visible character **0.12 s**,
**33.1 tok/s**, both shown in the message footer.

## What this does *not* establish

- No quality claim. Speed is not quality, and the German register problem (`du`/`Sie` mixed
  inside one answer) is unaffected by any of this.
- Only one model, one quantisation, one device, one machine.
- The reasoning phase is off by default for conversation; it is still available for callers
  that want it, and turning it on costs the latency shown above.

## Reproduce

```powershell
.\.venv\Scripts\hcs-therapy.exe runtime bench --backend cpu    --n 5 --max-tokens 48 --json
.\.venv\Scripts\hcs-therapy.exe runtime bench --backend vulkan --n 5 --max-tokens 48 --json
```
