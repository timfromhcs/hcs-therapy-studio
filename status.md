# status.md — verified state

Last updated: 2026-11-04 (third session). This file records what was **executed**, not what
was intended. If a claim here has no command, it is wrong.

## Environment (measured)

| Item | Value | How |
|---|---|---|
| OS | Windows 11 Pro 10.0.26200 | `Win32_OperatingSystem` |
| CPU | AMD Ryzen 7 7735HS, 8C/16T, sse2/avx/avx2 | `hcs-therapy doctor --json` |
| RAM | 19.79 GiB total; 4.7–8.4 GiB free during the session | same |
| GPU | AMD Radeon(TM) Graphics, integrated, driver 32.0.21043.12001 | Win32_VideoController |
| Vulkan | 1 device: AMD Radeon(TM) Graphics, integrated-gpu, Vulkan 1.4.315, 9.35 GiB shared device-local heap | `probe_vulkan()` |
| Python (app) | 3.14.6 in `.venv`; numpy 2.5.4; training extras torch 2.15.0+cpu, transformers 5.22.1, peft 0.21.2, trl 1.17.1, datasets 5.1.0 | `import` check, `train smoke --json → versions` |
| Node | 22.23.1; Vite 8; React 19 | `npm run build` |

## Test suite

```
$ .\.venv\Scripts\python.exe -m pytest
539 passed in 50.98s

$ .\.venv\Scripts\python.exe -m ruff check .
All checks passed!

$ npm run build   (apps/web)
tsc -b && vite build → built, ~464 kB js / ~143 kB css

$ cd packages/sdk-ts; npm pack --dry-run
14 files, 10.2 kB tarball, 36.3 kB unpacked, no sources, no dependencies

$ pwsh -File scripts/verify/wheel_install.ps1
wheel verified: builds, checks, installs clean, and every entry point runs.   (exit 0)
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
| `test_evals_stats.py` | 17 | bootstrap CIs, paired significance, BT ranking, calibration |
| `test_svg.py` | 17 | sanitisation, escaping, scene validation |
| `test_cli_io.py` | 5 | BOM-prefixed reports, non-unicode console, calibration CLI |
| `test_train.py` | 11 | memory estimate, geometry resolution, data gating, plan serialisation |
| `test_knowledge.py` | 31 | chunking, hybrid retrieval, MMR, citations, encrypted index |
| `test_streaming.py` | 10 | SSE framing, crisis-before-token, dead backend, meta trailer |
| `test_region_consistency.py` | 7 | region/language of the crisis message match the UI |
| `test_numerics_*.py` | 216 | every formula against an analytically known value |
| `test_register.py` | 26 | `du`/`Sie` detection incl. verb-number disambiguation, anchoring |
| `test_register_anchoring.py` | 7 | the anchor reaches the prompt, can be switched off for A/B |
| `test_eval_register.py` | 13 | register and emoji as scored eval dimensions |
| `test_trajectories.py` | 20 | multi-turn crisis ordering and the attentiveness window |
| `test_attentive.py` | 5 | the carry-over reaches the prompt and cannot weaken the gate |
| `test_packaging.py` | 6 | declared dependencies cover what the package imports |
| `test_cli.py` | 23 | exit codes and JSON contracts, generation without dirtying the checkout |
| `test_readme_links.py` | 8 | README links resolve, diagrams parse as XML, unbuilt work stays named |
| `test_sdk_package.py` | 6 | the TS SDK builds, declares types, packs without sources or dependencies |

## New this session #4 - SDK, diagrams, README, publication (measured)

```
$ cd packages/sdk-ts; npm run build && npm pack --dry-run
dist/index.js 455 B · dist/index.d.ts 557 B · 14 files · 10.2 kB tarball
$ .\.venv\Scripts\python.exe -m pytest tests/test_sdk_package.py
6 passed
```

| Item | State | Evidence |
|---|---|---|
| `@hcsmedia/therapy-sdk` | builds, packs, zero deps, no Node built-ins | `npm pack --dry-run`, `test_sdk_package.py` |
| Four diagrams (`assets/diagram-*.svg`) | render, parse as XML, carry `aria-label` | Chromium screenshots, `test_readme_links.py` |
| README rebuilt | logo, banner, gallery, evidence map | `test_readme_links.py`, rendered on GitHub after push |
| Offline banner in the client | shown only when `/health` fails | Chromium: route-aborted `/health` → banner + no overflow; unblocked → banner absent |

The banner matters for the hosted build: a static page opened without the local studio used to
show a red "Nicht verbunden" chip and nothing else. It now explains the situation and prints
the command, which is the difference between "broken" and "not started yet".

## Milestones

| Milestone | State | Evidence |
|---|---|---|
| M0 Repository/research freeze | **done** | licence register with verified SHAs, 9 ADRs, safety/privacy docs |
| M1 Native LLM runtime | **gate PASSED (measured)** | 200/200 generations on CPU + Vulkan, hashes verified, `docs/benchmarks/m1-runtime-gate.md` |
| M2 Evaluation harness | **done (local only)** | deterministic suite, v2 report schema, CIs, paired p-values, BT ranking, calibration |
| M3 Dataset pipeline | **done (gating)** | `data validate` → ok, 10 smoke rows, 0 trainable, 0 leaks, 0 PII |
| M4 CPU LoRA training | **pipeline proven, not a quality result** | 10-step and 13-step runs executed; resume from checkpoint-10 verified |
| M5 Safety layers | **done (deterministic) + region/language consistency** | crisis/policy tests, browser-verified crisis path, `test_region_consistency.py` |
| M6 Agent + MCP | **done**, knowledge tool now real | MCP stdio roundtrip test; `search_local_knowledge_base` uses the BM25 index |
| M7 VLM + graphics | **graphics partial** | SVG sanitiser + scene renderer + Studio screen; VLM runtime unproven |
| M8 Product UI | **done, streamed and re-verified** | 8 screens, SSE streaming, command palette, 0 console errors, 0 overflow at 3 widths |
| M9 Browser edition | **not started** | no WebLLM/WebGPU |
| M10 Packages/EXE | **wheel done, installers not started** | `scripts/verify/wheel_install.ps1` exit 0; no npm package, no EXE |
| M11 Publication | **blocked** | needs explicit owner authorisation; nothing was uploaded |

## New this session #2 - streaming, latency, retrieval, statistics (measured)

### First-token latency

```
$ hcs-therapy runtime bench --backend vulkan --n 5 --max-tokens 48 --json
ttft_p50_seconds 0.199 · ttft_p95_seconds 0.669 · tokens_per_second_mean 28.17 · failed 0
```

Browser, production bundle, 1440×900, after the reasoning-phase change below:

```
erste sichtbare Zeichen 0.12 s · 33.1 Token/s   (shown in the message footer)
```

**The finding that mattered:** with Qwen3's reasoning phase left at the default, the first
*visible* token arrived at **13.31 s**. The scratchpad is not a reply, so
`chat_template_kwargs.enable_thinking = false` is now set for the conversational path
(`ServerConfig.thinking`, default `False`). 13.31 s → 0.12 s. Report:
`docs/benchmarks/m4-first-token-latency.md`.

## New this session #3 - register anchoring and packaging (measured)

### German address register — the M1 limitation, closed and measured

`status.md` carried this from M1: *"the 1.7B model mixed German `du` and `Sie` inside one
answer … the output guard does not catch register."*

```
$ .\.venv\Scripts\python.exe scripts\bench\register_anchoring.py --ab --repeat 3
n=15 pro Arm. Anrede gewechselt: 0 mit Anker, 0 ohne.
Falsche Anrede: 0 mit Anker, 6 ohne.
```

| Arm | n | mixed `du`/`Sie` | wrong register |
|---|---|---|---|
| anchored (shipped default) | 15 | 0 | **0** |
| unanchored (`hcs.no_register_anchor`) | 15 | 0 | **6** |

The unanchored failure is not random mixing, it is a consistent default: the model answers
every German prompt in `du`, including the four whose prompt used `Sie`. Full method, samples
and the n=15 caveat: `docs/benchmarks/register-anchoring.md`.

Detection detail that took a real bug to get right: `Sie` is formal only when capitalised
mid-sentence, and a sentence-initial `Sie` is resolved by the **following verb**
(`Sie können` = formal, `Sie kann` = she). The first implementation searched a three-character
slice with a pattern starting in `^`, which matched every slice and silently classified every
`Sie` as ambiguous — the detector looked correct and did nothing.

### Packaging — wheel builds, checks, installs clean

```
$ .\.venv\Scripts\python.exe -m build            → sdist + wheel
$ .\.venv\Scripts\python.exe -m twine check dist/*  → PASSED (both)
$ pwsh -File scripts/verify/wheel_install.ps1     → exit 0
  6 packages installed: cffi, cryptography, hcs-therapy-core, numpy, pycparser, pyyaml
  CLI starts · doctor reports this machine · kb index+search work · safety gate fires ·
  eval suites registered · hcs-therapy-mcp entry point present
```

Defect the clean-venv install found and nothing else could: **`numpy` was imported by the
package and declared in no dependency group.** The wheel installed fine and then
`hcs-therapy kb index` died with `ModuleNotFoundError`. The dev venv happened to have numpy,
so no source-tree test could see it. Fixed in `pyproject.toml` and guarded by
`tests/test_packaging.py`, which checks that every third-party import is declared and that the
core runtime needs no training extra.

### Retrieval

```
$ hcs-therapy kb index docs/safety/intended-purpose.md docs/privacy/data-flow.md \
                   docs/architecture/local-inference.md
$ hcs-therapy kb search "Notfallnummern" --k 2 --json
[#9] intended-purpose  score=1.0       rank_word none  rank_trigram #1
[#5] intended-purpose  score=0.983871  rank_word none  rank_trigram #2
```

`rank_word: none` is the point of the design: the query "Notfallnummern" shares **no word** with
"Notfallnummern im Notfall …", because the document says "Notfallnummer" and the query is
plural. Only the character-trigram scorer found it, and RRF fused it in. That is the compound
bridging working end to end through the CLI, not in a unit test.

API payload is explicit that this is lexical:

```
$ curl /api/knowledge/stats
"retriever": "bm25-word + bm25-trigram, fused with RRF, diversified with MMR",
"vector_index": null,
"note": "lexical only: no embedding model is installed in this build, so this is not a dense/vector index"
```

### Evaluation statistics

```
$ hcs-therapy eval run --suite hcs-core --provider echo --json     (twice)
$ hcs-therapy eval rank --reports r1.json r2.json --json
ranking[0] overall 0.75  overall_ci [0.5667, 0.9333]  checks 10
dimensions_compared 6 · caveat: "Dimension-level wins are coarse: ... a per-dimension
interval is absent below five checks in that dimension, and where it is absent the order is
a hypothesis, not a result."
```

`eval compare` now emits a paired bootstrap p-value per dimension when the check ids align,
and refuses to compute one when they do not (`paired_items: 0`, `verdict: insufficient_data`).

## M4 — what the training run actually showed

```
$ hcs-therapy train plan --config configs/train/cpu-lora-smoke-0_6b.yaml --json
records 10 · smoke_only true · params 596,049,920
total 2.85 GiB vs budget 3.05 GiB → can_run true

$ hcs-therapy train smoke --config ... --json
run_20261104-100359_2833e1 · 10 steps · 86.8 s · ~8 s/step
loss 4.61 → 3.74 · grad_norm 2.35 → 1.73
checkpoint-5, checkpoint-10 · adapter saved

$ hcs-therapy train smoke --config ... --steps 13 --resume --json
run_20261104-101409 · resumed from checkpoint-10 → 13 steps · 28.5 s
peak_rss_gib 3.04 · losses 13 · exit 0
```

Honest reading: the **pipeline** works. It is **not** evidence of model quality — the corpus is
10 `engineering-smoke` rows, the run is `promotable: false`, and no evaluation was run on the
adapter. The 1.7B config is refused by the memory guard on this machine, correctly.

## M8 — UI verification (this session)

Chromium against the production bundle (`vite preview`, port 4173) talking to the real API on
`127.0.0.1:8765` with the real model loaded on Vulkan.

- **Streaming verified**: send → first visible character in **0.12 s**, tokens rendered
  incrementally, footer showing the measured latency and throughput, stop button present.
- **Crisis path verified**: `⚠ Sofort erreichbar Deutschland: 112 · Telefonseelsorge: 0800 111 0
  111 · …`, model bypassed, regional numbers, **no English leakage** (`hasEnglish: false`).
- **Card and message agree**: the crisis card and the crisis message now both say Germany,
  because the client region is sent as a lookup key and resolved through the verified pack table.
- **Knowledge search verified**: Lab screen → "Angst" → results rendered with citation ids,
  BM25 rank and trigram rank, plus the honest "no embedding model" note.
- **Command palette**: `Ctrl+K` opens it, typing "Sich" filters to 2 entries, `Esc` closes.
- **Overflow**: `scrollWidth === clientWidth` on all 8 screens at 375, 768 and 1440 px.
- **Console errors: 0.**
- Screenshots: `docs/screenshots/ui-{home,chat,chat-crisis,journal,reflection,studio,lab,safety,
  settings}-desktop.png`, `ui-{home,chat,journal}-mobile.png`, `ui-home-dark.png`.

Bugs found **by** the browser check and fixed this session:

1. The shipped client was the Vite scaffold: `<title>vite-app</title>`, `vite.svg` favicon,
   `lang="en"` on a German-default app, no CSP. Now the product mark, `lang` from the detected
   locale, and a CSP that forbids remote origins.
2. The crisis *message* was German while the crisis *card* was regional — or the message fell
   back to the unknown-region template because the server ignored the client's region. Both are
   fixed and tested (`test_region_consistency.py`).
3. The unknown-region fallback printed an **English** line inside a German answer.
4. The keyboard hint rendered as `Shift+Enter = —`.
5. `text-pop-red-ink/80` measured 4.26:1 — below the AA floor for 12 px text.
6. The destructive fill measured 3.80:1 in light and 3.08:1 in dark. Both darkened.

**Not run:** `review-ui-code`, `get-review-rules`, `check-comprehension`, `inspect-spacing`,
`finalize-dashboard-review`, `inspect-spacing`. The Better Design account still returns
`AGENT_QUOTA_EXHAUSTED` (25 free queries used). The UI review is source-level plus
rendered-browser measurement, **not** the tool receipt. Details and the measurement
limitations: `docs/a11y-audit.md`.

## M1 — measured runtime results

Artifacts: `llama.cpp` b12102 (commit `bbb02c93…f9a7`, archive sha256 `b322f7d6…de08`), model
`Qwen3-1.7B-Q8_0.gguf` (sha256 `061b54da…cb1a`, 1,834,426,016 bytes, Apache-2.0, revision
`90862c4b…6077`).

| Check | CPU | Vulkan |
|---|---|---|
| 100 repeated generations | 100/100, **0 failures** | 100/100, **0 failures** |
| Throughput | 16.55 tok/s | 27.36 tok/s (1.65×) |
| Latency p50 (48 tok) | 2,823 ms | 1,722 ms |
| Server working set | 1.86 GiB | 2.70 GiB |
| Single-shot load | 3.18 s | 6.07 s |

Defects found and fixed during that gate are listed in the previous revision of this file; they
remain fixed and are covered by tests.

Not established by M1: answer quality, German register consistency (the model mixed *du* and
*Sie*), or any benchmark score.

## Explicitly NOT done

- No `llama-server` binary is bundled in git; it is fetched by
  `scripts/bootstrap/fetch_llama_server.ps1` and hash-pinned.
- No external benchmark (MentalHealthBench, CBT-Bench, HealthBench, BFCL, MCPMark).
- No German native-speaker review of prompts, templates or UI copy.
- No screen-reader pass (NVDA/Narrator) and no 400 % zoom reflow test.
- No Tauri shell, no installer, no wheel publication, no npm package, no Vercel deployment, no
  GitHub repository created or pushed.
- No VLM runtime; no image generation by design (ADR-005).
- No embedding model, therefore no vector index. The retriever is lexical and says so.
- No consistent-CI evidence: `.github/workflows/ci.yml` is written and mirrors the local
  commands, but it has never run anywhere, because nothing was pushed.

## Next actions

1. A reviewer-cleared training corpus so M4 can produce a promotable run.
2. A/B evaluation of the LoRA adapter against the base model on `hcs-core`, now that the
   harness reports intervals and paired p-values.
3. A larger register run (`--repeat 10`, n=50 per arm) so the 0/15 vs 6/15 result becomes a
   rate rather than a demonstration.
4. An embedding model with a cleared licence, to make retrieval genuinely hybrid rather than
   lexical-only. The RRF and MMR plumbing already accepts a third ranking.
5. A screen-reader pass and a 400 % zoom reflow check (WCAG 1.4.10).
6. `packages/sdk-ts`: a typed client published as `@hcsmedia/therapy-sdk`, plus `npm pack`
   verification. Not started; the wheel is the only installable artifact so far.
7. The Windows one-file installer (M10 remainder) and publication (M11, blocked on explicit
   authorisation).
