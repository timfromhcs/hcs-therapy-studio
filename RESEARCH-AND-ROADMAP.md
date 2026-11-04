# HCS Therapy Studio — Research & Engineering Roadmap

**Research snapshot:** 2026-11-04  
**Project codename:** HCS Therapy Studio  
**Suggested repository:** `hcs-therapy-studio`  
**Credits:** Made with love by hcsmedia and timfromhcs  
**Primary target:** Windows 11, Ryzen 7 7735HS, Radeon 680M / Vulkan, CPU fallback  
**Product class for v1:** local-first wellbeing, psychoeducation, reflective journaling, creative and research tooling — not a medical device or clinical diagnostic service.

> This is an engineering plan, not medical or legal advice. A software product that claims to diagnose or guide treatment can trigger medical-device and other regulatory obligations. Keep intended purpose, UI copy, datasets, and release claims aligned.

---

## 1. Executive recommendation

Build one local-first platform with independently replaceable modules rather than one monolithic neural network that is expected to do everything.

### Recommended initial stack

| Role | Candidate | Why it is shortlisted | Decision |
|---|---|---|---|
| Main text / therapy-support model | `Qwen/Qwen3-1.7B-Base` | 1.7B parameters, Apache-2.0, ungated weights, useful base for supervised adaptation | **Primary candidate**; benchmark against instruct baseline before training |
| Main text baseline | `Qwen/Qwen3-1.7B` | Apache-2.0 and instruction-tuned; measures whether custom tuning improves on a ready-made assistant | **Mandatory baseline** |
| Independent 3B challenger | `HuggingFaceTB/SmolLM3-3B` | Apache-2.0, 3B, multilingual and reasoning-oriented model card | Benchmark challenger; likely heavier |
| Independent 2B challenger | `ibm-granite/granite-3.3-2b-instruct` | Apache-2.0, multi-language support including German, structured reasoning | Benchmark challenger |
| Vision-language candidate | `Qwen/Qwen3-VL-2B-Instruct` | Apache-2.0; image/text model | First VLM candidate; runtime conversion must be proven |
| Vision-language alternative | `HuggingFaceTB/SmolVLM2-2.2B-Instruct` | Apache-2.0; compact model family | Alternative if Qwen3-VL export/backend is unsuitable |
| Text embedding / retrieval | Select after a small German/English retrieval benchmark | Avoid adding a second model before it has measurable value | Phase 2 optional |
| Text-to-image | No model approved yet under the strict release filter | Current attractive candidates have extra terms, restrictive licences, or impractical size | **Research gate, not a promised v1 feature** |

Model references:

- Qwen3 1.7B Base: <https://huggingface.co/Qwen/Qwen3-1.7B-Base>
- Qwen3 1.7B Instruct: <https://huggingface.co/Qwen/Qwen3-1.7B>
- Qwen3-1.7B GGUF: <https://huggingface.co/Qwen/Qwen3-1.7B-GGUF>
- SmolLM3 3B: <https://huggingface.co/HuggingFaceTB/SmolLM3-3B>
- Granite 3.3 2B Instruct: <https://huggingface.co/ibm-granite/granite-3.3-2b-instruct>
- Qwen3-VL 2B: <https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct>
- SmolVLM2 2.2B: <https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct>

The main candidate's published full-precision weights are about 3.45 GB in the Hugging Face repository. A quantized GGUF can be substantially smaller, but total runtime memory also includes the KV cache, context, compute buffers, UI, and operating system. Never make a RAM/VRAM-fit claim from weight-file size alone.

## 2. Define what “open source” means for this project

Use a strict approval filter for all bundled model weights, tokenizers, encoders, decoders, VAEs, datasets, evaluation code, and runtime dependencies.

### Green: default acceptance

- Apache License 2.0, MIT, BSD-2-Clause, BSD-3-Clause, or CC0 where appropriate.
- Direct, non-gated download.
- Explicit licence file in the actual model/dataset repository.
- Derivatives and redistribution permitted under the terms.
- Every auxiliary component has its own audited licence and model card.
- The exact revision/commit is pinned and checksummed.

### Amber: legal review required; do not bundle by default

- Research-only statements or non-commercial conditions.
- Use-based model licences.
- “Open weights” with additional usage terms.
- Model repositories that declare Apache/MIT but depend on separately licensed model components.
- Missing or ambiguous dataset provenance.

### Red: reject for the default release

- Non-commercial-only material where the distribution/use case may be commercial.
- Unknown or absent rights for weights/data.
- Gated access or terms incompatible with redistribution.
- Any model or data whose source cannot be documented.

### Important distinction

“Downloadable open weights” is not automatically the same thing as fully Open Source AI under the Open Source Initiative’s Open Source AI Definition 1.0. That definition expects the preferred form for modification: data information, training and inference code, and parameters. Therefore describe this project accurately as **open-source application code plus permissively licensed open-weight components**, unless and until the full model-data and training disclosure requirements are met.

Reference: <https://opensource.org/ai/open-source-ai-definition>

### Model licence findings from this research pass

