# Documentation index

Start here if you are new to the project.

| Document | Read it when |
|---|---|
| [`../README.md`](../README.md) | you want to know what this is and whether it runs on your machine |
| [`../status.md`](../status.md) | you want to know what was actually executed, with commands |
| [`../plan.md`](../plan.md) | you want the milestone board |
| [`../LONG-HORIZON-PLAN.md`](../LONG-HORIZON-PLAN.md) | you want the research and the execution log of the current run |
| [`../CHANGELOG.md`](../CHANGELOG.md) | you want to know what changed and what evidence supports it |
| [`../AGENTS.md`](../AGENTS.md) | you are an agent or contributor and need the build contract |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | you want to send a pull request |
| [`../SECURITY.md`](../SECURITY.md) | you found a vulnerability, or you need the security boundary |

## Architecture

| Document | Contents |
|---|---|
| [`architecture/system-overview.md`](architecture/system-overview.md) | module map and the layering rule |
| [`architecture/local-inference.md`](architecture/local-inference.md) | `llama.cpp` sidecar, budgets, context sizing |
| [`decisions/`](decisions) | nine ADRs: scope, runtime, training backend, VLM, image generation, encryption, browser engine, packaging, licence |

## Safety and privacy

| Document | Contents |
|---|---|
| [`safety/intended-purpose.md`](safety/intended-purpose.md) | what the product is for and what it refuses to do |
| [`privacy/data-flow.md`](privacy/data-flow.md) | what is stored, where, encrypted with what, and how it is deleted |
| [`a11y-audit.md`](a11y-audit.md) | contrast and structure audit, with its own limitations |

## Measurements

| Document | Contents |
|---|---|
| [`benchmarks/m1-runtime-gate.md`](benchmarks/m1-runtime-gate.md) | 200 generations across CPU and Vulkan, latency, memory |
| [`benchmarks/m4-first-token-latency.md`](benchmarks/m4-first-token-latency.md) | time-to-first-token, and the 13.3 s → 0.12 s reasoning finding |
| [`benchmarks/register-anchoring.md`](benchmarks/register-anchoring.md) | German `du`/`Sie` anchoring, measured A/B with its n=15 caveat |
| [`feature-parity.md`](feature-parity.md) | desktop vs. browser capability matrix (browser edition not built) |
| [`installation/llama-server.md`](installation/llama-server.md) | installing and verifying the inference runtime |

## Screenshots

[`screenshots/`](screenshots) — captured in Chromium against the production bundle at
1440 × 900 and 390 × 844, with the real API and the real model. They are evidence, not
mockups.

## Verification scripts

| Script | What it proves |
|---|---|
| `scripts/verify/wheel_install.ps1` | the wheel builds, passes `twine check`, installs into a clean venv and every entry point runs |
| `scripts/bench/register_anchoring.py` | German address-register compliance, anchored vs unanchored, n configurable |
| `scripts/bench/summarise_register_ab.py` | the same run, reduced to the mismatches so the failure mode is visible |
| `scripts/ops/reminder.ps1` | a detached checkpoint reminder with a hard deadline (not an autostart entry) |
