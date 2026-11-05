# plan.md — current milestone plan

Product: **HCS Therapy Studio** (codename), repo `hcs-therapy-studio`.
Contract: [`AGENTS.md`](AGENTS.md). Research basis: [`RESEARCH-AND-ROADMAP.md`](RESEARCH-AND-ROADMAP.md).

Only one milestone is "active" at a time. A milestone is done when its gate
report in [`status.md`](status.md) cites executed commands and their output.

The long-horizon execution plan for the 2026-11-04 run — including the research
it is based on — is [`LONG-HORIZON-PLAN.md`](LONG-HORIZON-PLAN.md).

---

## M0 — Repository and research freeze (done)

Deliverables: architecture ADRs, licence manifest with verified upstream
revisions, dataset manifest, safety/intended-purpose statement, hardware doctor,
test harness.

Gate: no unknown dependency or model licence; project starts; baseline tests
recorded. → satisfied, see `status.md`.

## M1 — Minimal native LLM runtime (gate passed)

Deliverables: `llama-server` supervision, loopback API, model manager with hash
verification and resumable download, profile selection from measured memory.

Gate: 100 repeated short generations across CPU and Vulkan without a crash, with
latency and RAM recorded.

Done: pinned `llama-server` b12102 (hash recorded), installed
`qwen3-1.7b-gguf-q8-0` (hash verified), `runtime smoke` on CPU and Vulkan, and
100 repeated generations on each backend with zero failures. Numbers:
`docs/benchmarks/m1-runtime-gate.md`.

Remaining: time-to-first-token measurement on the streaming path.

## M2 — Evaluation harness (done for the local suite)

Done: deterministic local suite, per-dimension report with bootstrap confidence
intervals, paired bootstrap significance in `eval compare`, Bradley–Terry
ranking across reports (`eval rank`), calibration measurement with temperature
scaling (`eval calibrate`), report schema v2, and an honest refusal to fake
external benchmarks.

Remaining: adapters for authorised external suites (MentalHealthBench,
CBT-Bench evaluation-only, HealthBench) that fail loudly when credentials or
licences are missing.

## M3 — Dataset pipeline (done for gating, corpus not built)

Done: manifest schema, provenance check, PII scan, dedup, split discipline,
leakage check, review-status gating, smoke-only classification.

Remaining: a clinician-reviewed, permission-cleared bilingual corpus. This is a
human task, not an agent task.

## M4 — CPU LoRA training (pipeline proven on 0.6B)

Done: gated dataset loading, config, memory estimator calibrated against a
measured run, 10-step and 13-step runs, checkpoint save, resume from
checkpoint-10, adapter saved, run recorded in SQLite.

Remaining: reviewer-cleared corpus, adapter A/B evaluation against the baseline,
safety regression report. The 1.7B run was refused by the memory guard on this
machine and stays refused until memory allows it.

## M5 — Safety and product behaviour (done for the deterministic layers)

Done: crisis gate, verified resources, output guard, boundary prompt, tests, **multi-turn
trajectories with a session-level attentiveness window**, German register anchoring with an
A/B measurement.

Remaining: professional review of prompts and templates; a German-speaking reviewer for tone.
Whether the model *behaves* gently during an attentive turn needs the model in the loop and has
not been measured.

## M6 — Agent and MCP layer (done)

Done: tool registry, JSON-Schema validation, policy gate, budgets, audit, stdio
MCP server, path confinement.

Remaining: an external MCP client test (Claude Desktop / OpenCode) against the
server, and a loop controller driving a real model.

## M7 — VLM and graphics (partially done)

Done: SVG sanitiser, constrained scene renderer, licence clearance for two VLM
candidates.

Remaining: prove a VLM export/runtime on this device; build the editor UI.

## M8 — Product UI (done, streaming)

Done: React/Vite client, 8 screens, DE/EN strings, Loam design system, wired to
the real local API; SSE streaming with measured first-token latency in the
footer, stop/copy/regenerate, safe markdown-lite renderer, command palette
(`Ctrl/⌘+K`), skip link, retrieval playground in the Lab screen, product
title/favicon/CSP instead of the Vite scaffold. Browser-verified at 375, 768 and
1440 px: zero console errors, zero horizontal overflow.

Remaining: Tauri shell, automated visual regression, a screen-reader pass, and
the Better Design review tools (still blocked by account quota — the evidence is
rendered-browser measurement, not a tool receipt).

## M7b — Retrieval (done for the lexical layer)

Done: encrypted knowledge index, paragraph/sentence chunking with overlap,
BM25 over words plus BM25 over character trigrams, RRF fusion, MMR
diversification, citation ids, hallucinated-citation detection, CLI
(`kb index|search|stats`), API routes, Lab-screen playground, and the MCP tool
switched from a substring scan to the real index.

Remaining: an embedding model with a cleared licence, to make the retrieval
genuinely hybrid rather than lexical-only. The RRF plumbing already accepts a
third ranking list, so this is a drop-in when a licensed model exists.

## M8b — Numerics library (done)

Done: `hcs_therapy.numerics` with 216 tests, every formula anchored to an
analytically known value: BM25, RRF, MMR, trigram tokenisation, samplers
(top-k/top-p/min-p/typical/penalties/DRY), perplexity, ECE/Brier/NLL,
temperature and Platt scaling, split conformal prediction, Bradley–Terry, Elo,
bootstrap intervals and paired tests, κ statistics, MRR/NDCG/pass@k, GGUF block
arithmetic, KV-cache bytes, LoRA parameter counts, SLERP, TIES, DARE, and the
DPO/IPO/ORPO/SimPO/CPO losses with a GRPO advantage.

## M9 — Browser/Vercel edition (not started)

## M10 — Packages and executable (not started)

## M11 — Release hardening and publication (blocked on explicit authorisation)

Publication requires the account owner's explicit approval for the GitHub
repository, registry credentials and Vercel deployment. The agent prepares
everything and stops there.