- Qwen3 1.7B Base and Instruct declare Apache-2.0. Qwen's project README says its open-weight Qwen3 family is Apache-2.0.
- Granite 3.3 2B Instruct declares Apache-2.0.
- SmolLM3 3B declares Apache-2.0.
- Qwen3-VL-2B-Instruct declares Apache-2.0.
- SmolVLM2-2.2B-Instruct declares Apache-2.0.
- Sana Sprint 1.6B declares Apache-2.0 for the diffusion model, but its model card names `Gemma2-2B-IT` as the fixed text encoder and describes the model as intended for research. The Gemma component has separate terms. Do not treat the top-level Apache label as the complete licence chain.
- Sana 1.5 1.6B likewise identifies Gemma-2-2B-IT and Gemma terms.
- PixArt-Sigma uses CreativeML Open RAIL++-M, not the strict permissive filter.
- Janus-Pro / JanusFlow use the DeepSeek Model Licence for weights, notwithstanding code/model-card MIT labels. The weight licence contains use-based restrictions and redistribution conditions; it is not interchangeable with a plain MIT licence.
- Qwen-Image-Edit is Apache-2.0 but is a 20B-parameter model with a repository size around 57.7 GB; it is not a fit for the stated consumer device.

Relevant source pages:

- <https://huggingface.co/Qwen/Qwen3-1.7B-Base>
- <https://github.com/QwenLM/Qwen3>
- <https://huggingface.co/HuggingFaceTB/SmolLM3-3B>
- <https://huggingface.co/ibm-granite/granite-3.3-2b-instruct>
- <https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct>
- <https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct>
- <https://huggingface.co/Efficient-Large-Model/Sana_Sprint_1.6B_1024px>
- <https://huggingface.co/Efficient-Large-Model/SANA1.5_1.6B_1024px>
- <https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS>
- <https://github.com/deepseek-ai/DeepSeek-LLM/blob/HEAD/LICENSE-MODEL>
- <https://huggingface.co/Qwen/Qwen-Image-Edit>

## 3. Why hand-editing individual weights is not the main training method

A transformer checkpoint contains billions of interdependent numeric values. Randomly changing scalar weights usually damages learned representations; it does not provide a principled way to add a skill. Also, the number of parameters is determined by architecture dimensions (layers, hidden width, attention heads, feed-forward width, vocabulary, and related tensors). Changing the tensor shape of a pretrained checkpoint does not magically resize it while preserving its learned knowledge.

The useful interpretation of “manual weight editing” is a **Model Surgery / Parameter Lab** with controlled, inspectable operations:

1. Load a frozen base checkpoint and record its hash.
2. Apply a controlled modification to a copy: LoRA delta, pruning mask, selected layer/head ablation, task-vector interpolation, or a documented manual tensor edit on a small selected slice.
3. Save a separate candidate checkpoint and a machine-readable change manifest.
4. Run the same fixed evaluation suite against baseline and candidate.
5. Keep the candidate only if the target score improves without a safety/general-capability regression.
6. Preserve the ability to restore the immutable parent checkpoint.

Useful parameter operations:

- **LoRA:** train a low-rank update, commonly expressed as `W' = W + (alpha/r) * B A`, while freezing the base weight matrix `W`. This is the practical first choice for constrained fine-tuning.
- **Weight-space task vectors:** `delta = theta_finetuned - theta_base`; apply/interpolate the delta only to compatible checkpoints.
- **TIES-Merging:** trim small deltas, resolve sign conflicts, and merge aligned parameter changes. This is an experiment, not a guaranteed improvement.
- **Pruning / layer freezing / ablation:** controlled experiments that need benchmark evidence and recovery snapshots.

Do not expose a UI that pretends a person can meaningfully hand-type billions of scalar weights. Provide a parameter explorer with tensor metadata, distributions, heatmaps, layer selection, small-slice inspection, controlled operations, diffs, and rollback.

References:

- LoRA paper: <https://arxiv.org/abs/2106.09685>
- Hugging Face PEFT: <https://huggingface.co/docs/peft/>
- TIES-Merging paper: <https://arxiv.org/abs/2306.01708>
- TIES-Merging NeurIPS publication: <https://papers.neurips.cc/paper_files/paper/2023/hash/1644c9af28ab7916874f6fd6228a9bcf-Abstract-Conference.html>

## 4. Mental-health research and safety evaluation

### 4.1 Most relevant benchmarks

| Benchmark / resource | What it measures | How to use it |
|---|---|---|
| MentalHealthBench (2026) | Realistic mental-health conversations; safety, context seeking, user agency, actionable support; acuity levels from non-acute to emergency | Primary external evaluation; keep benchmark data out of training; record exact release/version and rubric grader |
| CBT-Bench (NAACL 2025) | CBT knowledge, cognitive distortion classification, core-belief classification, therapeutic-response generation | External CBT capability check; preserve official test splits; licence is CC BY-NC 4.0, so do not bundle or use commercially without separate permission |
| HealthBench | Physician-written rubrics for open-ended health conversations | Secondary health-communication check, not a replacement for MentalHealthBench |
| ESConv | Emotional support dialogues and support strategies | Research reference only; upstream states academic-research-only, HF card declares CC BY-NC 4.0; do not include in a distributable commercial training corpus |
| HCS Clinician Review Set | Project-specific bilingual examples authored/reviewed by qualified professionals | Main German/English acceptance set; create original scenarios and document reviewers/permissions |

Primary references:

