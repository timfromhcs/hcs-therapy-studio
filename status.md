# status.md — verified state

Last updated: 2026-11-04. This file records what was **executed**, not what was
intended. If a claim here has no command, it is wrong.

## Environment (measured, not assumed)

| Item | Value | How |
|---|---|---|
| OS | Windows 11 Pro 10.0.26200 (build 26200) | `Get-CimInstance Win32_OperatingSystem` |
| CPU | AMD Ryzen 7 7735HS, 8 cores / 16 threads, SIMD sse2/avx/avx2 | `hcs-therapy doctor --json` |
| RAM | 19.79 GiB total; 4.28–4.66 GiB free during the session | same |
| GPU | AMD Radeon(TM) Graphics (integrated, driver 32.0.21043.12001) | Win32_VideoController |
| Vulkan | loader `vulkan-1.dll` present; 1 device: AMD Radeon(TM) Graphics, integrated-gpu, Vulkan 1.4.315, 9.35 GiB device-local heap (shared) | `hardware.probe_vulkan()` |
| Python | 3.14.6 | `python --version` |
| Node | 22.23.1 | `node --version` |
| Rust / cargo | present | `Get-Command cargo` |
| Disk free | C: 90 GB, D: 95 GB, E: 137 GB | `Get-PSDrive` |
| Project venv | `.venv` (Python 3.14.6) | `uv venv` |

## Test suite

```
$ .\.venv\Scripts\python.exe -m pytest
212 passed in 19.44s

$ .\.venv\Scripts\python.exe -m ruff check .
All checks passed!
```

Coverage by area (all executed, no skips):

| File | Tests | What it proves |
|---|---|---|
| `test_crisis.py` | 30 | crisis gate fires, negation/third-party/quoted/injection handled |
| `test_policy.py` | 25 | turn policy, verified resources, output guard |
| `test_hardware_profiles.py` | 14 | detection, budget math, iGPU sharing, partial offload |
| `test_manifests_downloads.py` | 26 | manifest rules, resumable download, checksum atomicity |
| `test_storage.py` | 13 | encryption at rest, migrations, export, delete |
| `test_api.py` | 19 | auth, CORS, confirmation gate, crisis bypass |
| `test_agent_mcp.py` | 24 | schema validation, policy gate, budgets, MCP protocol |
| `test_datasets.py` | 18 | provenance, PII, dedup, review gating, leakage |
| `test_evals.py` | 15 | scoring, report schema, regression compare |
| `test_svg.py` | 17 | sanitisation, escaping, scene validation |
| `test_cli.py` | 21 | exit codes and JSON contracts of every command |

## Milestone board

| Milestone | State | Evidence |
|---|---|---|
| M0 Repository/research freeze | **done** | this file, `licenses/manifest.yaml`, `docs/decisions/*` |
| M1 Native LLM runtime | **implemented, gate pending** | `hcs_therapy/runtime/*`; `runtime smoke` not yet run (no binary/model installed) |
| M2 Evaluation harness | **partial** | `hcs_therapy/evals.py`, `eval run --provider echo` executed |
| M3 Dataset pipeline | **done (gating)** | `hcs-therapy data validate` → ok, 10 smoke rows, 0 trainable |
| M4 CPU LoRA training | **scaffolded** | config + gates; **no training run executed** |
| M5 Safety layers | **done (deterministic parts)** | crisis/policy tests |
| M6 Agent + MCP | **done** | MCP stdio roundtrip test |
| M7 VLM + graphics | **partial** | SVG sanitiser + renderer done; no VLM runtime proven |
| M8 Product UI | **not started** | — |
| M9 Browser edition | **not started** | — |
| M10 Packages/EXE | **not started** | — |
| M11 Publication | **blocked** | needs explicit owner authorisation |

## Commands that were actually run

```powershell
hcs-therapy doctor                        # profile: VULKAN_BALANCED, ctx 2048, -1 GPU layers
hcs-therapy doctor --json                 # reasons + warnings, redacted
hcs-therapy models list                   # 1 manifest, approved, 1.71 GiB, not installed
hcs-therapy models install ...            # refused without --accept-license (by design)
hcs-therapy data validate --json          # ok: 1 manifest, 10 smoke rows, 0 trainable
hcs-therapy data scan datasets/train/seed-smoke.jsonl --json   # ok, 0 PII hits
hcs-therapy data leakage --json           # no leaks
hcs-therapy license verify --json         # 0 problems, 7 approved, 5 unapproved
hcs-therapy license generate --json       # wrote NOTICE, THIRD_PARTY_NOTICES.md, MODEL_ATTRIBUTION.md, DATASET_ATTRIBUTION.md, SBOM.spdx.json
hcs-therapy safety assess "Ich bringe mich um" --region DE   # ELEVATED + verified numbers
hcs-therapy safety scan "You have depression."               # blocked: diagnosis_claim
hcs-therapy svg sanitize broken.svg       # script removed
hcs-therapy agent tools                   # 6 read-only tools, no shell
hcs-therapy eval run --suite hcs-core --provider echo
```

## Explicitly NOT done

- No model was downloaded or run. `runtime smoke` has **never** executed on this
  machine; therefore no tokens/second, no Vulkan inference claim, no load time.
- No `llama-server` binary is bundled or pinned yet.
- No PyTorch training run. M4 is scaffolded only.
- No external benchmark executed (MentalHealthBench/CBT-Bench/HealthBench/BFCL).
- No German native-speaker review of prompts, templates or outputs.
- No UI exists. No installer, wheel publication, npm package or Vercel deployment.
- No GitHub repository created or pushed.

## Upstream licence work actually performed

Queried the Hugging Face API on 2026-11-04 and fetched each repository's `LICENSE`
file to confirm the Apache-2.0 text, then pinned commit SHAs:

| Asset | Revision | Licence | Gated |
|---|---|---|---|
| Qwen3-1.7B-Base | `ea980cb0…04c1` | Apache-2.0 | no |
| Qwen3-1.7B | `70d244cc…ad5e` | Apache-2.0 | no |
| Qwen3-1.7B-GGUF | `90862c4b…6077` | Apache-2.0 | no (Q8_0 only, 1,834,426,016 B) |
| SmolLM3-3B | `a07cc9a0…0ac1` | Apache-2.0 | no |
| Granite 3.3 2B Instruct | `707f574c…e0f0` | Apache-2.0 | no |
| Qwen3-VL-2B-Instruct | `89644892…4203` | Apache-2.0 | no |
| SmolVLM2-2.2B-Instruct | `482adb53…72e4` | Apache-2.0 | no |

Rejected with reasons: PixArt-Sigma (OpenRAIL++-M), CBT-Bench and ESConv
(CC BY-NC), Sana (Gemma-2 encoder terms), Janus (DeepSeek Model Licence).

## Next actions before any capability claim

1. Pin and vendor a `llama-server` Vulkan build; record its SHA-256.
2. `models install qwen3-1.7b-gguf-q8-0 --accept-license`; verify the hash.
3. `runtime smoke --backend cpu` and `--backend vulkan`; record load time,
   first-token latency, tokens/s and peak RSS.
4. 100-generation stress loop; count failures.
5. Only then may the README mention working local inference.
