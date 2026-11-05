# LONG-HORIZON-PLAN.md — autonomous execution plan

Created: 2026-11-04 · Baseline commit: `2fcfe8c` · Author of record: the agent session that
produced this file.

This plan is the working document for one long autonomous run. It is written **after**
reading the repository, running the baseline, and researching the field. Every claim in
"current state" below is backed by a command that was executed; every item in "research"
names a source; every phase has an executable acceptance gate.

`plan.md` remains the milestone board (M0…M11). This file is the *execution* plan for the
long run that follows, and it is the file to read when asking "what is being built right
now and why".

---

## Part 0 — Where the project actually stands

Measured at the start of this run:

| Check | Command | Result |
|---|---|---|
| Tests | `.\.venv\Scripts\python.exe -m pytest -q` | **225 passed** |
| Lint | `python -m ruff check .` | clean (prior run) |
| Web build | `npm run build` in `apps/web` | `tsc -b && vite build` passes |
| Git | `git status --short` | clean |
| Inference | `runtime smoke --backend vulkan` | 27.36 tok/s, 100/100 gen |
| Model | `qwen3-1.7b-gguf-q8-0` | SHA-256 verified, Apache-2.0 |
| Python | 3.14.6, numpy 2.5.4, torch 2.15.0+cpu | available |

### What exists and works

`hcs_therapy` (runtime package): hardware/Vulkan probe, compute-profile selection with RAM
budgets, hash-verified resumable model downloads, `llama-server` supervision, loopback API
with per-launch bearer token + CORS allow-list + confirmation gate, deterministic crisis
gate (EN/DE, negation/third-party/quoted/injection), verified regional resource pack,
output guard, AES-256-GCM storage, tool registry with JSON-Schema validation + policy gate +
budgets + audit, stdio MCP server, dataset gating (provenance/PII/dedup/leakage), eval
harness with A/B compare, CPU LoRA training with memory guard + checkpoint/resume, SVG
sanitiser.

`apps/web`: React 19 + Vite 8, 8 screens (Übersicht, Gespräch, Tagebuch, Reflexion, Studio,
Labor, Sicherheit, Einstellungen), DE/EN, a full shadcn-style component kit vendored under
`src/components/ui`, wired to the real loopback API, browser-verified at 375 px and 1440 px.

### The five real gaps (in priority order)

1. **No retrieval.** The model has no access to the user's own notes. `search_local_knowledge_base`
   is a declared tool but there is no index behind it. This is the single largest capability
   gap versus every comparable product.
2. **No streaming.** The UI uses the non-streaming path. Time-to-first-token is unmeasured,
   and a 1.7B model at 27 tok/s feels dead for the 3–8 s it takes to produce a paragraph.
3. **No statistics.** Evaluation produces point estimates only. There is no confidence
   interval, no significance test, no inter-rater agreement, no calibration measurement, no
   way to say "candidate B is better than baseline and that difference is not noise".
4. **No numeric toolkit.** The project asserts things about quantisation, KV-cache footprint,
   LoRA parameter counts, merging and preference optimisation without a single tested
   implementation. Those are exactly the algorithms that can be implemented from the
   published formulas and unit-tested deterministically.
5. **Presentation.** The README is honest but visually flat: no logo, no badges, no
   architecture diagram, no CI, no issue templates. It reads like a lab notebook, which
   undersells a 225-test project.

---

## Part 1 — Research: what the field does, and what is worth copying

### 1.1 Comparable products (local-first LLM applications)

| Product | Licence | What it does better than this project | Adopt? |
|---|---|---|---|
| **Jan** (jan.ai) | Apache-2.0 | One-click model hub, thread-based conversations, extension system, hybrid local/cloud switch in one conversation | Partly — model hub concept, not the cloud switch (violates local-first) |
| **LM Studio** | proprietary | Pre-download fit check ("will this run on your machine"), automatic backend pick, quantisation filter in the model browser, OpenAI-compatible server | Partly — the *fit check before download* is a real UX win and this project already has the math for it |
| **Open WebUI** | custom | Knowledge/RAG with 13 vector DBs, hybrid search, per-model prompts/tools/parameters, plugin pipeline (filters/pipes), RBAC | Partly — hybrid search + per-conversation system prompt |
| **AnythingLLM** | MIT | Document chat with workspace isolation, citation surfaces | Partly — citations |
| **Msty** | proprietary | Side-by-side model comparison, branching conversations | Partly — side-by-side eval is genuinely useful for the model lab |
| **Ollama** | MIT | `Modelfile` — declarative model configuration as text | Yes — a declarative profile/preset file is cheap and high value |
| **Unsloth** | Apache-2.0 | Training speed/VRAM claims with reproducible notebooks, export to GGUF in-app | Partly — record *how* a run is reproduced, already begun in `train.py` |