- MentalHealthBench announcement: <https://openai.com/index/introducing-mentalhealthbench/>
- MentalHealthBench paper: <https://cdn.openai.com/ctf-cdn/MentalHealthBench_A_Comprehensive_Benchmark_of_AI_Capabilities_in_Realistic_Mental_Health_Conversations.pdf>
- CBT-Bench publication: <https://aclanthology.org/2025.naacl-long.196/>
- CBT-Bench dataset card: <https://huggingface.co/datasets/Psychotherapy-LLM/CBT-Bench>
- HealthBench: <https://openai.com/index/healthbench/>
- ESConv upstream repository: <https://github.com/thu-coai/Emotional-Support-Conversation>
- ESConv dataset card: <https://huggingface.co/datasets/thu-coai/esconv>

MentalHealthBench was announced on 2026-09-23 and was co-created with more than 80 licensed mental-health experts from 22 countries. Its expert rubrics are weighted and distinguish helpful from harmful behaviours; the benchmark also reports performance across ten mental-health behaviour dimensions. Treat it as an evaluation benchmark, not as a ready-made training corpus.

CBT-Bench is useful because it explicitly separates knowledge recall, cognitive-model classification, and therapeutic response generation. Its public dataset card lists CC BY-NC 4.0. Do not assume it can be used in a public or commercial model release merely because it is downloadable.

ESConv is also not a free-for-any-purpose data source: the upstream repository states academic-research-only, and the Hugging Face card declares CC BY-NC 4.0.

### 4.2 Supporting behavioural competencies

Create original, professionally reviewed examples around:

- reflective listening and accurate paraphrase;
- validation without endorsing harmful beliefs or making assumptions;
- curiosity and context gathering before advice;
- preserving user agency and presenting options without coercion;
- CBT psychoeducation and clearly labelled self-reflection worksheets;
- identifying cognitive distortions as tentative hypotheses, not labels or diagnoses;
- emotional support and strengths/resources exploration;
- motivational-interviewing-style open questions and change talk, with careful scope;
- recognising uncertainty and correcting mistaken assumptions;
- crisis-risk recognition and safe hand-off language;
- transparent boundaries around diagnoses, tests, prescriptions, and treatment decisions;
- multilingual German/English quality, including idiomatic German and culturally aware phrasing.

### 4.3 What the system must not claim or do in v1

- No diagnosis of depression, ADHD, PTSD, bipolar disorder, personality disorders, or any other condition.
- No interpretation of a screening questionnaire as a definitive diagnosis.
- No medication prescribing, dosage advice, medication changes, or treatment planning.
- No claims that the product is a licensed therapist, medical professional, or clinically validated treatment.
- No autonomous decisions about a user's fitness, legal status, benefits, employment, insurance, or access to care.
- No manipulative, dependency-forming, coercive, or deliberately attachment-maximising conversation strategies.
- No replacement of real-world care or emergency services.

A future medical/diagnostic product is a separate regulatory workstream, not a feature flag that can simply be enabled.

## 5. Training-data policy

### 5.1 Data to prioritise

1. Original HCS-authored psychoeducation and conversation examples, reviewed by qualified professionals.
2. Expert-authored synthetic scenarios with written contributor agreements and an explicit redistribution licence.
3. Public-domain / CC0 / CC BY-licensed educational material with provenance and licence snapshots.
4. Tool-call traces produced in a synthetic sandbox, released under a documented permissive licence.
5. Public datasets only after checking the original dataset, upstream source, and every record-level third-party licence.

### 5.2 Data to avoid by default

- Real patient or therapy records, private messages, medical files, or social-media posts.
- Scraped forum, Reddit, Discord, or social support conversations without a clear licence and privacy basis.
- CBT-Bench or ESConv in the commercial/distributable training corpus under their current non-commercial terms.
- Copyrighted clinical manuals, DSM text, proprietary assessment instruments, paywalled books, or copied questionnaires without permissions.
- Synthetic examples that are generated by another model and then treated as ground truth without independent review.
- The locked test examples of any benchmark used for final evaluation.

### 5.3 Dataset manifest requirements

Every dataset manifest must include:

- dataset name, version, source URL, acquisition date, exact revision/commit;
- copyright owner and licence URL plus a local copy of the licence;
- intended permitted use and prohibited use;
- original source and any upstream dependencies;
- language, content type, record count, and known coverage gaps;
- privacy review, PII scan, sensitive-data review, and de-identification procedure;
- transformations, filtering, deduplication, and synthetic-generation recipe;
- train/validation/test assignment and leakage checks;
- annotator/reviewer role and consent/permission records;
- SHA-256 hashes and reproducible export script.

### 5.4 Data split discipline

- Split by source/conversation/person/scenario family, not random individual rows alone.
- Deduplicate before assigning splits.
- Keep all benchmark test data outside training, prompt examples, RAG content, and preference generation.
- Keep a sealed final test set and a separate development set.
- Store evaluation prompts in a restricted folder and never publish answer keys unnecessarily.
- Maintain a contamination scanner and report possible benchmark overlaps.

## 6. Training strategy on the target machine

### 6.1 What the hardware can and cannot do

Target is Windows 11 on Ryzen 7 7735HS with Radeon 680M and Vulkan, with CPU fallback and limited shared memory. `llama.cpp` has a documented Vulkan build path on Windows. That is an inference route, not evidence that PyTorch can backpropagate through every Vulkan operation.

