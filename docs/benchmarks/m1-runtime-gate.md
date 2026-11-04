# M1 runtime gate — measured results

Date: 2026-11-04. Everything below was executed on the development machine
(Windows 11 26200, Ryzen 7 7735HS, Radeon 680M, 19.79 GiB shared RAM), not
estimated.

## Artifacts under test

| Component | Identity |
|---|---|
| Runtime | `llama.cpp` release `b12102`, commit `bbb02c93e9b83255b70ac1a755bb02b0a251f9a7` |
| Runtime archive | `llama-b12102-bin-win-vulkan-x64.zip`, 37,660,949 bytes, sha256 `b322f7d6ce8b2a31cf16980aa38986a6a27da2e55e406e770f0221621c38de08` |
| Model | `Qwen3-1.7B-Q8_0.gguf`, 1,834,426,016 bytes, sha256 `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`, upstream revision `90862c4b9d2787eaed51d12237eafdfe7c5f6077`, Apache-2.0 |
| Loader | `vulkan-1.dll`, 1 device: AMD Radeon(TM) Graphics, integrated-gpu, Vulkan 1.4.315 |

Both hashes were recomputed on the machine before use: the model through
`hcs-therapy models verify` (deep), the runtime archive by `Get-FileHash` and
again by `scripts/bootstrap/fetch_llama_server.ps1`.

## Single-completion smoke

`hcs-therapy runtime smoke --backend cpu|vulkan --max-tokens 64`

| Backend | Profile | ctx | GPU layers | Load | 64 tokens | tok/s |
|---|---|---|---|---|---|---|
| CPU | `SAFE_CPU` | 4096 | 0 | 3.18 s | 3.82 s | **16.77** |
| Vulkan | `VULKAN_BALANCED` | 4096 | -1 (all) | 6.07 s | 2.67 s | **23.93** |

Vulkan is **1.43× faster** than CPU on this device for the same model, context
and prompt. CPU load was faster (3.18 s vs 6.07 s) because no device buffers are
allocated.

## Stress gate — 100 repeated generations

`python scripts/benchmark/stress_generations.py --count 100 --max-tokens 48`

| Metric | CPU | Vulkan |
|---|---|---|
| Completed | 100/100 | 100/100 |
| Failed | **0** | **0** |
| Wall | 290.0 s | 175.5 s |
| Tokens generated | 4,800 | 4,800 |
| Throughput | 16.55 tok/s | **27.36 tok/s** |
| Latency mean | 2,864.6 ms | 1,729.5 ms |
| Latency p50 | 2,823.0 ms | 1,721.6 ms |
| Latency max | 3,507.2 ms | 2,243.3 ms |
| Server working set | 1.86 GiB | 2.70 GiB |

No crash, no timeout, no empty completion across 200 generations.

## Full-stack path

`hcs-therapy serve --start-backend` → API on `127.0.0.1:8765`, backend on a
random free port with its own generated API key and restricted CORS.

Observed profile at start: `VULKAN_BALANCED`, ctx 8192, all layers offloaded
(~7 GiB free at that moment).

| Request | Result |
|---|---|
| `GET /health` | `{"status":"ok","model_loaded":true}` |
| Normal German message | policy `normal`, `model_bypassed: false`, guard `ok`, answer from the model |
| Imminent-risk German message | policy `crisis_imminent`, `model_bypassed: true`, verified DE numbers, no generation |

A real model answer, unedited (note the register slip — see below):

> „Wie geht es dir jetzt? Es ist wichtig, dass du weißt, dass du es nicht allein
> findest. Haben Sie etwas, das besonders anstrengend war? Oder möchten Sie
> einfach mal einen Moment ruhen? Vielleicht können wir gemeinsam etwas Gutes
> tun, um die Energien zu sammeln."

## Why Qwen3 needs a reasoning-aware reader

Qwen3 emits a separate `reasoning_content` stream. With a 24-token budget, the
entire budget went to reasoning and `message.content` was empty — the first
stress run reported "empty completion" 4 times before aborting. Both the smoke
command and the stress script now read `content || reasoning_content` and report
`has_reasoning_stream`. This is a real product consequence: a short output limit
on a reasoning model produces no visible answer.

## Findings that are not flattering

1. **German register drifts.** The model mixed *du* and *Sie* within one answer.
   The output guard does not catch register, and the local suite's language check
   only measures stopword ratio. This needs prompt-level anchoring plus a
   reviewer, and is exactly the kind of thing `status.md` must not call "done".
2. **Emoji appear.** The sample ends with an emoji. Not a policy violation, but
   inconsistent with the product's tone rules.
3. **No first-token latency yet.** The smoke reports completion throughput, not
   time-to-first-token, because the non-streaming path is what the UI uses today.
   A streaming measurement is outstanding work.
4. **Integrated GPU memory is shared.** ctx 8192 was available with ~7 GiB free;
   earlier with ~4.6 GiB free the profile chose ctx 2048. Same machine, different
   answer — because the answer is measured, not configured.

## What this gate does and does not establish

Established: local inference works on this device on both backends, reproducibly,
without crashes, with verified artifacts, and the app's safety gate still bypasses
the model correctly when the model is loaded.

Not established: answer quality, German naturalness, therapeutic appropriateness,
or that any external benchmark score would be acceptable. None of those were
measured and none may be claimed.