**The consistent lesson across all of them:** the differentiator is never the chat bubble.
It is (a) retrieval over the user's own material, (b) *measured* model fit and speed shown
before the user commits, and (c) never lying about what is running.

### 1.2 Research: algorithms with published formulas that this project can implement and test

Each item below is a real, cited algorithm whose implementation is deterministic and
verifiable on this machine without a GPU.

**Retrieval**

- **BM25 (Okapi)** — Robertson & Walker. `score(D,Q) = Σ IDF(qᵢ)·[tf·(k₁+1)] / [tf + k₁·(1−b+b·|D|/avgdl)]`,
  `IDF(q) = ln(1 + (N − n + 0.5)/(n + 0.5))`. Defaults k₁=1.5, b=0.75.
- **Reciprocal Rank Fusion** — Cormack, Clarke & Büttcher, SIGIR 2009. `RRF(d) = Σ_r 1/(k + rank_r(d))`,
  k = 60 (sweepable 40–80). Rank-based, so it fuses scorers with incomparable scales.
- **Maximal Marginal Relevance** — Carbonell & Goldstein, SIGIR 1998.
  `MMR = argmax_{d∈R\S} [ λ·sim(d,q) − (1−λ)·max_{s∈S} sim(d,s) ]`.
  This is the difference between "ten near-identical hits" and "five useful passages".

**Sampling and decoding**

- **Top-k** (Fan et al. 2018), **nucleus/top-p** (Holtzman et al. 2019, `Σ_{x∈V_p} p(x) ≥ p`),
  **min-p** (Nguyen et al. 2024, keep tokens with `p ≥ p_min · max_x p(x)`), **typical decoding**
  (Meister et al. 2022, keep tokens near `−log p = H(p)`).
