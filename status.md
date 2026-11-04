# status.md — verified state

Last updated: 2026-11-04. This file records what was **executed**, not what was
intended. If a claim here has no command, it is wrong.

## Environment (measured)

| Item | Value | How |
|---|---|---|
| OS | Windows 11 Pro 10.0.26200 | `Win32_OperatingSystem` |
| CPU | AMD Ryzen 7 7735HS, 8C/16T, sse2/avx/avx2 | `hcs-therapy doctor --json` |
| RAM | 19.79 GiB total; 6.3–8.4 GiB free during the session | same |
| GPU | AMD Radeon(TM) Graphics, integrated, driver 32.0.21043.12001 | Win32_VideoController |
| Vulkan | 1 device: AMD Radeon(TM) Graphics, integrated-gpu, Vulkan 1.4.315, 9.35 GiB shared device-local heap | `probe_vulkan()` |
| Python (app) | 3.14.6 in `.venv`; training extras: torch 2.15.0+cpu, transformers 5.22.1, peft 0.21.2, trl 1.17.1, datasets 5.1.0 | `train smoke --json → versions` |
| Node | 22.23.1; Vite 8; React 19 | `npm run build` |

## Test suite

```
$ .\.venv\Scripts\python.exe -m pytest
225 passed in 17.92s

$ .\.venv\Scripts\python.exe -m ruff check .
All checks passed!

$ npm run build   (apps/web)
tsc -b && vite build → built, 444 kB js / 141 kB css
```

| File | Tests | Proves |
|---|---|---|
| `test_crisis.py` | 30 | crisis gate: intent, imminence, negation, third party, quoted, injection, EN + DE |
| `test_policy.py` | 25 | turn policy, verified resources, output guard |
| `test_hardware_profiles.py` | 14 | detection, budget math, iGPU sharing, partial offload |
| `test_manifests_downloads.py` | 26 | manifest rules, resumable download, checksum atomicity |
| `test_storage.py` | 13 | encryption at rest, migrations, export, delete |
| `test_api.py` | 21 | auth, CORS incl. loopback ports, confirmation gate, crisis bypass, wipe |
| `test_agent_mcp.py` | 24 | schema validation, policy gate, budgets, MCP protocol |
| `test_datasets.py` | 18 | provenance, PII, dedup, review gating, leakage |
| `test_evals.py` | 15 | scoring, report schema, regression compare |
| `test_svg.py` | 17 | sanitisation, escaping, scene validation |
| `test_cli.py` | 21 | exit codes and JSON contracts of every command |
| `test_train.py` | 11 | memory estimate, geometry resolution, data gating, plan serialisation |

## Milestones

| Milestone | State | Evidence |
|---|---|---|
| M0 Repository/research freeze | **done** | licence register with verified SHAs, 9 ADRs, safety/privacy docs |
| M1 Native LLM runtime | **runtime done, inference gate NOT met** | sidecar supervision + API + model store implemented and tested; no `llama-server` binary pinned, no GGUF run |
| M2 Evaluation harness | **partial** | local suite + A/B compare; `eval run --provider echo` executed; no external benchmark |
| M3 Dataset pipeline | **done (gating)** | `data validate` → ok, 10 smoke rows, 0 trainable, 0 leaks, 0 PII |
| M4 CPU LoRA training | **pipeline proven, not a quality result** | 10-step and 13-step runs executed; resume from checkpoint-10 verified |
| M5 Safety layers | **done (deterministic)** | crisis/policy tests + browser-verified crisis path |
| M6 Agent + MCP | **done** | MCP stdio roundtrip test; 6 read-only tools, no shell |
| M7 VLM + graphics | **graphics partial** | SVG sanitiser + scene renderer + Studio screen; VLM runtime unproven |
| M8 Product UI | **done for the static client** | 8 screens, browser-verified at 375px and 1440px |
| M9 Browser edition | **not started** | no WebLLM/WebGPU |
| M10 Packages/EXE | **not started** | no wheel published, no installer, no npm package |
| M11 Publication | **blocked** | needs explicit owner authorisation |

## M4 — what the training run actually showed

