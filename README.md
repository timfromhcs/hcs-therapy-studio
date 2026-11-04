# HCS Therapy Studio

**A local-first wellbeing, psychoeducation, reflection and AI-research studio.**
Runs on your machine with CPU or Vulkan inference. No cloud inference, no
telemetry, no hidden prompt logging.

> Made with love by hcsmedia and timfromhcs

**Status: pre-release (v0.1.0).** This README distinguishes what is implemented,
what is experimental, and what is not built yet. Read the
[honest limitations](#honest-limitations) before drawing any conclusion about
capability.

---

## What this is (and is not)

It **is** a local application for supportive conversation, psychoeducation,
guided self-reflection, private journaling, a native SVG/layout studio, a model
and training laboratory, an evaluation harness, and a bounded local tool
(MCP) layer.

It is **not** a medical device, a diagnostic tool, a therapist, or a crisis
service. It does not diagnose, does not recommend medication, and does not
replace professional care. See [`docs/safety/intended-purpose.md`](docs/safety/intended-purpose.md).

The shipped model is a general-purpose open-weight model with a scope prompt and
deterministic safety layers around it — not a clinically validated therapeutic
model.

## Quick start

Requirements: Windows 11 (primary target), Python 3.11+, 8 GB RAM minimum,
`llama-server` from [llama.cpp](https://github.com/ggml-org/llama.cpp) for local
inference.

```powershell
uv venv --python 3.14
uv pip install -e .
.\.venv\Scripts\hcs-therapy.exe doctor
```

`doctor` detects the machine, prints the compute profile it selected **and why**,
and reports whether a runtime and a model are available:

```
OS          : Windows 10.0.26200 (AMD64)
CPU         : AMD Ryzen 7 7735HS with Radeon Graphics | 16 cores | SIMD sse2, avx, avx2
RAM         : 4.66 GiB free of 19.79 GiB
GPU         : AMD Radeon(TM) Graphics
Vulkan      : AMD Radeon(TM) Graphics (integrated-gpu, Vulkan 1.4.315, 9.35 GiB device-local)
Profile     : VULKAN_BALANCED | ctx 2048 | -1 GPU layers
```

That output is a real measurement from the development machine, including the
important part: the integrated GPU's 9.35 GiB is *shared* with system RAM, so the
profile is capped by the RAM that is actually free right now instead of promising
VRAM that does not exist.

Install the default text model (1.83 GB, Apache-2.0, SHA-256 pinned):

```powershell
.\.venv\Scripts\hcs-therapy.exe models list
.\.venv\Scripts\hcs-therapy.exe models install qwen3-1.7b-gguf-q8-0 --accept-license
.\.venv\Scripts\hcs-therapy.exe runtime smoke --backend auto --json
```

Start the local API and talk to it:

```powershell
.\.venv\Scripts\hcs-therapy.exe serve --port 8765
```

The server binds `127.0.0.1` only, prints a per-launch bearer token, and rejects
any other browser origin.

## Implemented

| Area | State | Evidence |
|---|---|---|
| Hardware/Vulkan detection through the real loader | implemented | `hcs-therapy doctor --json`, `tests/test_hardware_profiles.py` |
| Compute-profile selection with explicit budgets and reasons | implemented | same |
| Resumable, hash-verified model downloads with atomic promotion | implemented | `tests/test_manifests_downloads.py` |
| `llama-server` supervision (start, health, stop, log capture) | implemented | `hcs_therapy/runtime/llama_server.py` |
| Loopback API with per-launch token, CORS allow-list, size caps, confirmation gate | implemented | `tests/test_api.py` |
| Deterministic crisis detection (EN/DE), negation, third-person, quoted, injection | implemented | `tests/test_crisis.py` |
| Verified regional resource pack with source + review date | implemented | `tests/test_policy.py` |
| Output guard: diagnosis, medication, false certainty, dependence, invented hotlines | implemented | `tests/test_policy.py` |
| Encrypted-at-rest journal/messages (AES-256-GCM), export and delete | implemented | `tests/test_storage.py` |
| Tool registry with JSON-Schema validation + policy gate + budgets + audit | implemented | `tests/test_agent_mcp.py` |
| MCP server over stdio (JSON-RPC 2.0) | implemented | same |
| Dataset gating: provenance, PII, dedup, review status, train/eval leakage | implemented | `tests/test_datasets.py` |
| Evaluation harness with deterministic scorers and A/B regression compare | implemented | `tests/test_evals.py` |
| SVG sanitiser + constrained scene renderer (text-to-layout) | implemented | `tests/test_svg.py` |
| Attribution/SBOM generation from manifests | implemented | `hcs-therapy license generate` |

## Experimental

- **CPU LoRA training** — configuration, dataset gates and smoke-run plumbing
  exist; PyTorch is an optional extra and no training run is claimed here. Full
  fine-tuning is out of scope for this device.
- **Browser/WebGPU edition** — not implemented yet. Static-client design is
  documented; nothing in the browser is validated and no feature-parity claim is
  made.
- **Vision-language** — licences cleared for Qwen3-VL-2B and SmolVLM2, but no
  runtime export has been proven on this hardware. The UI must not present a VLM
  until a real smoke test passes.
- **Generative image models** — deliberately not bundled. The licence chain of
  the candidates fails the project's filter, or the model size does not fit the
  target device. The image capability ships as a deterministic editor and SVG
  renderer instead.

## Not built yet

Windows one-file installer, Python wheel publication, npm packages, Vercel
deployment, public repository. See [`status.md`](status.md) for the milestone
board.

## Safety architecture

A system prompt is not safety. The layers that actually run:

1. **Deterministic crisis gate** before the model is called. On an imminent
   signal the model is *skipped entirely*; the response is a reviewed template
   with verified numbers for the user's region.
2. **Verified resource pack** with source URL and review date per entry, plus an
   explicit "no region pack" fallback that never invents a hotline.
3. **Output guard** that flags diagnostic claims, medication advice, false
   certainty, dependence-fostering language and unrecognised service numbers,
   and replaces the text with a safe fallback.
4. **Tool budget gate** that requires approval for side effects and cannot be
   talked around by the model.
5. **Tests for all of the above**, including negation, third-person concern,
   quoted fiction, prompt injection and multilingual input.

## Privacy

- No analytics, no crash telemetry, no prompt logging.
- Journal content and messages are encrypted with AES-256-GCM before they reach
  SQLite. The key lives beside the database; back it up — losing it means losing
  the entries, and that limitation is stated in the UI.
- Audit rows contain metadata only (event, tool, status, byte counts).
- The local API only listens on `127.0.0.1` and requires a token generated per
  launch.

## Repository map

```
python/hcs_therapy/     runtime package (hardware, profiles, models, runtime, safety, agent, evals)
python/hcs_therapy/     CLI: hcs-therapy, MCP: hcs-therapy-mcp
tests/                  pytest suite
models/manifests/       pinned model manifests
datasets/               dataset manifests + smoke corpus
licenses/manifest.yaml  licence register (verified upstream revisions)
docs/                   architecture, safety, privacy, ADRs
evals/                  local suites and report output
```

## Commands

```powershell
hcs-therapy doctor [--json] [--no-vulkan] [--probe]
hcs-therapy models list|verify|install|remove
hcs-therapy runtime status|smoke [--backend auto|cpu|vulkan]
hcs-therapy serve [--port 8765] [--model ID] [--no-encrypt]
hcs-therapy eval run --suite hcs-core [--provider echo|local]
hcs-therapy eval compare --baseline a.json --candidate b.json
hcs-therapy data validate|scan|leakage
hcs-therapy safety assess "text" | scan "text" | resources
hcs-therapy license verify | generate
hcs-therapy svg sanitize FILE | render SCENE.json
hcs-therapy agent tools | call TOOL --args '{...}' | audit
```

## Honest limitations

- No external benchmark score is reported anywhere. MentalHealthBench, CBT-Bench
  and HealthBench need authorised access or non-commercial terms and are not
  bundled. The local suite measures behaviour on this project's own prompts only.
- Vulkan inference is not claimed until `runtime smoke` has passed on the target
  machine with a real binary and model.
- The default model is Q8_0 because that is the only quantisation Qwen publishes
  officially. Q4_K_M would need a separately audited third-party repo.
- The integrated GPU shares memory with the system. Free-RAM measurement drives
  the profile, so the same machine reports different context sizes at different
  times. That is honest, not unstable.
- No deterministic rule set catches every crisis signal. The gate is conservative
  in both directions and is not a substitute for human care.
- German text quality is untested against native reviewers.

## Licence

Application code: Apache-2.0 (`LICENSE`). Model weights are *not* covered by that
licence — each has its own terms, recorded in `licenses/manifest.yaml` and
`MODEL_ATTRIBUTION.md`. Upstream projects do not endorse this application.

---

**Made with love by hcsmedia and timfromhcs.**