The current PyTorch hardware guide lists CPU as a first-class training backend and says `TrainingArguments` can be forced to CPU with `use_cpu=True`. The current AMD Windows ROCm compatibility matrix does not list Radeon 680M. A 2026 PyTorch issue reports a Vulkan autograd / `nn.Linear` training limitation. So:

- **Training baseline:** CPU with PyTorch + Transformers + PEFT; benchmark first, never assume a fixed throughput.
- **Inference baseline:** `llama.cpp` with Vulkan where device detection and smoke tests pass; CPU fallback always available.
- **Experimental only:** Vulkan training, DirectML training, or ROCm on unsupported Radeon 680M. Do not make them mandatory.
- **QLoRA:** optional experiment only after validating CPU bitsandbytes support, memory use, gradients, and numerical correctness on the exact environment. Do not assume CUDA-oriented examples work on this machine.
- **Full fine-tuning:** out of scope for first stable release on this consumer PC.

References:

- Transformers hardware support: <https://huggingface.co/docs/transformers/main/hardware>
- Transformers CPU training: <https://github.com/huggingface/transformers/blob/main/docs/source/en/cpu.md>
- PEFT: <https://huggingface.co/docs/peft/>
- TRL SFTTrainer: <https://huggingface.co/docs/trl/main/en/sft_trainer>
- TRL/PEFT: <https://huggingface.co/docs/trl/main/en/peft_integration>
- AMD Windows support matrix: <https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html>
- llama.cpp Windows/Vulkan build: <https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md>
- PyTorch Vulkan autograd issue (evidence of a backend limitation, not a complete compatibility specification): <https://github.com/pytorch/pytorch/issues/187698>

### 6.2 Staged model training

**Stage A — Baselines**

- Run Qwen3-1.7B-Base without domain training using a fixed prompt/template.
- Run Qwen3-1.7B-Instruct as a separate ready-made baseline.
- Benchmark Granite 3.3 2B Instruct and SmolLM3 3B on a smaller common test suite.
- Save exact prompt templates, tokenizer versions, revisions, quantisation, context, decoding parameters, and hashes.

**Stage B — CPU training smoke test**

- Start with a tiny, synthetic and permissively licensed dataset.
- Run 10–30 steps to validate loading, gradients, checkpoint save/load, and deterministic resume.
- Benchmark 0.6B or other smaller compatible model first if Qwen3-1.7B proves too slow.
- Measure wall-clock time per step, tokens/sec, peak resident RAM, swap, CPU temperature/throttling, and failure rate.

**Stage C — LoRA SFT**

- Freeze the base model.
- Train adapter parameters only with PEFT.
- Start with rank 4/8; compare rank 16 only if memory and throughput permit.
- Use batch size 1, gradient accumulation, conservative sequence length, gradient checkpointing if supported, and a saved reproducible config.
- Run an ablation on a 256/512/1024/2048 token sequence budget before a large run.
- Use actual device support for BF16; otherwise use a tested FP32 route. Do not force BF16 just because a CPU is recent.
- Log every dataset ID, prompt template, seed, package lock, step, loss, checkpoint, RAM measurement, and run ID.

**Stage D — Preference optimisation**

- Use DPO or another supported preference objective only after SFT has passed safety and quality gates.
- Preferences must be based on clinician-reviewed or independently annotated responses, not a single model judge.
- Include pairwise preferences for helpfulness, autonomy, accuracy, non-assumption, and safety.
- Keep examples of harmful or inappropriate advice in a controlled safety dataset, not as open-ended user-visible content.

**Stage E — Verifiable tool-use optimisation**

- Use synthetic sandbox tasks with deterministic success criteria (correct schema, valid arguments, expected state transition, no unauthorised side effects).
- Consider GRPO only for narrow, verifiable behaviours after the normal agent loop works.
- Do not define a reward that maximises conversation duration, emotional attachment, agreement, or a shallow “therapy score”.
- Any safety reward must be supplemented with explicit tests and expert review; a scalar reward is not a safety guarantee.

**Stage F — Consolidation**

- Merge LoRA into a separate candidate checkpoint only after A/B evaluation.
- Quantise a copy for inference, preserve the master checkpoint and adapter.
- Compare Q4_K_M, Q5_K_M, and Q8_0 only by measured quality/latency/RAM, not by assumptions.
- Test context windows progressively (for example 2K, 4K, 8K); longer context is a capability claim that must be tested.

### 6.3 Training must stop when

- The training dataset's license/provenance is incomplete.
- The baseline cannot be reproduced.
- Validation loss diverges, gradients become non-finite, or training cannot resume from checkpoint.
- The candidate regresses materially on general instruction following, German comprehension, safety, or tool-call correctness.
- It improves a narrow benchmark by becoming more presumptive, more verbose, more agreeable, less calibrated, or less safe.
- There is no clear improvement over the baseline after the agreed evaluation protocol.

## 7. Evaluation suite

### 7.1 Text model

| Area | Suggested test | Key metrics |
|---|---|---|
| Mental-health behaviour | MentalHealthBench | Total and per-dimension score; non-acute/high-acuity/emergency slices; confidence intervals |
| CBT capability | CBT-Bench | Knowledge accuracy, distortion classification, core-belief classification, response rubric |
| Health communication | HealthBench | Weighted rubric score and negative-criterion count |
| General instruction following | IFEval + selected lm-evaluation-harness tasks | Exact instruction compliance and task accuracy |
| German/English | HCS bilingual holdout | Human-rated fluency, semantic fidelity, culturally appropriate register |
| Calibration | HCS uncertainty set | Correct abstention, uncertainty quality, false certainty |
| Hallucination | Source-grounded QA set | Supported-claim precision, citation correctness, fabricated-source rate |
| Robustness | Adversarial/paraphrase set | Stability, prompt-injection resistance, context retention |

