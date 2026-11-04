# AGENTS.md — HCS Therapy Studio

> **Autonomous build contract for Codex / Claude Code / OpenCode / other long-horizon agents**  
> Product codename: **HCS Therapy Studio**  
> Proposed public repository: `hcs-therapy-studio`  
> Credit: **Made with love by hcsmedia and timfromhcs**  
> Research snapshot: **2026-11-04**

This file is the authoritative implementation contract for the first stable release. Read it completely before editing code. The agent must work in small, reversible steps, keep the project runnable, and report what was actually tested. Never invent successful tests, model support, benchmark scores, licences, or deployment status.

---

## 0. Mission and definition of done

Build a polished, local-first wellbeing and creative AI platform around a customised 1–3B-class open-weight text model. The platform combines:

- a specialist wellbeing / psychoeducation / reflective-conversation assistant;
- local LLM inference with Vulkan-first and CPU fallback;
- a controlled MCP/tool-use agent;
- a local training and model-editing laboratory;
- model, dataset, and benchmark management;
- a vision-language module for images and documents;
- a native image editor and text-to-SVG/layout designer;
- a browser edition hosted as a static Vercel app using local WebGPU/WASM inference where validated;
- a Windows desktop edition distributed as a single self-extracting `.exe` installer with the default quantised text model included;
- Python wheel / PyPI package and npm package;
- high-quality documentation, attribution, release provenance, and a new public GitHub repository.

The first stable release is **not** a medical diagnostic product and must not claim to diagnose or treat mental-health conditions. Do not build a product that impersonates a licensed therapist. The initial scope is supportive conversation, psychoeducation, guided self-reflection, journaling, creative work, and research tooling.

### Stable means

- no known open Critical or High severity defects;
- all required tests pass on a clean environment;
- the desktop and browser applications start, work, and fail gracefully;
- no unhandled exception in core user journeys;
- the local inference stack has measured CPU and Vulkan profiles;
- the model/dataset/runtime licence chain is complete;
- safety and privacy gates pass;
- all shipped features are real, tested, and documented;
- artifacts install in fresh environments;
- the release can be reproduced from a tagged commit and locked dependencies.

“Perfect” or “zero bugs forever” is not a verifiable engineering criterion. Use the above release definition and maintain a public known-limitations section.

---

## 1. Absolute non-negotiables

1. **Local-first:** never send conversations, journals, mood entries, uploaded images, documents, test responses, or training examples to a cloud inference service.
2. **No hidden telemetry:** no analytics, tracking pixels, session replay, or prompt/content logging. Diagnostics must redact content and require an explicit opt-in.
3. **No fabricated capability:** never label a feature as supported until the real path works on hardware or browser runtime and has tests.
4. **No fake placeholders:** no dead buttons, empty menus, mock model results presented as real, fake charts, static “success” messages, or unimplemented workflows in a release build.
5. **Licence before download/bundle:** no model, dataset, encoder, decoder, tokenizer, VAE, code dependency, or benchmark dataset enters the public package without provenance and licence records.
6. **Evaluation before promotion:** every new model or checkpoint must beat or at least match its declared baseline on the defined acceptance suite without safety regressions.
7. **Immutable baselines:** preserve original model weights and hashes. Never overwrite the only copy of a base model/checkpoint.
8. **Bounded agents:** tool calls and agent loops have hard step, time, token, and permission limits.
9. **Human approval for side effects:** write, delete, export, send, publish, or external actions require explicit approval. Read-only is the default.
10. **Safety is architectural:** prompt text alone does not establish safety. Add product-level policies, tool constraints, crisis handling, logging boundaries, and automated tests.
11. **No autonomous clinical decision-making:** no diagnosis, treatment selection, medication change, or clinical triage beyond a limited safe handoff response.
12. **No benchmark contamination:** evaluation test sets stay out of training, RAG, demos, prompt examples, and generated preference data.
13. **No infinite self-healing:** retry a repair a bounded number of times, then revert or report a blocker with evidence.
14. **No false release claims:** never say a package is on PyPI/npm, a repository is public, or Vercel is deployed unless the exact action succeeded and has been verified.
15. **No secrets in code:** credentials, tokens, signing keys, API keys, and registry credentials belong in environment variables or secure CI secrets.

---

## 2. Source of truth and first tasks

Before implementation:

1. Read `RESEARCH-AND-ROADMAP.md`.
2. Inspect the existing repository and the user's current working tree. Do not overwrite useful work or delete files without a reason.
3. Create `plan.md`, `status.md`, `decisions/ADR-0001-project-scope.md`, and `risk-register.md`.
4. Create a complete dependency/model/data licence manifest before fetching large assets.
5. Record actual hardware: OS, CPU, RAM, GPU, Vulkan driver, free disk, model directory, Python, Node, Rust, browser versions. Do not assume that the old device report still exactly matches the current machine; re-detect.
6. Run baseline checks before refactoring: repository status, package tests, current build, runtime smoke test.
7. Establish an issue list with acceptance criteria; keep `status.md` updated after every phase.

### Project variables

Use these defaults unless the existing repository already defines compatible names:

- application display name: `HCS Therapy Studio`;
- repository slug: `hcs-therapy-studio`;
- Python package: `hcs-therapy-core`;
- Python import namespace: `hcs_therapy`;
- CLI command: `hcs-therapy`;
- MCP command: `hcs-therapy-mcp`;
- npm package: `@hcsmedia/therapy-sdk`;
- desktop bundle identifier: `space.hcsmedia.therapy-studio`;
- main model display name: `HCS Wellbeing 1.7B` only after model adaptation and acceptance;
- base model: `Qwen/Qwen3-1.7B-Base` (pin an exact commit);
- default baseline model: `Qwen/Qwen3-1.7B` (pin an exact commit);
- default inference artifact: Q4_K_M after measured regression checks;
- product credit: `Made with love by hcsmedia and timfromhcs`.

Do not call a base Qwen checkpoint “HCS” until an actual derivative has been created, evaluated, and documented. Keep upstream name visible in the attribution.

---

## 3. Scope boundaries and safety contract

### 3.1 Supported v1 modes

- **Supportive conversation:** empathic listening, accurate paraphrase, non-directive help, and clarifying questions.
- **Psychoeducation:** general explanations with sources, uncertainty, and a non-clinical boundary.
- **Guided reflection:** thought records, emotion/need reflection, values reflection, and optional structured exercises.
- **Journal:** local private notes, mood check-ins, tags, search, export, and delete.
- **Creative studio:** text-to-SVG, layouts, posters, worksheets, palettes, layers, and normal image editing.
- **Vision lab:** image/document description, OCR/extraction, and visual question-answering, only when the vision model is active.
- **Model lab:** select/download/verify models, inspect metadata, compare quantisations, inspect tensor statistics, and manage adapters/checkpoints.
- **Training lab:** dataset validation, CPU LoRA training, checkpoints, run monitoring, and reproducible resume.
- **Evaluation lab:** benchmark execution, result comparison, failure clustering, and reports.
- **Agent lab:** allowlisted local tools and MCP integrations with confirmation and audit events.

