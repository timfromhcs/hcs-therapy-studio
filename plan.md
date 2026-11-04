# plan.md — current milestone plan

Product: **HCS Therapy Studio** (codename), repo `hcs-therapy-studio`.
Contract: [`AGENTS.md`](AGENTS.md). Research basis: [`RESEARCH-AND-ROADMAP.md`](RESEARCH-AND-ROADMAP.md).

Only one milestone is "active" at a time. A milestone is done when its gate
report in [`status.md`](status.md) cites executed commands and their output.

---

## M0 — Repository and research freeze (done)

Deliverables: architecture ADRs, licence manifest with verified upstream
revisions, dataset manifest, safety/intended-purpose statement, hardware doctor,
test harness.

Gate: no unknown dependency or model licence; project starts; baseline tests
recorded. → satisfied, see `status.md`.

## M1 — Minimal native LLM runtime (implemented, gate pending a local smoke run)

Deliverables: `llama-server` supervision, loopback API, model manager with hash
verification and resumable download, profile selection from measured memory.

Gate: 100 repeated short generations across CPU and Vulkan without a crash, with
latency and RAM recorded.

Remaining work: obtain a pinned `llama-server` Vulkan build, install
`qwen3-1.7b-gguf-q8-0`, run `runtime smoke` on both `--backend cpu` and
`--backend vulkan`, then run the 100-generation stress script.

## M2 — Evaluation harness (partially done)

Done: deterministic local suite, per-dimension report, A/B regression compare,
honest refusal to fake external benchmarks.

Remaining: adapters for authorised external suites (MentalHealthBench,
CBT-Bench evaluation-only, HealthBench) that fail loudly when credentials or
licences are missing.

## M3 — Dataset pipeline (done for gating, corpus not built)

Done: manifest schema, provenance check, PII scan, dedup, split discipline,
leakage check, review-status gating, smoke-only classification.

Remaining: a clinician-reviewed, permission-cleared bilingual corpus. This is a
human task, not an agent task.

## M4 — CPU LoRA training (scaffolded)

Done: gated dataset loading, config, memory estimator, smoke-run planning.

Remaining: PyTorch install on the target, 10–30 step run, checkpoint resume
verification, adapter A/B evaluation.

## M5 — Safety and product behaviour (done for the deterministic layers)

Done: crisis gate, verified resources, output guard, boundary prompt, tests.

Remaining: professional review of prompts and templates; a German-speaking
reviewer for tone.

## M6 — Agent and MCP layer (done)

Done: tool registry, JSON-Schema validation, policy gate, budgets, audit, stdio
MCP server, path confinement.

Remaining: an external MCP client test (Claude Desktop / OpenCode) against the
server, and a loop controller driving a real model.

## M7 — VLM and graphics (partially done)

Done: SVG sanitiser, constrained scene renderer, licence clearance for two VLM
candidates.

Remaining: prove a VLM export/runtime on this device; build the editor UI.

## M8 — Product UI (not started)

Remaining: React/Vite app, all journeys, visual QA, accessibility gate.

## M9 — Browser/Vercel edition (not started)

## M10 — Packages and executable (not started)

## M11 — Release hardening and publication (blocked on explicit authorisation)

Publication requires the account owner's explicit approval for the GitHub
repository, registry credentials and Vercel deployment. The agent prepares
everything and stops there.