```
$ hcs-therapy train plan --config configs/train/cpu-lora-smoke-0_6b.yaml --json
records 10 · smoke_only true · params 596,049,920
weights 2.22 GiB · LoRA 0.01 · activations 0.0 · overhead 0.60
total 2.85 GiB vs budget 3.05 GiB → can_run true

$ hcs-therapy train smoke --config ... --json
run_20261104-100359_2833e1 · 10 steps · 86.8 s · ~8 s/step
loss 4.61 → 3.74 · grad_norm 2.35 → 1.73
checkpoint-5, checkpoint-10 · adapter saved

$ hcs-therapy train smoke --config ... --steps 13 --resume --json
run_20261104-101409 · resumed from checkpoint-10 → 13 steps · 28.5 s
peak_rss_gib 3.04 · losses 13 · exit 0
```

Honest reading of this:

- The **pipeline** works: gated data → tokenisation → LoRA attachment → steps →
  loss → checkpoint → adapter → resume.
- It is **not** evidence of model quality. The corpus is 10 `engineering-smoke`
  rows, the run is marked `promotable: false`, and no evaluation was run on the
  adapter.
- The memory estimator under-predicted (2.25 GiB estimated vs 3.04 GiB measured).
  Cause: unmodelled process overhead. Fixed by adding a calibrated 0.6 GiB
  `PROCESS_OVERHEAD_BYTES` term, so the guard now refuses instead of over-committing.
- The 1.7B config was **refused** by the guard on this machine (6.5 GiB needed vs
  1.3–1.8 GiB budget with a browser and the user's own `llama-server` running).
  That is the guard doing its job, not a workaround.

## M8 — UI verification

Rendered in Chromium via Playwright against the production bundle
(`vite preview`, port 4173) talking to the real API on 127.0.0.1:8765.

- `#home` → live profile: `VULKAN_BALANCED`, 16,384 tokens, 3.31 GiB budget,
  7.91 GiB free, with the integrated-GPU caveat rendered verbatim.
- `#chat` → sent a German imminent-risk message. Result: deterministic response,
  model bypassed (`Sicherheitsantwort ohne Modell` badge), region-filtered
  resource panel, no invented numbers.
- `#studio`, `#journal`, `#lab`, `#safety`, `#settings` → load and render.
- 390×844: `document.scrollWidth === clientWidth` (375 = 375) after fixing a
  badge that forced horizontal overflow.
- Screenshots: `docs/screenshots/ui-{home,chat-crisis,studio}-desktop.png`,
  `ui-{chat-crisis,journal}-mobile.png`.

Bugs found **by** the browser check and fixed:

1. CORS allow-list was an exact port match, so any Vite port (4173/5173/…) was
   rejected and every request failed. Now loopback origins on any port are
   accepted; remote origins are still rejected (`origin_allowed()` + tests).
2. `ConnectionResetError` tracebacks on every client abort spammed the console.
   `StudioHTTPServer.handle_error` now treats a client hang-up as normal.
3. Crisis card showed all four regions at once; now the user's region only.
4. Crisis template emitted markdown (`**…**`, `- …`) that rendered as literal
   asterisks; `resources.render()` is now plain text.

**Not run:** `review-ui-code`, `get-review-rules`, `check-comprehension`,
`inspect-spacing`, `finalize-dashboard-review`. The Better Design account returned
`AGENT_QUOTA_EXHAUSTED` (25 free queries used). The UI review is therefore
source-level plus rendered-browser evidence, **not** the tool receipt.

## Explicitly NOT done

- No `llama-server` binary pinned or bundled; **no local LLM inference has ever
  run from this app**. No tokens/second, no Vulkan-vs-CPU comparison.
- No GGUF model downloaded (only safetensors for training).
- No external benchmark (MentalHealthBench, CBT-Bench, HealthBench, BFCL, MCPMark).
- No German native-speaker review of prompts, templates or UI copy.
- No Tauri shell, no installer, no wheel publication, no npm package, no Vercel
  deployment, no GitHub repository created or pushed.
- No VLM runtime; no image generation by design (ADR-005).

## Next actions before any capability claim

1. Pin a `llama-server` Vulkan build, record its SHA-256, add the licence entry.
2. `models install qwen3-1.7b-gguf-q8-0 --accept-license`, `models verify`.
3. `runtime smoke --backend cpu` then `--backend vulkan`; record load time,
   first-token latency, tokens/s, peak RSS.
4. 100-generation loop; count failures.
5. Then, and only then, may the README claim working local inference.