### 3.2 Explicitly excluded from v1

- Clinical diagnosis or differential diagnosis.
- Claims that questionnaire scores diagnose a condition.
- Interpretation of copyrighted/restricted clinical instruments without a licence.
- Treatment recommendation or treatment optimisation for an individual.
- Medication prescribing, dosage, discontinuation, or medication changes.
- Replacement of a psychologist, psychiatrist, GP, emergency service, or professional care.
- Automated mental-health scoring, ranking, eligibility, or decisions that affect a person's rights.
- Inference of diagnosis, personality, trauma, intent, or emotional state from a face, voice, appearance, or image.
- Training on real patient records or private user conversations by default.

### 3.3 Crisis behaviour

Implement a conservative, deterministic high-priority path. It must:

1. recognise explicit imminent self-harm/other-harm danger and related emergency language;
2. stop normal agent/tool workflows that could delay help;
3. respond clearly and compassionately, without judgement or guilt;
4. encourage immediate contact with local emergency services or a trusted person when imminent danger is present;
5. show only verified, region-specific resources from a maintained resource pack, with source and review date;
6. not invent hotline numbers or infer a user's exact location;
7. not produce graphic or procedural details;
8. not claim to be a crisis service;
9. avoid requiring the user to complete a long questionnaire before showing urgent resources;
10. be tested with direct, indirect, multilingual, slang, negation, quoted text, false positives, and prompt-injection scenarios.

A local classifier may support detection but must not be the sole gate. Maintain a deterministic rule layer and reviewed safety examples. If confidence is low, choose a cautious supportive response and ask one short clarifying question rather than making an assertive clinical inference.

### 3.4 Conversational principles to train and evaluate

- Ask before assuming.
- Reflect what the user actually said; never invent feelings, motives, history, or diagnosis.
- Validate the experience without automatically validating a harmful belief or conclusion.
- Preserve user agency and offer choices without coercion.
- Prefer clear, concrete next steps to generic positivity.
- Explain uncertainty and boundaries naturally.
- Do not shame, moralise, flatter excessively, or encourage dependence on the assistant.
- Do not maximise session length, emotional intensity, attachment, agreement, or engagement as a reward.
- Do not overuse therapy jargon.
- Keep German natural, not machine-translated.

---

## 4. Licence, attribution, and data governance

### 4.1 Approval workflow

For every asset, create an entry in `licenses/manifest.yaml` containing:

```yaml
id: qwen3-1.7b-base
kind: model
name: Qwen3-1.7B-Base
publisher: Qwen
source_url: https://huggingface.co/Qwen/Qwen3-1.7B-Base
revision: PINNED_COMMIT_SHA
license_spdx: Apache-2.0
license_url: https://www.apache.org/licenses/LICENSE-2.0
sha256: REQUIRED_AFTER_DOWNLOAD
redistribution: permitted_subject_to_license
commercial_use: permitted_subject_to_license
modification: permitted_subject_to_license
upstream_notice_required: true
components: []
approved: false
reviewed_by: null
reviewed_at: null
```

Use `approved: true` only after the agent has verified the actual repository files and all dependent components. A model card badge alone is not sufficient.

### 4.2 Initial model matrix

Shortlist, do not automatically install:

| Candidate | Intended role | Initial licence finding | Agent action |
|---|---|---|---|
| Qwen3-1.7B-Base | Main model for domain SFT | Apache-2.0 | Preferred training candidate; pin revision |
| Qwen3-1.7B | Baseline | Apache-2.0 | Baseline only; preserve untouched |
| SmolLM3-3B | Challenger | Apache-2.0 | Compare on common suite |
| Granite 3.3 2B Instruct | Challenger | Apache-2.0 | Compare German + tool use |
| Qwen3-VL-2B-Instruct | Vision | Apache-2.0 | Test only after export/runtime spike |
| SmolVLM2-2.2B-Instruct | Vision alternative | Apache-2.0 | Alternative if deployment is better |
| Sana Sprint 1.6B | Text-to-image | Apache-2.0 top-level, but Gemma2-2B-IT encoder and research-purpose positioning | Do not bundle unless full chain and permitted intended use are reviewed |
| Sana 1.5 1.6B | Text-to-image | Apache-2.0 top-level, Gemma terms for text encoder | Do not bundle by default |
| PixArt-Sigma | Text-to-image | OpenRAIL++-M | Reject strict permissive filter |
| Janus-Pro / JanusFlow | Unified vision + generation | DeepSeek Model Licence with use-based conditions | Reject strict OSI-style permissive filter unless project owner deliberately accepts separate terms after legal review |
| Qwen-Image-Edit 20B | Image editing | Apache-2.0 | Not suitable for target device; do not bundle |

### 4.3 Training data rules

Allowed by default:

- original HCS content authored by contributors who sign a permission/release agreement;
- synthetic examples created from original templates and reviewed by qualified professionals;
- public-domain, CC0, or CC BY material where the exact source and conditions are verified;
- deterministic synthetic tool-use traces generated in a test sandbox;
- datasets with an explicit permissive licence and complete provenance.

Not allowed by default:

- real therapy transcripts, hospital notes, private messages, user journals, or clinical records;
- scraped internet conversations without rights and privacy basis;
- ESConv and CBT-Bench as an unrestricted commercial training corpus under their current NC/academic restrictions;
- benchmark test sets used as training, prompt examples, or RAG content;
- copyrighted test instruments, DSM text, paid manuals, or copied clinical scales without permission;
- raw health data from the app being re-used for training automatically.

Every dataset needs a card, exact revision, licence copy, source URL, checksum, language, schema, privacy review, transformation recipe, dedup report, and split manifest.

### 4.4 Evaluation leakage prevention

- `evals/external/` contains only authorised evaluation files and is excluded from all training/RAG packaging.
- `evals/holdout/` is access-restricted in the training workflow.
- `datasets/train/` is the only training input directory.
- Build a test that fails if test-set filenames or hashes appear in training manifests.
- Do not publish proprietary answer keys or full copyrighted benchmark prompts.

### 4.5 Attribution output

Generate these files from manifests:

- `LICENSE` for HCS-owned code (recommend Apache-2.0);
- `NOTICE`;
- `THIRD_PARTY_NOTICES.md`;
- `MODEL_ATTRIBUTION.md`;
- `DATASET_ATTRIBUTION.md`;
- `SBOM.spdx.json` or CycloneDX equivalent.

For every model: upstream organisation, creator/model name, exact source URL, revision, licence, paper/citation, files included, components and required notices. Never imply the upstream provider endorses the application.

---

## 5. Hardware detection and compute profile

### 5.1 Detect at runtime

Collect only what is required to select a safe profile:

- OS, OS build, architecture;
- CPU model, cores/threads, supported SIMD instructions;
- total/available physical memory and pagefile/swap;
- GPU device name, API, driver, dedicated/shared memory where accessible;
- Vulkan instance/device extension availability;
- free disk for model cache and temporary files;
- browser WebGPU availability and adapter limits (browser build only);
- measured warm-up throughput and memory use.

Do not send hardware fingerprints or exact system information to a cloud endpoint. Show the detected profile locally and allow manual override.

### 5.2 Target priority

1. Windows 11 desktop.
2. `llama.cpp` Vulkan backend if device probe and generation test pass.
3. CPU backend always available.
4. External model directory supported, including USB3 drives.
5. No Docker requirement.
6. Do not require CUDA.
7. Do not treat unsupported ROCm on Radeon 680M as a dependency.
8. Do not treat PyTorch Vulkan inference operations as proof that autograd training works.

### 5.3 Profile selection

Create profiles based on live memory and warm-up tests, not a hard-coded GPU model name.

- `SAFE_CPU`: CPU inference, conservative context, one active model.
- `VULKAN_BALANCED`: Vulkan inference if warm-up stable; model quantised; context measured.
- `VULKAN_LOW_MEMORY`: minimum supported layers and smaller context; CPU fallback for remainder if backend supports it.
- `BROWSER_WEBGPU`: model compiled for WebLLM/MLC and browser device; model size limited by storage/device limits.
- `BROWSER_WASM`: CPU/WASM path for small supported models; explicitly slower.

For the 1.7B model, test Q4_K_M first, then compare Q5_K_M/Q8_0. Start with 4K context; only offer 8K/16K when repeated load/stress tests pass on the current profile. Context length from a model card is not equivalent to safe local memory usage.

### 5.4 Telemetry-free performance record

Store locally:

- model ID/revision/quantisation;
- runtime commit/build flags;
- selected backend and devices;
- load time, first-token latency, tokens/sec;
- RAM, GPU memory where measurable, KV/context settings;
- temperature/throttling only if available with user consent;
- crash/fallback count.

Provide export as JSON/CSV with private details redacted by default.

---

## 6. Model architecture, training, and weight operations

### 6.1 Main model workflow

1. Download Qwen3-1.7B-Base from a pinned revision.
2. Verify licence files, model config, tokenizer, revision, and SHA-256.
3. Save the raw upstream snapshot read-only.
4. Run base and instruct baselines with consistent prompts and settings.
5. Build a small synthetic data smoke set.
6. Execute 10–30 CPU training steps to validate the training environment.
7. Save/resume a checkpoint and verify numerical consistency.
8. Run a short LoRA SFT experiment.
9. Compare on a local development set; inspect qualitative outputs.
10. Expand only after memory, speed, and score gates pass.
11. Run clinician review / safety set and external benchmark evaluation.
12. Save adapter; merge to a new checkpoint only if promotion criteria pass.
13. Quantise a copy; preserve master checkpoint and adapter.
14. Run Vulkan and CPU inference smoke/stress tests.
15. Promote by writing a model card and updating the model manifest.

### 6.2 Candidate challengers

Benchmark the same dataset/prompt suite with:

- Qwen3-1.7B-Base + custom LoRA;
- Qwen3-1.7B-Instruct untouched;
- Granite 3.3 2B Instruct untouched;
- SmolLM3 3B untouched.

Do not compare different quantisations, context limits, prompt styles, or decoding settings and present the results as a fair model ranking. Record the differences.

### 6.3 CPU training implementation

Use a locked Python environment and these libraries only when compatibility tests pass:

- PyTorch;
- Hugging Face Transformers;
- PEFT;
- TRL;
- Datasets;
- Accelerate (CPU config);
- Safetensors;
- `psutil` or equivalent for local memory/time measurements.

Force CPU deliberately with `TrainingArguments(use_cpu=True)` where using Transformers Trainer. Verify dtype support at runtime. Use FP32 as the compatibility fallback. BF16 may be tested only after a correctness and throughput check; do not force FP16/BF16 based on generic advice.

Start configuration (experiment, not guarantee):

```yaml
training:
  method: lora_sft
  use_cpu: true
  precision: auto_safe
  batch_size: 1
  gradient_accumulation_steps: 8
  max_seq_length: 1024
  gradient_checkpointing: true
  num_workers: 0
  lora:
    r: 8
    alpha: 16
    dropout: 0.05
  optimizer: adamw_torch
  learning_rate: 0.0001
  warmup_ratio: 0.03
  max_steps: 30
  save_steps: 10
  eval_steps: 10
  seed: 42
  resume_from_checkpoint: true
```

The first 30-step run is a smoke experiment only. After successful validation, use a tracked sweep for sequence length, rank, learning rate, batch accumulation, and data mixture. Store the final effective config and all dependency versions with each run.

### 6.4 Memory safeguards

- Before model load/training, estimate RAM requirement and check free disk.
- Refuse to start if the available-memory safety margin is too low; explain how to change the model/sequence length.
- Use batch size 1 for initial training; accumulate gradients.
- Start with 512–1024 token sequence length; expand after measurement.
- Use checkpointing only if supported and tested; record added time cost.
- Do not load a second full model for DPO/GRPO without an explicit memory estimate.
- Do not run training and heavy inference concurrently on the target PC by default.
- Save checkpoint to a temp path, verify load, then atomically promote.
- Disk full, shutdown, or crash must not corrupt the last good checkpoint.

### 6.5 SFT data design

Use structured conversation JSONL with one consistent Qwen3 chat template and fields for provenance. Include:

- German and English support conversations;
- reflective listening and question selection;
- psychoeducation with sources;
- tentative CBT self-reflection examples;
- autonomy-preserving suggestions;
- uncertainty and abstention;
- safe crisis hand-off examples written/reviewed by qualified people;
- tool-call examples from a fake/sandboxed environment;
- refusal/boundary examples;
- adversarial prompts and prompt injection to test the safety layer.

Do not train the model to emit internal chain-of-thought. Train concise, user-facing explanations and structured outputs when needed.

### 6.6 Preference/RL progression

- Start with SFT only.
- Add DPO when there are high-quality, reviewed preference pairs and a stable evaluation baseline.
- Add GRPO only for narrow, programmatically verifiable tasks such as argument schema correctness or expected sandbox state changes.
- Keep therapeutic response quality under expert/human review; no single scalar reward can validate clinical benefit.
- Do not optimise for adherence, emotional dependence, session time, agreement, or user disclosure volume.

### 6.7 Parameter Lab

Implement an experiment UI rather than a fake “edit all weights by hand” screen:

- model structure/config viewer;
- parameter count and layer map;
- tensor name, shape, dtype, and storage format;
- tensor distribution statistics and heatmap for sampled regions;
- safe, read-only default;
- controlled single-tensor slice edits only on copies;
- LoRA rank/alpha experiments;
- adapter merge/unmerge;
- task-vector interpolation;
- pruning and ablation experiments;
- before/after hash, diff summary, and evaluation report;
- rollback and immutable baseline.