Use EleutherAI's LM Evaluation Harness for reproducible general-purpose suites: <https://github.com/EleutherAI/lm-evaluation-harness>.

### 7.2 Agent / tool calling

| Benchmark | Role |
|---|---|
| BFCL v4 | Function-call selection, argument correctness, multi-turn and agentic tool use |
| MCPMark Verified | Multi-step CRUD and realistic MCP workflows with task verifiers |
| MCPAgentBench / MCP-AgentBench | MCP-mediated real-world tool-use evaluation |
| MCP-Atlas | Cross-server discovery and orchestration, distractor resistance |
| HCS Local Tool Suite | Exact product-specific workflows: journal creation, export, knowledge retrieval, local model management |

References:

- BFCL: <https://gorilla.cs.berkeley.edu/leaderboard.html>
- BFCL v4 benchmark review: <https://epoch.ai/benchmarks/berkeley-function-calling-leaderboard/review>
- MCPMark: <https://github.com/eval-sys/mcpmark>
- MCPAgentBench: <https://github.com/Brunestuder/MCPAgentBench>
- MCP-Atlas paper: <https://arxiv.org/abs/2602.00933>
- MCP-AgentBench (AAAI 2026): <https://ojs.aaai.org/index.php/AAAI/article/view/40347>

Caution: an independent 2026 audit reported defects in a sample of BFCL v4 scored tasks. Use BFCL as one signal, not the only release gate; keep local verifiers and a second independent benchmark.

### 7.3 Vision-language

Candidate evaluation set:

- MMMU / MMMU-Pro for multimodal academic-style reasoning;
- DocVQA for document understanding;
- OCRBench for visual text reading;
- POPE for object hallucination checks;
- MMStar or a similar balanced visual reasoning set;
- project-specific image/document tests with consent-free synthetic examples.

Do not let a VLM infer mental-health diagnoses, personality traits, or hidden psychological states from facial expressions, appearance, or private images.

### 7.4 Image generation and editing

Only activate this track after a model passes the model-component licence audit and hardware smoke test.

- Text-to-image: GenEval 2 (800 prompts, compositionality, objects, attributes, relations, counting; evaluated with Soft-TIFA).
- Editing: GEditBench v2 (2026) for instruction coverage and visual consistency.
- Add a human comparison for typography, composition, preservation of identity/structure, prompt adherence, and artefacts.

References:

- GenEval 2: <https://github.com/facebookresearch/GenEval2>
- GEditBench v2 paper: <https://arxiv.org/abs/2603.28547>

For v1, implement a deterministic native image editor and editable text-to-SVG / layout designer. This is useful, testable, and distributable without pretending that an unsuitable image model is production-ready.

### 7.5 Benchmark protocol

Every report must include:

- exact model revision and SHA-256;
- tokenizer, chat template, quantisation, runtime version, hardware and driver;
- context length, temperature, top-p, top-k, seed, and stop rules;
- dataset revision, split, licence and evaluator version;
- raw machine-readable outputs plus aggregate tables;
- mean, standard deviation, confidence intervals where suitable;
- known benchmark limitations and any human review procedure;
- baseline-versus-candidate delta and regression analysis;
- failed cases with error categories, not only a headline score.

No “perfect”, “clinically proven”, “SOTA”, or “diagnostic accuracy” claim without evidence designed for that claim and the appropriate professional/regulatory review.

## 8. Inference and runtime architecture

### 8.1 Desktop

- **UI shell:** Tauri 2 + React + TypeScript + Vite.
- **Local LLM runtime:** bundled `llama.cpp` / `llama-server` sidecar; Vulkan first, CPU fallback.
- **Local API:** loopback-only, OpenAI-compatible endpoints where available.
- **MCP server:** local, explicit tool registry, schema validation, bounded execution.
- **Metadata and user data:** local SQLite database; encrypted-at-rest option/default for sensitive local journals; export/delete controls.
- **Training stack:** separate Python environment / CLI package using PyTorch, Transformers, PEFT, TRL. Do not make the runtime depend on a global Python installation.
- **Model files:** pinned manifest, SHA-256 verification, resumable download, optional external model directory (including external USB storage).

`llama.cpp` has a documented Windows Vulkan build using `GGML_VULKAN=ON`: <https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md>.

Tauri supports Windows setup executables and bundling external sidecars/resources:

- <https://tauri.app/distribute/windows-installer/>
- <https://v3.tauri.app/develop/sidecar/>

### 8.2 Browser / Vercel demo

- Vercel hosts a static web client only; it does not host inference for private user data.
- Browser LLM inference uses WebLLM/MLC WebGPU where the exact model can be compiled and validated.
- ONNX Runtime WebGPU is the alternative for compatible exported VLM/vision components; WASM is the CPU fallback.
- Browser storage uses OPFS / IndexedDB with quota checks and clear-download/delete controls.
- The web app must clearly explain that model weights are downloaded to the user's device and that the model runs inside the browser.
- No telemetry or analytics capturing conversations, images, files, mood entries, health details, or prompts.
- Browser MCP cannot silently launch arbitrary local stdio processes. For MCP, require a separately installed local bridge using a supported HTTP transport and explicit user trust.
- Browser feature detection is not the same as full hardware detection. Use WebGPU adapter capabilities and a short benchmark; do not promise exact detection of dedicated/shared VRAM on all browsers.

