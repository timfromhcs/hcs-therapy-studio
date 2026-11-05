# Changelog

All notable changes to this project. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/), with the caveat that this is pre-release software.

Every entry names the command that supports it. An entry without evidence is a rumour.

## [Unreleased]

### Added

- **`@hcsmedia/therapy-sdk`** (`packages/sdk-ts`) — the typed client for the loopback API.
  ESM with declarations, zero runtime dependencies, no Node built-ins, and every mutating
  method sends `confirmed: true`, which the server enforces rather than trusting. Checked by
  `npm pack --dry-run` (14 files, 10.2 kB unpacked 36.3 kB) and
  [`tests/test_sdk_package.py`](tests/test_sdk_package.py), which also asserts the package
  cannot have leaked `src/`, `node_modules/` or a secret into the tarball. Not published.
- **Four authored diagrams** (`assets/diagram-architecture.svg`, `-crisis-gate`, `-retrieval`,
  `-evidence-map`). Self-contained SVGs with `role="img"` and an `aria-label`, no remote font,
  image or `href`. A test parses each one as XML, because a diagram that does not parse renders
  as a broken-image icon on GitHub.
- **README rebuilt around evidence.** Logo, banner, a screenshot gallery, per-area evidence
  links, the measured-numbers tables, and an explicit "not built yet" table that names the
  missing installer, browser edition and clinician review instead of implying they exist.
- **Honest offline state in the client.** When `/health` is unreachable — which is exactly what
  a visitor to the static host sees — the shell says so, prints the command that starts the
  local studio, and states that the page only ever asks `127.0.0.1`. It disappears on its own
  when the server answers; verified both ways in Chromium.

### Changed

- **README badge and test counts are generated from a real run**, not estimated: 539 passed.
  They were updated in the same edit as the suite that produced them.

- **Multi-turn crisis trajectories** (`trajectories.py`, `hcs-therapy eval trajectories`). Six
  scripted German conversations walked through the real gate, asserting the policy mode,
  resource visibility and model bypass **per turn**, and failing with the offending turn named.
  **6/6 pass.** Measures the policy layer only — no model is called, and every report says so.
  [`docs/safety/crisis-trajectories.md`](docs/safety/crisis-trajectories.md)
- **Session-level attentiveness.** A crisis decision now marks the following three turns
  attentive, and `PolicyDecision.system_suffix` reaches the forwarded prompt so the model
  acknowledges and slows down instead of returning to small talk. The window lives on the
  client (`hcs.attentive`), can only make a turn more careful, and a test proves it cannot
  disable the gate.
- **German address-register anchoring** (`safety/register.py`). Detects `du` vs `Sie` from the
  person's own message and pins the register in the system prompt; reports the register of the
  reply in `hcs.register`, including a `mixed` flag and a `violated_anchor` flag.
  Measured A/B, n=15 per arm: **0/15 wrong register anchored vs 6/15 unanchored**
  (`docs/benchmarks/register-anchoring.md`).
- **Register and emoji as eval dimensions** (`score_register`, `score_no_emoji`) — the two
  behaviours `status.md` listed as unguarded since M1 are now scored in `hcs-core`.
- **Packaging verification** (`scripts/verify/wheel_install.ps1`): build → `twine check` →
  wheel contents → clean-venv install → CLI, `doctor`, `kb index/search`, safety gate, eval
  suites, MCP entry point. Exit 0. Nothing is published.
- **`tests/test_packaging.py`** — every third-party import must be declared, and the core
  runtime must not need a training extra.
- **Reminder process** (`scripts/ops/reminder.ps1`) — detached 30-minute checkpoint log with a
  hard deadline, deliberately not a second autostart entry (`AGENTS.md` §8.5).
- **`scripts/bench/register_anchoring.py`** and `summarise_register_ab.py` — the A/B harness
  behind the register number.

### Fixed

- **`numpy` was imported and declared nowhere.** The wheel installed cleanly and then
  `hcs-therapy kb index` crashed with `ModuleNotFoundError`; only a clean-venv install could
  see it, because the dev venv had numpy. Declared as a core dependency and guarded by a test.
- **Every sentence-initial `Sie` was classified as ambiguous.** The detector searched a
  three-character slice with a pattern beginning in `^`, which matches every slice — so the
  formal-address path was dead code that looked correct. Now resolved by the following verb
  (`Sie können` formal, `Sie kann` third person).
- **A 401 on a streaming request arrived as `ConnectionAbortedError` (WSAECONNABORTED).** The
  server answered and closed without draining the request body. `_drain_body()` now runs before
  the 401 and the 403.