Every edit action creates an experiment record with: parent model hash, operation, arguments, changed tensor names, timestamp, output hash, and evaluation outcome. Reject incompatible tensor shapes. Do not allocate a giant browser array holding all weights in memory.

---

## 7. Benchmark and quality programme

### 7.1 Required test layers

**A. Unit tests**

- tokenizer/chat-template formatting;
- prompt boundary assembly;
- schema validation;
- dataset manifests and hashes;
- licence-manifest validation;
- model download/checksum/resume;
- SQLite migration and recovery;
- local path sanitisation;
- permission policy;
- model profile detection;
- export/import and deletion.

**B. Component tests**

- model load / generation / stop tokens;
- Vulkan initialisation and CPU fallback;
- local OpenAI-compatible endpoint;
- MCP server and tool schema validation;
- crisis detector / policy layer;
- VLM image load/OCR/answer;
- SVG renderer and editor operations;
- WebGPU and WASM backend selection;
- cache and offline behaviour.

**C. Integration tests**

- user session -> local model -> UI stream;
- journal write -> encrypted local persistence -> export/delete;
- model download -> verify -> load -> unload;
- LoRA smoke train -> checkpoint -> resume -> evaluate;
- MCP tool call -> user confirmation -> sandbox result -> audit event;
- browser PWA -> model cache -> offline session;
- desktop sidecar launch -> health check -> shutdown cleanup.

**D. E2E tests**

- first launch with no model;
- install bundled model;
- first local chat;
- CPU fallback with Vulkan disabled;
- corrupted/missing model recovery;
- interrupted download recovery;
- low disk and low RAM handling;
- local data export/deletion;
- Vercel page running with WebGPU unavailable;
- no network after assets/models have been cached.

**E. Human/visual tests**

- German and English naturalness;
- clear therapeutic boundary language;
- no over-assumption / no excessive agreement;
- accessible design and keyboard navigation;
- responsive widths from small phone to desktop;
- motion reduced / dark and light themes;
- editor canvas rendering, typography, layer ordering;
- screenshot comparisons at stable viewport sizes.

### 7.2 Text acceptance suite

Use a mix of:

- MentalHealthBench (external mental-health conversation benchmark);
- CBT-Bench (where its current terms permit evaluation; do not train on locked test split);
- HealthBench as secondary health communication reference;
- HCS bilingual clinician-reviewed set;
- selected LM Evaluation Harness tasks for instruction following and broad regressions;
- calibration and hallucination set;
- adversarial and crisis test suite.

Score separately for:

- accurate listening;
- empathy/validation;
- appropriate context gathering;
- agency/autonomy;
- clarity/actionability;
- uncertainty calibration;
- safe boundary adherence;
- crisis handoff;
- general reasoning/instruction following;
- German/English language quality.

Never collapse all of these into a single “therapy quality” score without showing sub-scores.

### 7.3 Tool-use acceptance suite

- BFCL v4;
- MCPMark Verified;
- MCPAgentBench or MCP-AgentBench;
- MCP-Atlas public subset where licence and access allow;
- HCS Local Tool Suite.

Because benchmark tasks and graders can contain defects, always verify the local tool contract with independent task assertions. Report pass@1, success rate, invalid argument rate, wrong tool rate, unnecessary tool rate, permission violations, recoverable errors, tool calls per task, and wall-clock latency.

### 7.4 Vision acceptance suite

- Qwen3-VL-2B and SmolVLM2-2.2B compared under a common image-size and hardware budget;
- DocVQA, OCRBench, POPE, MMMU/MMStar where licences and runner compatibility allow;
- project-made synthetic screenshot/document set;
- verify no unsupported psychological/medical inference from image appearance.

### 7.5 Image acceptance suite

The native image editor must be tested regardless of generative model status:

- crop, resize, rotate, flip;
- layers, z-order, opacity;
- masks and non-destructive adjustment;
- text placement and font fallback;
- SVG import/export;
- colour/palette and contrast;
- undo/redo and autosave recovery;
- export to PNG/SVG/JPEG/WebP where supported.

For future diffusion model support, require a fully approved licence chain, a real backend test, GenEval 2 and/or GEditBench v2 where applicable, visual review, and resource budgets before activation.

### 7.6 Regression rule

A candidate cannot be promoted merely because its target training loss improves. It must:

- show improvement on the target skill set;
- have no severe regressions in the safety suite;
- remain within agreed language/general-task degradation bounds;
- maintain valid tool-call schemas;
- pass CPU and Vulkan inference;
- reproduce evaluation from a clean run.

Set numeric thresholds after recording baseline variance; do not invent thresholds from a one-off run.

---

## 8. Agent runtime and MCP security

### 8.1 Architecture

- Main model proposes tool calls.
- A deterministic tool registry defines allowed tools, JSON Schema, permissions, and side effects.
- A policy gate validates request, state, user permission, argument size, path, and rate limit.
- The tool runner executes a single action in a sandbox/allowlisted location.
- The tool output is bounded and redacted before being returned to the model.
- A loop controller imposes step/time/token limits and detects repetition.
- An audit event records action name, timestamp, status, and redacted summary; do not record personal content by default.

### 8.2 Default safe tools

Read-only by default:

- `get_local_time`;
- `list_available_local_models`;
- `get_device_profile`;
- `search_local_knowledge_base`;
- `read_user_selected_file`;
- `list_user_approved_export_targets`;
- `get_benchmark_report`.

Approval required:

- create/update journal entry;
- export or delete personal data;
- download a model pack;
- run a training job;
- write or modify files;
- call an external MCP server;
- open an external URL;
- change a model or memory setting.

Never expose raw unrestricted shell, PowerShell, arbitrary SQL, or unrestricted filesystem delete as a default MCP tool.

### 8.3 Loop budgets

- fixed maximum number of calls per user action;
- maximum total tool-output bytes;
- maximum wall-clock duration;
- maximum retries per tool;
- detect repeated identical calls and abort;
- cancel button must cancel the current task and stop spawned processes;
- read-only tool calls may be batched only when the policy permits;
- irreversible actions always require user confirmation.

### 8.4 Local API security

- bind to `127.0.0.1` only;
- generate an unpredictable per-launch token;
- restrict CORS to the desktop origin and explicitly trusted local web origin;
- reject hostile browser origins;
- validate JSON schema and request size;
- disable directory browsing and arbitrary path traversal;
- require confirmation for write/delete/export;
- log metadata only, never journal or prompt content;
- close ports/processes cleanly on exit.

### 8.5 Browser MCP limitations

A browser page hosted on Vercel cannot spawn local `stdio` MCP servers or access arbitrary OS files. Implement either:

- built-in browser-safe tools executed inside the page; or
- an explicitly installed local bridge that exposes a loopback/streamable HTTP transport with auth and user approval.

Never claim full desktop MCP parity in the browser without this bridge.

---

## 9. Backend, frontend, and repository architecture

### 9.1 Preferred monorepo