Useful references:

- WebLLM: <https://github.com/mlc-ai/web-llm>
- WebLLM docs: <https://llm.mlc.ai/docs/deploy/webllm.html>
- Transformers.js WebGPU: <https://huggingface.co/docs/transformers.js/en/guides/webgpu>
- ONNX Runtime WebGPU: <https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html>
- ONNX Runtime WebGPU execution provider: <https://onnxruntime.ai/docs/execution-providers/WebGPU-ExecutionProvider.html>

Feature parity must be described honestly. Browser-only deployment cannot reproduce every desktop capability: native model conversion, unrestricted filesystem access, local stdio MCP, and long-running training are desktop/CLI features. The web product should expose the same product areas and clearly mark capabilities that require the desktop companion.

### 8.3 Model management and quantisation

- Pin all model files by source revision and checksum.
- Keep master weights, LoRA adapter, merged checkpoint, and inference quantisation in distinct directories.
- Do not quantise the only copy of a trained model.
- Start with Q4_K_M for memory-conscious inference; compare Q5_K_M and Q8_0 empirically.
- Use adaptive context based on real memory headroom; default conservatively (e.g. 4K), expand only after successful stress tests.
- Use KV cache quantisation only when the runtime/model combination supports it and regression tests pass.
- Do not reserve a fixed amount of GPU layers or context for every user; query device, run a short warm-up, and choose a safe profile.
- Ensure CPU fallback is a supported mode, not a crash recovery afterthought.

## 9. UI/UX product map

### Core navigation

1. **Home / Session:** current session, clear privacy state, model and device status.
2. **Support Chat:** empathic conversation, selectable modes, explicit scope label, grounding/context gathering.
3. **Guided Reflection:** thought record, situation/thought/feeling/response structure, values and needs reflection.
4. **Journal:** private notes, mood check-in, optional tags, export/delete, local-only default.
5. **Psychoeducation:** licensed local knowledge base with sources and “learn more” references.
6. **Self-reflection Tools:** optional self-report forms only where copyright/use rights are verified; show scores descriptively, never as diagnoses.
7. **Visual Studio:** SVG generation, layout compositions, typography, palette, shape tools, layer panel, crop/rotate/resize/filters, non-destructive edits.
8. **Vision Lab:** image/document Q&A, OCR/document extraction, with clear uncertainty and no appearance-based psychological inference.
9. **Model Lab:** local model switcher, download/verify, parameter explorer, adapter manager, checkpoints and rollback.
10. **Training Lab:** dataset manifests, CPU training settings, run queue, logs, checkpointing and resume.
11. **Evaluation Lab:** benchmark matrix, per-dimension scorecards, A/B comparisons, visual reports and export.
12. **Agent & MCP:** connected servers, tool permissions, audit log, test mode, manual approval controls.
13. **Settings:** language, theme, accessibility, storage path, device profile, privacy, licenses and attribution.

### Visual system

- Responsive, clean, modern, warm and calm; glass-like surfaces used sparingly rather than overloading text contrast.
- Light/dark themes; accessible contrast; keyboard navigation; visible focus; screen-reader labels.
- Motion should be subtle, with `prefers-reduced-motion` support and a global disable control.
- No streaks, shame, social comparison, coercive nudges, or engagement-maximising emotional hooks.
- Do not display a “mental health score” as a gamified score or user ranking.
- Use clear state indicators: model loading, local-only, file permission, tool awaiting confirmation, offline, low memory, and crisis information.
- Provide empty, loading, error, offline, and permission-denied states for every major screen.

## 10. Privacy, safety, and EU deployment boundary

### Privacy architecture

- Local-first and no cloud inference by default.
- No conversation content in telemetry, crash reports, console logs, benchmark exports, or analytics.
- Encrypt local journal/session data at rest; use a clear key-management story and recovery/export pathway.
- Data minimisation, explicit opt-in for saving memory, transparent retention, export and delete.
- Local model downloads are user-initiated and verified; disclose that model-hosting providers may see download request metadata.
- No silent collection of training examples from user sessions.
- Test local API security: bind only to `127.0.0.1`, random per-run token, strict CORS allowlist, request-size limits, CSRF protections where applicable, no remote interface by default.

### Mental-health safety architecture

A system prompt is not enough. Implement deterministic product-level constraints and tests around the model:

- crisis-intent detection and a simple, direct high-priority response flow;
- do not delay urgent support with model-generated lengthy exercises or multi-tool plans;
- never diagnose or prescribe;
- no overconfidence in screening scores;
- ask clarifying questions when context is insufficient;
- no speculation about someone's hidden thoughts or motives;
- preserve autonomy, invite choice, avoid coercive instructions;
- clear distinction between model output, retrieved educational content, and professional advice;
- local emergency-resource pack with source/date and region selection; no fabricated telephone numbers;
- audit the boundary between safe support and clinical claims.

### Regulatory checkpoints