- **Repetition / frequency / presence penalties** (Keskar et al., CTRL 2019) and
  **DRY** (don't-repeat-n-gram, llama.cpp) — implementable as a logit post-processor over a
  token history.
- **Perplexity** `PPL = exp(−(1/N) Σ log p(xᵢ | x_<ᵢ))` — the only honest way to talk about
  quantisation damage.

**Calibration and abstention**

- **Expected Calibration Error** (Naeini et al. 2015; Guo et al. 2017) with equal-mass bins,
  **Brier score**, **NLL**.
- **Temperature scaling** (Guo et al. 2017): one scalar `T` minimising NLL on held-out data;
  **Platt scaling** (Platt 1999): `σ(a·s + b)`.
- **Split conformal prediction** (Papadopoulos 2002; Angelopoulos & Bates 2023): pick the
  `⌈(n+1)(1−α)⌉`-th smallest nonconformity score as the threshold; the resulting abstention
  rule has a *finite-sample* coverage guarantee. This is the right way to decide when the
  assistant should say "I am not confident" instead of answering.

**Measurement**

- **Bradley–Terry** (Bradley & Terry 1952) via the MM algorithm (Hunter 2004) for ranking
  n candidates from pairwise wins; **Elo** (Elo 1978) as the online form.
- **Bootstrap CIs** (Efron 1979) and the **paired bootstrap test** for A/B comparisons —
  the correct answer to "is this 3-point difference real".
- **Cohen's κ** (1960) and **Fleiss' κ** (1971) for inter-rater agreement, which is what a
  clinician review protocol needs in order to mean anything.
- **pass@k** unbiased estimator (Chen et al. 2021, Codex): `1 − C(n−c, k)/C(n, k)`.

**Model numerics**

- **GGUF block quantisation sizes** — Q4_0 (32 weights → 1 fp16 scale + 16 bytes = 4.5 bpw),
  Q4_K/Q5_K super-blocks (256 weights → 12/16 bytes of scales+mins + 128/160 bytes of quants),
  Q8_0 (8.5 bpw). Exact byte accounting, no guessing.
- **KV-cache bytes per token** `= 2 · n_layers · n_kv_heads · head_dim · bytes_per_element`
  (NVIDIA inference-optimisation reference formula) — the number the profile selector already
  depends on.
- **LoRA parameter count** `= Σ_modules rank · (d_in + d_out)` (Hu et al. 2021), plus the
  trainable-memory implication.
- **DoRA** (Liu et al., ICML 2024) weight decomposition `W = m · (W₀ + BA)/‖W₀ + BA‖_c`.

**Alignment losses** (all implementable in torch and unit-testable against hand-computed values)

- **DPO** (Rafailov et al. 2023): `−log σ(β·[(log π_θ(y_w|x) − log π_ref(y_w|x)) − (log π_θ(y_l|x) − log π_ref(y_l|x))])`
- **IPO** (Azar et al. 2024): squared-difference form.
- **ORPO** (Hong et al. 2024): `L_SFT + λ·L_OR` with odds-ratio penalty.
- **SimPO** (Meng et al. 2024): reference-free, length-normalised log-prob with target margin γ.
- **CPO** (Xu et al. 2024): SFT + a simplex-constrained preference term.

**Merging**

- **SLERP** (Shoemake 1985) for two-checkpoint interpolation.
- **TIES-Merging** (Yadav et al., NeurIPS 2023): trim to top-k% magnitude, elect sign by
  mass, disjoint mean.
- **DARE** (Yu et al. 2024): random drop of delta parameters then rescale by `1/(1−p)`.
- **Task vectors** (Ilharco et al. 2022): `τ = θ_ft − θ_base`.

### 1.3 Research: what good mental-health-AI evaluation looks like in 2026

- **"Between Help and Harm" (arXiv 2509.24857)** — crisis handling must be scored on
  *conversation trajectories*, not single turns. Adopt: the eval harness measures the
  multi-turn crisis path, not just the first reply.
- **K-Bench (arXiv 2609.15855)** — clinically calibrated benchmark for high-risk conversations;
  calibration and risk-stratified scoring rather than one aggregate score. Adopt: report
  per-dimension scores with intervals, never a single "therapy quality" number (already the
  project's rule; now enforced numerically).
- **"Mental Health AI Safety Claims Must Preserve Temporal Evidence" (arXiv 2605.08827)** —
  a safety claim without the timestamped evidence of the run is not a claim. Adopt: every
  report carries commit, dirty flag, model hash and per-check timings (already present) and
  now also intervals and sample sizes.
- **Expert-evaluation limits (arXiv 2601.18061)** — human raters disagree; report agreement.
  Adopt: Cohen's/Fleiss' κ in the human-review protocol.

### 1.4 Research: README and repository presentation

From `matiassingers/awesome-readme` and the GitHub Mermaid docs, the pattern that recurs in
the top examples:

1. **Hero block**: logo/banner, one-line what-it-is, 3–6 honest badges, links to docs/demo.
2. **Table of contents** for anything over ~150 lines.
3. **A real screenshot early**, not at the bottom.
4. **Architecture diagram** — Mermaid renders natively on GitHub; no external image needed.
5. **Feature table with state** (implemented / experimental / not built) — the honest version
   of "features". This project already does this; keep it and link every row to evidence.
6. **Quickstart that a stranger can run in under two minutes**, with copy-paste blocks.
7. **Measured numbers, with the command that produced them.**
8. **Limitations section that a reviewer believes.**
9. **Contributing, security, licence, attribution** — separate files, linked.
10. **Star history / contributor graphics** only when they are real.

Badges that would lie are worse than no badges. Every badge added in this run is either
static text derived from a measured fact, or a shields.io endpoint whose value the repo
actually produces.

### 1.5 Research: UI/UX for calm, clinical-adjacent products

Synthesis of the design guidance already loaded in this repository (Better Design, WCAG 2.2
AA) plus what the comparable products get right:

- **Reading width beats screen width.** A support conversation should be a ~68-character
  column with the rest of the window used for context, not a full-bleed wall of text.
- **Streaming with a visible caret** is the single strongest perceived-performance
  improvement in every local-LLM app. It also makes latency honest.
- **Never disable the stop button.** A local 1.7B model on an iGPU can take 20 s; the user
  must be able to abort, and aborting must not corrupt the transcript.
- **Show the machine's state truthfully**: tokens/s, first-token latency, context used,
  backend. This project already has the numbers; the UI does not show them.
- **Colour is never the only signal** (WCAG 1.4.1). Crisis state gets an icon and text.
- **Motion respects `prefers-reduced-motion`** (WCAG 2.3.3).
- **Every destructive action is two-step** and says what will be deleted, in the user's
  language.
- **Keyboard-first**: `Ctrl/Cmd+Enter` send, `Esc` stop, `Ctrl/Cmd+K` command palette.

---

## Part 2 — Phases

Each phase has: goal, deliverables, acceptance gate (a command with a pass condition), and
the artefacts it must leave behind. A phase that fails its gate is reverted, not papered
over. Maximum 3 repair cycles per defect, per `AGENTS.md` §15.2.

### Phase 1 — `hcs_therapy.numerics` (the algorithm library)

**Goal:** implement the cited formulas above as small, pure, tested functions. No network,
no GPU, no model required.

**Deliverables** (in `python/hcs_therapy/numerics/`):

| Module | Contents |
|---|---|
| `retrieval.py` | tokeniser (unicode + German compound folding), inverted index, BM25 (k₁,b), character-trigram index, RRF fusion (k=60), MMR (λ), token-set dedup |
| `sampling.py` | temperature, top-k, top-p, min-p, typical-p, repetition/frequency/presence penalty, DRY n-gram, seeded categorical draw, `perplexity()` |
| `calibration.py` | equal-mass ECE, Brier, NLL, temperature scaling (fit + apply), Platt scaling, split-conformal threshold + coverage |
| `rating.py` | Bradley–Terry MM fit, Elo update, percentile bootstrap CI, paired bootstrap p-value |
| `metrics.py` | Cohen κ, Fleiss κ, macro-F1, MRR, NDCG@k, pass@k |
| `quant.py` | GGUF block-size estimator (Q4_0/Q4_K/Q5_K/Q8_0), KV bytes/token, LoRA parameter count, DoRA note |
| `merge.py` | SLERP, TIES (trim/elect/disjoint-mean), DARE, task vectors — element-wise on arrays |
| `alignment.py` | DPO, IPO, ORPO, SimPO, CPO losses in torch + a GRPO-style group advantage |

**Gate:** `pytest tests/test_numerics_*.py` — every formula verified against a
hand-computed or analytically-known value (e.g. uniform distribution ⇒ PPL = |V|;
RRF scores reproduced by hand; conformal coverage ≥ 1−α on 2000 synthetic draws;
Bradley–Terry recovers the generating strengths within tolerance; SLERP at t=0/1 is the
identity).

### Phase 2 — Retrieval in the product (real knowledge base)

**Goal:** make `search_local_knowledge_base` real.

**Deliverables:**
- `python/hcs_therapy/knowledge.py`: chunker (sentence-boundary, overlap), index persisted in
  SQLite, **two real scorers** (BM25 over words, BM25 over character trigrams — honest naming:
  this is *lexical hybrid*, not dense/vector), RRF fusion, MMR diversification, citation ids.
- API: `GET /api/knowledge/stats`, `GET /api/knowledge/search?q=…&k=…&lambda=…`,
  `POST /api/knowledge/reindex`, and `POST /v1/chat/completions` with `hcs.use_knowledge: true`
  injecting the top passages plus an instruction to cite `[#id]`, and a post-check that any
  `[#id]` in the answer exists in the injected set (hallucinated citation ⇒ flagged).
- CLI: `hcs-therapy kb index | search | stats`.
- UI: Labor screen gains a retrieval playground showing BM25-only / trigram-only / RRF / MMR
  side by side, with real scores.
- Tests: indexing, ranking monotonicity, German compound query, empty index, citation
  validation, injection rejection of an oversized document.

**Gate:** `pytest tests/test_knowledge.py` + a real `kb search` against the repo's own docs,
with the ranking printed and inspected.

### Phase 3 — Statistics in the evaluation harness

**Goal:** every number the harness reports carries uncertainty.

**Deliverables:**
- `evals.py`: report schema v2 — per-dimension mean, bootstrap 95 % CI (1000 resamples,
  seeded), n; `rank_report()` producing Bradley–Terry strengths + order + CI from ≥2 reports;
  `calibrate_report()` producing ECE before/after temperature scaling when a calibrated
  scorer is present.
- CLI: `eval rank --reports a.json b.json …`, `eval calibrate --report r.json`.
- Docs: `docs/benchmarks/report-schema-v2.md`.
- Tests: CI width shrinks with n, ranking recovers a planted order, calibration reduces ECE.

**Gate:** `pytest tests/test_evals_stats.py` and a live `eval run --provider echo` that
writes a v2 report with intervals.

### Phase 4 — Streaming and first-token latency

**Goal:** the perceived speed problem.

**Deliverables:**
- API: `stream: true` → SSE (`text/event-stream`), chunked, with the crisis gate still
  evaluated **before** the first byte; `hcs` trailer event carrying policy meta, TTFT and
  tokens/s. Non-streaming path unchanged.
- `llama_server` client: streaming proxy helper with abort support.
- CLI: `runtime bench --stream --n 5` measuring TTFT p50/p95 and tok/s.
- Web: `api.chatStream()` using `fetch` + `ReadableStream`; chat screen renders tokens as
  they arrive, with a stop button wired to `AbortController`.
- Tests: SSE framing, abort mid-stream leaves no dangling state, crisis gate fires before
  any token, trailer meta present.

**Gate:** `pytest tests/test_streaming.py` + `runtime bench --stream` on the real Vulkan
backend with TTFT recorded in `status.md`.

### Phase 5 — UI/UX overhaul

**Goal:** the interface should look like the project it is.

**Deliverables:**
- Chat: streaming, stop, regenerate, copy, safe markdown-lite renderer (bold/italic/code/list,
  no HTML), latency + token footer, `aria-live` region, keyboard shortcuts.
- Home: live measured tiles (backend, tok/s, context, RAM headroom) drawn from real endpoints,
  with a sparkline of the local performance log.
- Labor: retrieval playground (Phase 2) + evaluation ranking table + calibration chart.
- Shell: command palette (`Ctrl/Cmd+K`), skip-link, focus-visible ring, reduced-motion, mobile
  drawer that traps focus.
- A11y: contrast pass on every token pair used, `aria-label` on every icon-only control,
  documented in `docs/a11y-audit.md` with the measured ratios.
- Screenshots regenerated at 375 / 768 / 1440 for every screen.

**Gate:** `npm run build` clean, Playwright run that loads all screens at 3 widths, asserts
`scrollWidth === clientWidth`, captures screenshots, and reads zero console errors.

### Phase 6 — Presentation: README, assets, CI, templates

**Deliverables:**
- `assets/logo.svg` + `assets/banner.svg` authored in-repo (no third-party art, clean licence).
- `README.md` rewritten to the pattern in §1.4: hero, badges, TOC, screenshot, feature matrix
  with evidence links, Mermaid architecture, quickstart, measured numbers, safety, privacy,
  limitations, repository map, contributing, licence, attribution.
- `.github/workflows/ci.yml`: ruff + pytest + `npm ci && npm run build` on push/PR.
- `.github/ISSUE_TEMPLATE/{bug,feature}.yml`, `.github/pull_request_template.md`.
- `docs/README.md` index; `docs/benchmarks/` updated.
- `CHANGELOG.md` with the real work of this run.

**Gate:** every relative link in README resolves (script check), every badge URL returns 200
or is static text, `ci.yml` parses as YAML and its commands are the ones that passed locally.

### Phase 7 — Verification and honest report

- Full `pytest`, `ruff`, `npm run build`, Playwright, `kb search`, `eval run`, `eval rank`.
- Update `status.md` with the new measured table and `plan.md` milestone notes.
- Final report in the format of `AGENTS.md` §22, including what was **not** done.

---

## Part 3 — Explicitly out of scope for this run

- No model training run beyond what already exists (no reviewer-cleared corpus exists; the
  1.7B run is refused by the memory guard on this machine, correctly).
- No external benchmark scores (licences/authorisation absent).
- No WebGPU/WebLLM browser inference (needs an MLC-compiled model; cannot be validated here).
- No VLM runtime (no proven export on this GPU).
- No installer, no PyPI/npm publication, no Vercel deploy, no GitHub push — all require
  explicit owner authorisation under `AGENTS.md` §19/§14.
- No claim of clinical efficacy, diagnosis capability or benchmark superiority anywhere.

---

## Part 4 — Risk register for this run

| Risk | Mitigation |
|---|---|
| Streaming breaks the crisis-before-model invariant | test asserts the gate runs first; SSE opens only after the gate returns |
| Retrieval injects prompt-injection text from a document | retrieved text is fenced, length-capped, and the output scanner still runs; test included |
| New numerics silently wrong | every formula tested against an analytic value, not against itself |
| UI regression while adding screens | Playwright width/no-overflow/console-error assertions per screen |
| Bootstrap CIs mislead on tiny n | n reported next to every interval; intervals suppressed below n=5 with an explicit note |
| README badge rot | prefer static shields with text derived from measured facts; CI file mirrors local commands |

---

**Made with love by hcsmedia and timfromhcs.**

---

## Part 5 — Execution log (what actually happened)

Recorded at the end of the run, against the phases above.

| Phase | State | Evidence |
|---|---|---|
| 0 Baseline freeze | done | 225 tests green, `git status` clean at `2fcfe8c` |
| 1 Numerics library | **done** | 8 modules, **216 tests**, ruff clean. Every formula checked against an analytic value (uniform ⇒ PPL = \|V\|; DPO at equal margin = log 2; SLERP endpoints exact; conformal coverage ≥ 1−α on 2000 draws; BT recovers a planted 2:1 ratio) |
| 2 Retrieval in the product | **done for the lexical layer** | 31 tests; `kb search "Notfallnummern"` returns the safety document via the trigram scorer only (`rank_word: none`, `rank_trigram: #1`); index encrypted with the journal key and tested for it |
| 3 Evaluation statistics | **done** | 17 tests; schema v2 with `overall_ci` and per-dimension `ci_low/ci_high`; paired bootstrap p-values; `eval rank`; `eval calibrate` |
| 4 Streaming + TTFT | **done** | 10 streaming tests + 7 region/language tests; `runtime bench` 0.199 s p50; browser 0.12 s first visible character |
| 5 UI/UX overhaul | **done** | build clean; 8 screens × 3 widths, 0 console errors, 0 overflow; contrast audit fixed 4 real AA violations |
| 6 Presentation | **done** | README rebuilt, logo + banner authored in-repo, CI workflow, issue/PR templates, 5 link/structure tests |
| 7 Verification | **done** | 443 tests, ruff clean, `npm run build` clean, Playwright evidence, `status.md` and `plan.md` updated |
| 8 Register anchoring *(unplanned)* | **done and measured** | n=15 per arm A/B: 0/15 wrong register anchored vs 6/15 unanchored; `docs/benchmarks/register-anchoring.md` |
| 9 Packaging *(unplanned)* | **wheel done** | `scripts/verify/wheel_install.ps1` exit 0; 6 dependencies, no torch; no publication |
| 10 Verification rerun | **done** | **505 tests**, ruff clean, npm build clean, wheel verify exit 0 |

### Deviations from the plan, and why

1. **Thinking disabled by default.** The plan assumed streaming would be the latency fix. It
   was not enough: Qwen3 spends 13.3 s in a private reasoning phase. Measured, then fixed by
   disabling the reasoning phase for conversation — a 110× improvement, and the scratchpad was
   never going to be shown anyway.
2. **A ninth phase appeared: region/language consistency.** The browser check found the crisis
   card saying "Deutschland" while the crisis *message* used the unknown-region fallback, and
   that fallback leaked an English sentence into a German answer. This was not in the plan
   because it was not visible from the source alone.
3. **No embedding model.** The plan listed "two real scorers"; it stayed lexical by design
   rather than adding a vector index with an unclear licence. The API, the UI and the README
   all say "lexical" in the same words.
4. **Better Design review tools still blocked.** `AGENT_QUOTA_EXHAUSTED` on the first call. The
   substitute is a rendered-browser contrast and structure audit whose limitations are written
   down in `docs/a11y-audit.md`, including the pairs it could not resolve.
5. **One planned item was skipped deliberately:** automated visual regression snapshots. A
   screenshot diff with no baseline reviewed by a human proves nothing, and the run had no
   human reviewer for it.

### What this run did **not** establish

No benchmark score, no quality claim, no clinically validated behaviour, no German
native-speaker review, no screen-reader pass, no installer, no published package, no
deployment. Each of those is listed in `status.md` under "Explicitly NOT done".