```text
hcs-therapy-studio/
├─ AGENTS.md
├─ README.md
├─ LICENSE
├─ NOTICE
├─ THIRD_PARTY_NOTICES.md
├─ MODEL_ATTRIBUTION.md
├─ DATASET_ATTRIBUTION.md
├─ SECURITY.md
├─ CONTRIBUTING.md
├─ CODE_OF_CONDUCT.md
├─ plan.md
├─ status.md
├─ risk-register.md
├─ docs/
│  ├─ architecture/
│  ├─ decisions/
│  ├─ safety/
│  ├─ privacy/
│  ├─ model-cards/
│  ├─ datasets/
│  ├─ benchmarks/
│  ├─ installation/
│  └─ release/
├─ apps/
│  ├─ desktop/              # Tauri 2 host
│  └─ web/                  # Vite/React static Vercel client
├─ packages/
│  ├─ ui/                   # shared React UI components
│  ├─ sdk-ts/               # typed API client
│  └─ mcp-client/           # safe MCP integration client
├─ crates/
│  ├─ app-core/             # Rust process/device/storage orchestration
│  └─ local-bridge/         # local HTTP/MCP bridge
├─ python/
│  ├─ hcs_therapy/          # inference API, datasets, evaluator, CLI
│  └─ hcs_therapy_train/    # training-only optional dependencies
├─ models/
│  ├─ manifests/
│  ├─ adapters/
│  ├─ quantized/
│  └─ experiments/
├─ datasets/
│  ├─ manifests/
│  ├─ raw/                  # gitignored
│  ├─ processed/            # gitignored
│  ├─ train/                # gitignored or LFS only by explicit decision
│  └─ holdout/              # gitignored/restricted
├─ evals/
│  ├─ configs/
│  ├─ external/
│  ├─ hcs_local/
│  ├─ holdout/
│  ├─ reports/
│  └─ scripts/
├─ scripts/
│  ├─ bootstrap/
│  ├─ build/
│  ├─ package/
│  ├─ benchmark/
│  └─ release/
├─ licenses/
│  ├─ manifest.yaml
│  └─ upstream/
└─ .github/
   ├─ workflows/
   ├─ ISSUE_TEMPLATE/
   └─ pull_request_template.md
```

Adapt the structure when a framework requires a standard layout, but preserve clear boundaries between UI, runtime, training, data, and evaluation.

### 9.2 Type boundaries

- TypeScript owns UI contracts and front-end SDK types.
- Rust owns desktop process lifecycle, device probing, secure local bridge, and application filesystem boundaries.
- Python owns training, dataset validation, benchmark orchestration, and optional researcher CLI.
- `llama.cpp` owns text inference process execution in native builds.
- Browser build owns WebLLM/ONNX Runtime Web inference within browser constraints.
- Model metadata is stored in a single versioned schema shared through generated types.

Do not duplicate model IDs, license versions, API schemas, or safety mode definitions in multiple files without a generated source of truth.

### 9.3 API contracts

Provide a typed, documented local API. Minimum routes:

- `GET /health` — runtime readiness and selected backend, no user data;
- `GET /v1/models` — installed/available model metadata;
- `POST /v1/chat/completions` — streaming and non-streaming local chat;
- `POST /v1/embeddings` — only if a retrieval embedding model is installed;
- `GET /api/device/profile`;
- `GET /api/models` and `POST /api/models/download`;
- `POST /api/models/verify`;
- `GET /api/training/runs`;
- `POST /api/training/runs`;
- `POST /api/training/runs/{id}/cancel`;
- `GET /api/evals` and `POST /api/evals/run`;
- `GET /api/storage/usage`;
- `POST /api/data/export` and `DELETE /api/data/{id}` behind confirmation.

Use OpenAPI generation and contract tests. The local bridge must reject unauthenticated requests except explicitly safe health checks.

### 9.4 Storage schema

At minimum:

- `sessions`;
- `messages`;
- `journal_entries`;
- `user_preferences`;
- `model_installs`;
- `model_revisions`;
- `training_runs`;
- `checkpoints`;
- `dataset_manifests`;
- `benchmark_runs`;
- `tool_permissions`;
- `audit_events` (redacted metadata only).

Use migrations, foreign keys, transactions, crash recovery, export/import tests, and a deletion path. Never store secrets in SQLite plaintext. Sensitive user content must be encrypted at rest or be explicitly user-disabled; explain key backup/recovery limitations.

---

## 10. Frontend and visual design requirements

### 10.1 Stack

- React + TypeScript + Vite;
- shared design system in `packages/ui`;
- Tauri desktop shell;
- Vercel static hosting for browser mode;
- motion library only where accessible and genuinely useful;
- no network dependency for core navigation or local session rendering after installation.

Choose dependencies only after a quick maintenance/licence/security review. Pin lockfiles.

### 10.2 Visual direction

- modern, calm, polished, premium, responsive;
- subtle glass panels, soft shadows, strong text contrast;
- a restrained accent palette and distinct status colours only when meaningful;
- comfortable reading width for support conversations;
- generous spacing and clear typography;
- consistent icon language;
- subtle animated transitions, never distracting;
- light/dark theme;
- German/English localisation with complete string coverage;
- responsive layouts for 320px, 375px, 768px, 1024px, 1440px and ultrawide.

### 10.3 Accessibility

- WCAG 2.2 AA target where practicable;
- keyboard navigation for all functionality;
- visible focus rings;
- semantic structure and accessible labels;
- sufficient contrast;
- screen-reader announcements for model state and tool confirmation;
- reduced-motion support;
- no status indication by colour alone;
- accessible dialogs, menus, tables, sliders, and canvas controls;
- text zoom and responsive reflow.

### 10.4 User journeys to implement end-to-end

1. First launch -> privacy explanation -> model check -> local model selection -> sample chat.
2. Start a support session -> response stream -> save only with user choice -> export/delete.
3. Start a reflection worksheet -> complete steps -> preview -> save locally.
4. Open a document -> local VLM/OCR -> show extracted text and uncertainty -> user approves any save.
5. Create a poster/worksheet from a text prompt -> editable SVG layout -> edit layers -> export.
6. Download VLM pack -> verify hash -> load -> image question -> unload safely.
7. Open Training Lab -> inspect dataset manifest -> 30-step CPU smoke -> checkpoint -> resume -> compare.
8. Run evaluation -> show per-dimension results -> inspect failures -> create experiment.
9. Configure MCP -> choose allowed tools -> test in sandbox -> approve action -> inspect audit history.
10. Switch to offline mode -> verify no network required for local chat and cached assets.

No journey is complete until tested with a real click-through or automation script.

---

## 11. Browser/WebGPU edition

### 11.1 Requirements

- Vercel deployment is static; the browser performs model inference locally.
- Use WebLLM/MLC for supported LLM variants; pin compiled model libraries and weights.
- Use ONNX Runtime WebGPU for compatible vision exports; fallback to WASM only when the model and memory budget make sense.
- Perform a small benchmark and choose a safe context/quantisation.
- Cache only after clear user consent; show disk quota and delete controls.
- Service-worker cache must be versioned and purgeable.
- Provide offline shell and no-network inference once model assets are cached.
- No hidden calls to remote LLM providers.