- GDPR Article 9 treats health data as a special category with additional legal requirements. Local storage reduces data exposure but does not automatically make every processing activity lawful.
- EU MDR Rule 11 can classify software intended to provide information used for diagnostic or therapeutic decisions as medical-device software; exact class depends on intended purpose and potential impact. The European Commission's MDCG guidance gives examples including software intended to diagnose depression from symptoms.
- As of the 2026 AI Act timeline following the Digital Omnibus agreement, Annex III high-risk rules have a scheduled application date of 2 December 2027 and high-risk AI embedded in regulated products under Annex I 2 August 2028; other AI Act provisions and transparency rules already apply earlier. Recheck current law before placing a later release on the market.
- Get qualified legal/regulatory review before claims about diagnosis, treatment recommendations, clinical use, or deployment in healthcare settings.

References:

- GDPR Article 9: <https://eur-lex.europa.eu/legal-content/EN-DE/TXT/?from=EN&uri=CELEX%3A32016R0679>
- European Commission on sensitive data: <https://commission.europa.eu/law/law-topic/data-protection/information-individuals_en>
- MDCG 2021-24 Rule 11: <https://health.ec.europa.eu/system/files/2021-10/mdcg_2021-24_en_0.pdf>
- MDCG 2019-11 Rev.1 announcement: <https://health.ec.europa.eu/latest-updates/update-mdcg-2019-11-rev1-qualification-and-classification-software-regulation-eu-2017745-and-2025-06-17_en>
- AI Act implementation timeline: <https://ai-act-service-desk.ec.europa.eu/en/ai-act/eu-ai-act-implementation-timeline>
- European Commission AI Act policy: <https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai>

## 11. Release and packaging strategy

### Desktop release

- Produce one Windows self-extracting setup `.exe` that includes the runtime, UI, licences/NOTICE, and the default quantised text model.
- On first run, stream-extract to a user-writable `%LOCALAPPDATA%` directory or a user-selected location; do not require Administrator privileges.
- The user can redirect large model packs to an external USB drive.
- The installer must verify all embedded model/runtime checksums, support repair/reinstall, and handle low-disk-space and interrupted extraction cleanly.
- Optional VLM and future image model packs are separate downloads to avoid shipping unused multi-gigabyte components in the default binary.
- Test signing and SmartScreen implications honestly; do not claim a signed/trusted binary without a real certificate.

### Python package

- Build a wheel with `python -m build`.
- Validate with `twine check dist/*`.
- Test install in a fresh venv from the produced wheel.
- Test `pip install -e .`, CLI commands, offline mode, and model manifest validation.
- Only publish to PyPI/TestPyPI when credentials and explicit release approval exist.

### npm packages

- Build typed SDK/UI packages.
- Validate `npm pack` output, package exports, types, dependency licensing, and clean install in a consumer fixture.
- Test on Windows Chromium browsers and at least one CPU-only/WASM fallback.
- Publish only after a release gate and registry credentials are present.

### Vercel

- Static deploy from the web app; no model backend hosted by Vercel.
- Test production URL, route fallback, CSP, cache headers, service worker, offline behavior, and browser-storage quota errors.
- Check that no prompt, image, journal entry, document, or evaluation sample is sent to serverless functions or analytics.

### Attribution and notices