- **`hcs_therapy.numerics`** — a pure, deterministic algorithm library, 216 tests, each
  anchored to an analytically known value rather than to its own output:
  BM25 (Okapi), reciprocal rank fusion (k=60), MMR (λ), character-trigram tokenisation,
  top-k/top-p/min-p/typical sampling, repetition/frequency/presence/DRY penalties,
  perplexity, ECE/Brier/NLL, temperature scaling, Platt scaling, split conformal prediction,
  Bradley–Terry (MM algorithm), Elo, percentile and paired bootstrap, Cohen κ, Fleiss κ,
  macro-F1, MRR, NDCG@k, unbiased pass@k, GGUF block-size arithmetic, KV-cache bytes/token,
  LoRA parameter counts, SLERP, TIES-Merging, DARE, task vectors, and the DPO/IPO/ORPO/SimPO/CPO
  losses with a GRPO group advantage.
  Evidence: `pytest tests/test_numerics_retrieval.py tests/test_numerics_sampling.py tests/test_numerics_calibration.py tests/test_numerics_rating.py tests/test_numerics_metrics.py tests/test_numerics_quant_merge_alignment.py`
- **Local knowledge base** (`knowledge.py`) — sentence/paragraph chunking with overlap,
  two real sparse scorers (BM25 over words, BM25 over character trigrams), RRF fusion,
  MMR diversification, token-set dedupe, citation ids, hallucinated-citation detection, and
  an index encrypted with the same AES-256-GCM key as the journal.
  Evidence: `pytest tests/test_knowledge.py`; `hcs-therapy kb search "Notfallnummern"` returns
  the safety document via the **trigram** scorer only, which is the whole point of fusing two
  lexical retrievers.
- **Streaming chat over SSE** with the crisis gate evaluated before the response opens, a
  stop button that leaves the partial answer intact, and measured first-token latency and
  tokens/second in the message footer.
  Evidence: `pytest tests/test_streaming.py`, `runtime bench --n 5`.
- **`runtime bench`** — time-to-first-token measurement on the streaming path.
  Evidence: [`docs/benchmarks/m4-first-token-latency.md`](docs/benchmarks/m4-first-token-latency.md).
- **Evaluation statistics** — bootstrap confidence intervals per dimension, a paired bootstrap
  p-value in `eval compare`, `eval rank` (Bradley–Terry across reports) and `eval calibrate`
  (ECE, Brier, NLL, temperature scaling). Report schema bumped to v2.
  Evidence: `pytest tests/test_evals_stats.py`.
- **Region and language consistency** — the crisis message now uses the region *and* the
  language the user is actually reading, instead of a server default that could disagree with
  the crisis card directly above it.
  Evidence: `pytest tests/test_region_consistency.py`.
- **UI**: real streaming with a caret and stop, copy/regenerate, safe markdown-lite renderer
  (React elements, no HTML), command palette (`Ctrl/⌘+K`), skip link, retrieval playground in
  the Lab screen, product title/favicon/CSP replacing the Vite scaffold, `aria-live` on the
  transcript.
- **Presentation**: `assets/logo.svg` and `assets/banner.svg` authored in-repo, a README
  rebuilt around the pattern that works on GitHub (hero, badges, TOC, Mermaid architecture,
  evidence-linked feature matrix, measured numbers, honest limitations), CI workflow, issue
  templates, PR template.
  Evidence: `pytest tests/test_readme_links.py`.

### Fixed

- **13.3 s to the first visible character.** `Qwen3` spends its opening tokens in a private
  reasoning stream. Disabled for conversation via `chat_template_kwargs.enable_thinking`;
  measured 13.31 s → 0.12 s.
- **English leaked into German crisis responses.** The unknown-region fallback printed
  "Local emergency services: your local emergency number" inside a German template. Both
  locales now render entirely in one language, and there is a test that greps for the leak.
- **The crisis card and the crisis message could disagree.** The card read the region from
  `localStorage`, the message from a launch flag. The client region is now accepted as a
  *lookup key*, resolved through the verified pack table so an unknown value degrades to the
  fallback instead of inventing a hotline.
- **`UnicodeEncodeError` on any non-cp1252 character.** A retrieved note containing `→`, `≥`
  or CJK crashed the CLI — the worst failure mode for a search tool, because it depends on
  what the user is searching for.
- **`eval rank`/`compare`/`calibrate` rejected PowerShell-written reports.** `Out-File
  -Encoding utf8` writes a BOM; the readers now use `utf-8-sig`.
- **The shipped client was the Vite scaffold.** `<title>vite-app</title>`, `vite.svg` as the
  favicon, `lang="en"` on a German-default app, and no CSP.
- **Retrieval ranked ASCII architecture diagrams first.** Fenced blocks over 12 lines are
  collapsed before chunking, and chunks that are mostly box-drawing are dropped.

### Changed

- `SuiteReport.to_dict()` now emits `report_schema: 2`, `overall_ci`, and per-dimension
  `ci_low`/`ci_high`/`ci_note`.
- `search_local_knowledge_base` (MCP tool) uses the real index and labels its fallback
  retriever as `substring` instead of quietly pretending to be the same thing.
- Documented: the retriever is **lexical**, not a vector index, in the API payload, the UI and
  the README.

### Not changed, deliberately

- No external benchmark score is claimed. MentalHealthBench, CBT-Bench and HealthBench need
  authorised access; none was obtained.
- No model training beyond the existing 10-step pipeline smoke run.
- No WebGPU/WebLLM edition, no VLM runtime, no installer, no package publication, no
  deployment. All of these need either hardware this project has not validated or explicit
  owner authorisation.