### 11.2 Browser limitations to show honestly

- Browser memory and VRAM reporting is approximate and differs across browsers.
- WebGPU availability and driver path vary; some environments require fallback or cannot run the model.
- WebLLM model support depends on the model being compiled to a supported MLC format.
- Browser pages cannot spawn arbitrary native processes or stdio MCP servers.
- Native training, full checkpoint conversion, Vulkan build, and full data access remain desktop/CLI tasks for v1.
- Browser storage may be evicted or quota-limited; do not promise permanent model retention.

### 11.3 Web security

- strict Content Security Policy;
- no third-party analytics;
- no user-content request bodies to Vercel functions;
- no public writable API endpoints;
- explicit disclosure when model weights are fetched from an external host;
- use integrity hashes and pinned versions;
- sanitize imported SVG and document content;
- defend against XSS, prompt injection in retrieved files, and malicious SVG scripts.

### 11.4 Feature parity matrix

Maintain `docs/feature-parity.md` with columns: feature, desktop, browser WebGPU, browser WASM, required model, data local/network, limitations. Update it on every feature change. Do not label the editions “identical” unless the matrix proves it.

---

## 12. Image / visual subsystem

### 12.1 Stable v1: real editor without a diffusion dependency

Implement:

- SVG and canvas workspace;
- editable text, shape and image layers;
- selection, resize, rotate, reorder, duplicate, group;
- crop, mask, transparency, opacity;
- fill/stroke/gradient/palette controls;
- typography and text wrapping;
- import PNG/JPEG/WebP/SVG;
- export PNG/JPEG/WebP/SVG where library permits;
- undo/redo, autosave, recovery, and version history;
- text-to-SVG generation using the main LLM with a constrained schema and sanitised renderer;
- design presets for worksheets, cards, posters, diagrams, and simple infographics.

### 12.2 Generative image module gate

Do not ship a model until:

- the main weight, text encoder, VAE, decoder, tokenizer, and code licence chain is approved;
- any extra terms are compatible with redistribution and intended use;
- the target device runs a real smoke test at realistic resolution;
- memory and latency budgets are defined;
- output moderation and misuse constraints are in place;
- GenEval 2 / editing evaluation and human visual QA have been run;
- the Vercel WebGPU build is tested separately.

Candidate runtimes such as `stable-diffusion.cpp` may be evaluated because the runtime is MIT-licensed and C/C++; the runtime licence does not grant rights to any model weights. Verify actual Vulkan support for the pinned commit and device.

### 12.3 Visual integrity

Do not let a model generate hidden executable SVG, scripts, remote image fetches, or HTML. Use a schema-driven renderer, sanitise SVG and asset URLs, and block script/event-handler attributes. Keep image metadata local and offer a privacy-safe metadata-strip export option.

---

## 13. Desktop executable and build system

### 13.1 Desktop plan

- Tauri 2 host;
- bundled `llama-server` sidecar built with Vulkan support and CPU fallback;
- React UI bundled into the desktop app;
- default Q4_K_M model included in the one-file installer payload;
- user-selected model directory supported;
- extraction to writable per-user data directory;
- SHA-256 verification before first load;
- clean process start/stop and port management;
- installer repair, upgrade and uninstall;
- no admin rights required for per-user installation by default.

### 13.2 Single-file packaging

The target artifact is one download, e.g. `HCS-Therapy-Studio-Setup.exe`. It can be a self-extracting bundle that streams embedded resources to a user-writable directory on first run. Do not load the multi-gigabyte model into RAM during extraction. If the full embedded payload makes downloads or updates unreasonable, offer an optional smaller bootstrapper but do not silently claim it contains model weights.

### 13.3 Release build reproducibility

- pinned Rust, Node, Python, CMake, compiler, Vulkan SDK and model revisions;
- clean build directory;
- SBOM;
- build manifest including compiler flags and source commit;
- SHA-256 for final installer, wheel and npm tarball;
- test installer in a clean Windows user account;
- test low-disk, corrupted archive, offline launch, and upgrade paths;
- no unsigned/signature trust claim unless signing is executed and verified.

---

## 14. Python wheel, PyPI, and npm packages

### 14.1 Python wheel

- use `pyproject.toml` and standard build backend;
- package core runtime/metadata without forcing training extras on all users;
- expose extras such as `[train]`, `[eval]`, `[vision]` only when optional dependencies are valid;
- build with `python -m build`;
- run `twine check dist/*`;
- install from the produced wheel into a clean venv;
- test `hcs-therapy --help`, `hcs-therapy doctor`, `hcs-therapy models list`, and a local API smoke;
- publish to TestPyPI only with explicit credentials/approval.

### 14.2 npm package

- TypeScript declarations shipped;
- explicit ESM/CJS support only if actually built and tested;
- minimal dependency surface;
- browser-safe package excludes Node/native modules;
- `npm pack` and clean fixture install;
- test package exports, types, tree-shaking and no accidental secret/model file inclusion;
- `npm publish --dry-run` before a real publish;
- real publication requires credentials and release approval.

### 14.3 Cross-package compatibility

- generate types from a shared OpenAPI schema;
- contract test Python API and TS SDK;
- run a version-compatibility test between current desktop and SDK;
- document compatibility/version policy;
- pin schema and expose `/version` and `/health`.

---

## 15. Self-healing development loop

This loop is mandatory for all non-trivial changes.

### 15.1 Loop

1. **Observe:** reproduce the issue with a minimal test, exact environment, logs and current commit.
2. **Classify:** bug, regression, environment, unsupported capability, flaky test, licence problem, safety issue, or design problem.
3. **Hypothesise:** write one testable cause before changing code.
4. **Patch minimally:** smallest reversible change; avoid unrelated refactoring.
5. **Verify targeted:** run the failing test and adjacent tests.
6. **Verify regression:** run the relevant full suite.
7. **Inspect visually:** for UI changes, capture screenshots and inspect layout/console/network.
8. **Record:** update `status.md`, issue, test report, and ADR if architecture changed.
9. **Promote or revert:** retain only a verified patch.

### 15.2 Retry policy

- Up to 3 targeted repair cycles for one defect.
- After 3 failed cycles, stop automatic editing, revert to last good commit, and file a blocker with logs, repro steps, and a suggested next experiment.
- Do not disable tests, lower thresholds, skip type checks, or mask exceptions to make a build green.
- A test can be quarantined only with a written reason, owner, expiry, and replacement plan.

### 15.3 Agent loop safety

- maximum autonomous task steps configurable and finite;
- no recursive agent spawning without approval;
- no arbitrary external network, account, or publishing actions without explicit permission;
- no writing outside project and configured temp/model directories;
- use branch/worktree per substantial feature;
- checkpoint before risky migration/model changes;
- ask before destructive operations if the consequence is not recoverable.