- Code licence for HCS-owned code: Apache-2.0 recommended.
- Include `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, and `MODEL_ATTRIBUTION.md`.
- For each model, display original creator, exact model name, official repository, model card, paper/citation, licence, pinned revision, and any dependency licences.
- Preserve upstream notices and label modified files/weights clearly.
- Do not imply endorsement by Qwen, Hugging Face, IBM, Qualcomm, or other upstream creators.
- Product credit line: **Made with love by hcsmedia and timfromhcs.**

## 12. Phased roadmap and measurable gates

| Phase | Deliverable | Exit gate |
|---|---|---|
| 0. Research & compliance | Model/data licence manifest, architecture ADRs, risk/scope statement | No unreviewed model or dataset enters the build |
| 1. Baseline runtime | Qwen3 1.7B baseline on CPU/Vulkan, API and benchmark runner | Reproducible smoke tests, memory/latency measured, safe fallback |
| 2. Data foundation | Synthetic bilingual wellbeing set, manifests, de-duplication, PII/licence checks | Every training record traceable to rights/provenance |
| 3. Model adaptation | CPU LoRA SFT and saved adapter/checkpoints | Resume works; measured improvement; no major regressions |
| 4. Clinical-safety evaluation | MentalHealthBench, CBT-Bench where permitted, human review | No critical safety regression; limitations documented |
| 5. Agent / MCP | Local tools, MCP bridge, safe approval system | Tool contracts and side effects fully tested |
| 6. Multimodal | Qwen3-VL or SmolVLM2 plus SVG/photo editor | Licence, inference, memory, visual QA pass |
| 7. Product UI | Responsive React/Tauri app, all states and modes | Accessibility, usability, and visual review pass |
| 8. Browser demo | Vercel static app, WebGPU/WASM, local storage | No server-side user content; tested feature matrix |
| 9. Packaging | EXE, wheel/PyPI package test, npm package test | Clean install/uninstall/repair and reproducible artifacts |
| 10. Public release | New GitHub repo, docs, attribution, release notes | All gates green; no known critical/high defects |

Do not skip a gate to preserve a release date. If a specific model is not usable on the target machine, keep the capability modular and record the limitation instead of faking support.

## 13. Research source register

### Text models

- Qwen3 1.7B Base: <https://huggingface.co/Qwen/Qwen3-1.7B-Base>
- Qwen3 1.7B Instruct: <https://huggingface.co/Qwen/Qwen3-1.7B>
- Qwen3 model tooling and training: <https://github.com/QwenLM/Qwen3>
- Qwen3 GGUF: <https://huggingface.co/Qwen/Qwen3-1.7B-GGUF>
- SmolLM3 3B: <https://huggingface.co/HuggingFaceTB/SmolLM3-3B>
- Granite 3.3 2B Instruct: <https://huggingface.co/ibm-granite/granite-3.3-2b-instruct>

### Vision models

- Qwen3-VL 2B Instruct: <https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct>
- SmolVLM2 2.2B Instruct: <https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct>

### Therapy / wellbeing evaluation

- MentalHealthBench: <https://openai.com/index/introducing-mentalhealthbench/>
- MentalHealthBench paper: <https://cdn.openai.com/ctf-cdn/MentalHealthBench_A_Comprehensive_Benchmark_of_AI_Capabilities_in_Realistic_Mental_Health_Conversations.pdf>
- CBT-Bench paper: <https://aclanthology.org/2025.naacl-long.196/>
- CBT-Bench data card: <https://huggingface.co/datasets/Psychotherapy-LLM/CBT-Bench>
- HealthBench: <https://openai.com/index/healthbench/>
- ESConv upstream: <https://github.com/thu-coai/Emotional-Support-Conversation>
- ESConv dataset card: <https://huggingface.co/datasets/thu-coai/esconv>
- HierINT-Dlg 2026 paper: <https://aclanthology.org/2026.emnlp-main.1729/>

### Agent and function calling

- BFCL: <https://gorilla.cs.berkeley.edu/leaderboard.html>
- BFCL review: <https://epoch.ai/benchmarks/berkeley-function-calling-leaderboard/review>
- MCPMark: <https://github.com/eval-sys/mcpmark>
- MCPMark ICLR 2026: <https://proceedings.iclr.cc/paper_files/paper/2026/hash/8138d211ce8790fdfbeeeb9781838a37-Abstract-Conference.html>
- MCPAgentBench: <https://github.com/Brunestuder/MCPAgentBench>
- MCP-AgentBench AAAI 2026: <https://ojs.aaai.org/index.php/AAAI/article/view/40347>
- MCP-Atlas: <https://arxiv.org/abs/2602.00933>
- LM Evaluation Harness: <https://github.com/EleutherAI/lm-evaluation-harness>

### Training and model editing

- PEFT: <https://huggingface.co/docs/peft/>
- TRL: <https://huggingface.co/docs/trl/>
- Transformers CPU training: <https://github.com/huggingface/transformers/blob/main/docs/source/en/cpu.md>
- Transformers hardware: <https://huggingface.co/docs/transformers/main/hardware>
- LoRA paper: <https://arxiv.org/abs/2106.09685>
- TIES-Merging: <https://arxiv.org/abs/2306.01708>
- TIES-Merging NeurIPS: <https://papers.neurips.cc/paper_files/paper/2023/hash/1644c9af28ab7916874f6fd6228a9bcf-Abstract-Conference.html>

### Runtime and packaging

- llama.cpp: <https://github.com/ggml-org/llama.cpp>
- llama.cpp Vulkan build: <https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md>
- WebLLM: <https://github.com/mlc-ai/web-llm>
- ONNX Runtime WebGPU: <https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html>
- Transformers.js WebGPU: <https://huggingface.co/docs/transformers.js/en/guides/webgpu>
- Tauri Windows installer: <https://tauri.app/distribute/windows-installer/>
- Tauri sidecars: <https://v3.tauri.app/develop/sidecar/>
- PyInstaller one-file behaviour: <https://pyinstaller.org/en/latest/operating-mode.html>

### Image models and evaluation

- Sana Sprint 1.6B: <https://huggingface.co/Efficient-Large-Model/Sana_Sprint_1.6B_1024px>
- Sana 1.5 1.6B: <https://huggingface.co/Efficient-Large-Model/SANA1.5_1.6B_1024px>
- PixArt Sigma: <https://huggingface.co/PixArt-alpha/PixArt-Sigma-XL-2-1024-MS>
- Janus-Pro-1B: <https://huggingface.co/deepseek-ai/Janus-Pro-1B>
- JanusFlow-1.3B: <https://huggingface.co/deepseek-ai/JanusFlow-1.3B>
- Qwen Image Edit: <https://huggingface.co/Qwen/Qwen-Image-Edit>
- stable-diffusion.cpp runtime: <https://github.com/leejet/stable-diffusion.cpp>
- GenEval 2: <https://github.com/facebookresearch/GenEval2>
- GEditBench v2: <https://arxiv.org/abs/2603.28547>

### Regulation

- OSI Open Source AI Definition 1.0: <https://opensource.org/ai/open-source-ai-definition>
- GDPR: <https://eur-lex.europa.eu/legal-content/EN-DE/TXT/?from=EN&uri=CELEX%3A32016R0679>
- MDCG Rule 11 guidance: <https://health.ec.europa.eu/system/files/2021-10/mdcg_2021-24_en_0.pdf>
- AI Act timeline: <https://ai-act-service-desk.ec.europa.eu/en/ai-act/eu-ai-act-implementation-timeline>