---

## 16. Testing commands and expected reports

The exact scripts will be implemented by the agent, but standardise a top-level command surface:

```powershell
# environment and source checks
uv sync --all-groups
npm ci
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings

# Python
uv run pytest -q
uv run ruff check .
uv run mypy python/hcs_therapy

# Web/desktop UI
npm run lint
npm run typecheck
npm run test -- --run
npm run build
npm run test:e2e

# Runtime
hcs-therapy doctor --json
hcs-therapy models verify --all
hcs-therapy runtime smoke --backend auto
hcs-therapy runtime smoke --backend cpu
hcs-therapy runtime smoke --backend vulkan

# Model training
hcs-therapy train smoke --config configs/train/cpu-lora-smoke.yaml
hcs-therapy train resume-test --latest

# Evaluation
hcs-therapy eval run --suite hcs-core --report reports/latest
hcs-therapy eval compare --baseline baseline.json --candidate candidate.json

# Packaging
python -m build
python -m twine check dist/*
npm pack
npm publish --dry-run

# desktop package
npm run tauri build
```

Adapt executable names to final entry points, but keep one documented command surface. All scripts must return non-zero on failure and write a machine-readable JSON report. Never print a green “PASS” if an unexecuted test is merely skipped.

### Test report schema

Every full validation report should include:

- commit hash and dirty/clean status;
- date/time and OS/runtime versions;
- exact command;
- pass/fail/skipped counts;
- logs and artifact paths;
- model/data revisions and hashes;
- known warnings and quarantines;
- test duration;
- gate decision and human approver when required.

---

## 17. Visual QA and accessibility gate

For every UI milestone:

1. Run the app at 320px, 375px, 768px, 1024px, 1440px and ultrawide.
2. Inspect light and dark themes.
3. Test keyboard-only navigation.
4. Test screen-reader names/roles for main controls.
5. Test reduced motion.
6. Check contrast and focus state.
7. Inspect loading, empty, offline, error, permission, and low-memory states.
8. Test long German strings and translated content.
9. Capture screenshots for Home, Chat, Journal, Reflection, Vision, Editor, Model Lab, Training, Evaluation, MCP, Settings.
10. Compare with expected screenshots and fix layout issues before proceeding.

A page is not “visually QA'd” merely because it compiles or is visible once.

---

## 18. Documentation deliverables

Before stable release, create and maintain:

- `README.md` — purpose, screenshots, quick start, requirements, core features, honest limitations;
- `AGENTS.md` — this build contract;
- `plan.md` — current milestone plan;
- `status.md` — actual state and latest verified tests;
- `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`;
- `MODEL_ATTRIBUTION.md`, `DATASET_ATTRIBUTION.md`;
- `SECURITY.md` — security boundary and vulnerability reporting;
- `docs/architecture/system-overview.md`;
- `docs/architecture/local-inference.md`;
- `docs/architecture/browser-inference.md`;
- `docs/privacy/data-flow.md` and retention/delete/export policy;
- `docs/safety/intended-purpose.md`, safety policy and known limitations;
- model cards for each trained checkpoint;
- dataset cards for every training and evaluation dataset;
- benchmark reports with baseline comparisons;
- training recipes and exact command/configs;
- installation and troubleshooting guides;
- API / MCP documentation;
- feature parity matrix for desktop and web;
- release notes and build provenance.

README claims must be generated from verified feature flags / benchmark reports where possible. Clearly separate implemented, experimental, and planned features.

---

## 19. GitHub repository creation and publication

Only after all stable gates pass:

1. Review the final branch and clean git status.
2. Run all tests on a fresh clone.
3. Run licence, secret, dependency, and model manifest scans.
4. Ensure model weights/datasets are not accidentally committed or pushed unless explicitly approved and permitted.
5. Generate release artifacts and SHA-256 hashes.
6. Create a new public repository named `hcs-therapy-studio` under the authorised owner/account.
7. Set default branch `main`, add description/topics, issue templates, CI badge, licence, security policy, and README.
8. Push source and tags; verify remote `main` commit equals local release commit.
9. Publish release notes and artifacts; verify download links and checksums.
10. Deploy static Vercel demo and verify production URL, browser-only inference, and privacy network behaviour.
11. Upload Python/npm packages only with valid credentials and explicit approval.
12. Run a final install test from the published release, not just the working directory.

Do not create a new public repo or publish packages until the user has explicitly authorised the account/owner/repository operation and any required credentials are available. The agent may prepare all files and commands first.

### Repository description

`A local-first wellbeing, psychoeducation, reflection, multimodal and AI research studio. Runs locally with CPU/Vulkan inference and an optional browser WebGPU edition. Made with love by hcsmedia and timfromhcs.`

### Suggested topics

`local-ai`, `open-weights`, `llama-cpp`, `vulkan`, `webgpu`, `wasm`, `tauri`, `mcp`, `wellbeing`, `psychoeducation`, `fine-tuning`, `peft`, `multimodal`, `hcsmedia`.

---

## 20. Milestone plan in exact order

### M0 — Repository and research freeze

- inspect existing source;
- establish architecture and ADRs;
- pin baseline revisions;
- create licence and dataset manifests;
- write safety/intended-purpose statement;
- hardware doctor script.

**Gate:** no unknown dependency or model licence; project starts and baseline tests recorded.

### M1 — Minimal native LLM runtime

- build/package `llama.cpp` Vulkan sidecar;
- run Qwen3 1.7B GGUF;
- CPU fallback;
- local OpenAI-compatible API;
- model manager and hash verification;
- performance profile and crash handling.

**Gate:** 100 repeated short generations across CPU and Vulkan where Vulkan is available, with no crash; benchmark latency/RAM; no unsupported device claim.

### M2 — Evaluation harness

- integrate LM Evaluation Harness or custom adapter;
- add HCS bilingual tests;
- wire MentalHealthBench and CBT-Bench evaluation adapters where authorised;
- add safety, calibration and hallucination tests;
- create baseline report.

**Gate:** same baseline report reproducible from a clean setup.

### M3 — Dataset pipeline

- manifest schema;
- provenance and licence scanner;
- PII/data-quality checks;
- dedup and split-by-source;
- original synthetic bilingual seed set;
- sealed holdout process.

**Gate:** no row without provenance; train/eval leakage checks pass.

### M4 — CPU LoRA training

- tiny smoke model/config;
- CPU step timing and memory profile;
- Qwen3-1.7B LoRA smoke;
- save/resume checkpoint;
- adapter A/B evaluation;
- controlled merge and quantisation.

**Gate:** training resumes reliably; candidate demonstrates measured improvement with no major regression; otherwise retain baseline and document why.

### M5 — Safety and product behaviour

- crisis flow;
- non-diagnostic self-reflection modes;
- local knowledge retrieval;
- consent, export/delete, local data encryption;
- professional review protocol;
- safety regression report.

**Gate:** no critical/high safety issue in the agreed test set; no diagnosis/medication features in UI or prompts.

### M6 — Agent and MCP layer

- tool registry and schema validation;
- local safe tools;
- step/time/size limits;
- user consent and audit log;
- MCP transport and local bridge;
- tool-use benchmarks.

**Gate:** tool calls cannot escape allowed scope; all side effects require approval; failure recovery tested.

### M7 — VLM and graphics

- benchmark Qwen3-VL-2B vs SmolVLM2-2.2B;
- choose one only after runtime and memory test;
- implement image/document ingestion;
- native canvas and SVG design editor;
- text-to-SVG generation with sanitisation;
- optionally research diffusion model licence chain.

**Gate:** VLM works within safe memory budget; editor undo/redo/export and SVG sanitisation pass; no diffusion model bundled without licence approval.

### M8 — Product UI

- all core journeys;
- responsive design;
- visual QA screenshots;
- accessibility gate;
- full localisation;
- error/empty/offline states.

**Gate:** all major user journeys tested end-to-end; no dead controls.

### M9 — Browser/Vercel edition

- WebLLM model compile;
- WebGPU capability probe;
- WASM fallback;
- OPFS/IndexedDB cache;
- local-only network audit;
- browser-safe tools;
- local bridge for optional MCP.

**Gate:** browser model actually runs locally, network inspection confirms no user content upload, offline mode verified, limitations shown.

### M10 — Packages and executable

- single self-extracting Windows setup EXE;
- embedded model and sidecar;
- wheel build and clean install;
- npm pack and clean install;
- TestPyPI/npm dry-run;
- upgrade/uninstall/repair tests.

**Gate:** all artifacts install on clean environments; hashes/manifests match.

### M11 — Release hardening and publication

- security and dependency scan;
- SBOM and attribution;
- fresh clone build;
- fresh user install;
- benchmark and visual reports;
- final README;
- repo create/push/release/Vercel deployment with authorised credentials;
- post-release smoke test.

**Gate:** no known Critical/High bugs; all release checks documented; all links and artifacts verified.

---

## 21. Decision log requirements

For any major alternative, create an ADR with:

- context and concrete constraints;
- options considered;
- test or research evidence;
- licence findings;
- performance/memory findings;
- decision and reasons;
- consequences and rollback path;
- date and commit.

Required ADRs:

- base model choice;
- local inference runtime;
- training backend;
- VLM choice;
- image generation decision (including decision to defer);
- local data encryption approach;
- browser inference engine;
- desktop packaging strategy;
- project licence and model/dataset distribution model.

---

## 22. Final agent response format

At the end of each milestone, report:

1. What was implemented (specific paths/features).
2. What commands were run.
3. Exact test results, including skipped tests.
4. Hardware/backend actually tested.
5. Model and dataset revisions/licences actually verified.
6. Benchmark results and baseline deltas, if any.
7. Known limitations and unresolved blockers.
8. Next milestone with acceptance criteria.
9. Git commit(s) and branch status.

At final release, add download URLs only after verifying them. Do not use phrases such as “perfect”, “100% error-free”, “clinically proven”, or “SOTA” unless the exact claim is substantiated and scoped.

---

## 23. Upstream reference links

### Models

- Qwen3 1.7B Base: <https://huggingface.co/Qwen/Qwen3-1.7B-Base>
- Qwen3 1.7B Instruct: <https://huggingface.co/Qwen/Qwen3-1.7B>
- Qwen3 GGUF: <https://huggingface.co/Qwen/Qwen3-1.7B-GGUF>
- SmolLM3 3B: <https://huggingface.co/HuggingFaceTB/SmolLM3-3B>
- Granite 3.3 2B Instruct: <https://huggingface.co/ibm-granite/granite-3.3-2b-instruct>
- Qwen3-VL 2B: <https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct>
- SmolVLM2 2.2B: <https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct>

### Training / model editing

- PEFT: <https://huggingface.co/docs/peft/>
- TRL: <https://huggingface.co/docs/trl/>
- Transformers CPU training: <https://github.com/huggingface/transformers/blob/main/docs/source/en/cpu.md>
- Transformers hardware guide: <https://huggingface.co/docs/transformers/main/hardware>
- LoRA paper: <https://arxiv.org/abs/2106.09685>
- TIES-Merging: <https://arxiv.org/abs/2306.01708>

### Benchmarks

- MentalHealthBench: <https://openai.com/index/introducing-mentalhealthbench/>
- CBT-Bench: <https://aclanthology.org/2025.naacl-long.196/>
- CBT-Bench dataset: <https://huggingface.co/datasets/Psychotherapy-LLM/CBT-Bench>
- HealthBench: <https://openai.com/index/healthbench/>
- ESConv upstream: <https://github.com/thu-coai/Emotional-Support-Conversation>
- BFCL: <https://gorilla.cs.berkeley.edu/leaderboard.html>
- BFCL review: <https://epoch.ai/benchmarks/berkeley-function-calling-leaderboard/review>
- MCPMark: <https://github.com/eval-sys/mcpmark>
- MCPAgentBench: <https://github.com/Brunestuder/MCPAgentBench>
- MCP-Atlas: <https://arxiv.org/abs/2602.00933>
- MCP-AgentBench: <https://ojs.aaai.org/index.php/AAAI/article/view/40347>
- LM Evaluation Harness: <https://github.com/EleutherAI/lm-evaluation-harness>
- GenEval 2: <https://github.com/facebookresearch/GenEval2>
- GEditBench v2: <https://arxiv.org/abs/2603.28547>

### Runtime / UI / packaging

- llama.cpp: <https://github.com/ggml-org/llama.cpp>
- llama.cpp Vulkan build: <https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md>
- WebLLM: <https://github.com/mlc-ai/web-llm>
- ONNX Runtime WebGPU: <https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html>
- Transformers.js WebGPU: <https://huggingface.co/docs/transformers.js/en/guides/webgpu>
- Tauri installer: <https://tauri.app/distribute/windows-installer/>
- Tauri sidecar: <https://v3.tauri.app/develop/sidecar/>
- PyInstaller one-file: <https://pyinstaller.org/en/latest/operating-mode.html>

### Licences / regulation

- OSI Open Source AI Definition: <https://opensource.org/ai/open-source-ai-definition>
- DeepSeek Model Licence: <https://github.com/deepseek-ai/DeepSeek-LLM/blob/HEAD/LICENSE-MODEL>
- GDPR Article 9: <https://eur-lex.europa.eu/legal-content/EN-DE/TXT/?from=EN&uri=CELEX%3A32016R0679>
- MDCG Rule 11: <https://health.ec.europa.eu/system/files/2021-10/mdcg_2021-24_en_0.pdf>
- AI Act timeline: <https://ai-act-service-desk.ec.europa.eu/en/ai-act/eu-ai-act-implementation-timeline>

---

**Project signature:**  
**HCS Therapy Studio — Made with love by hcsmedia and timfromhcs.**
