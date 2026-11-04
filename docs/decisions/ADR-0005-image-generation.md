# ADR-0005 — Image generation: deliberately not shipped

- **Status:** accepted (rejection)
- **Date:** 2026-11-04

## Context

A text-to-image feature is attractive for the creative studio. The build contract
requires an approved licence chain for the weights *and* every auxiliary
component (text encoder, VAE, tokenizer), plus a real smoke test on target
hardware.

## Findings

| Candidate | Licence finding | Size | Verdict |
|---|---|---|---|
| Sana Sprint 1.6B | Apache-2.0 top level, but fixed `Gemma2-2B-IT` text encoder with separate terms; model card positions it for research | 1.6B + encoder | reject |
| Sana 1.5 1.6B | same Gemma-2 encoder dependency | 1.6B + encoder | reject |
| PixArt-Sigma | CreativeML OpenRAIL++-M — not a strict permissive licence | ~0.6B | reject |
| Janus-Pro / JanusFlow | DeepSeek Model Licence on the weights, despite MIT-looking code | 1B / 1.3B | reject |
| Qwen-Image-Edit | Apache-2.0 | 20B, ~57.7 GB repo | not feasible on device |

## Decision

Ship a **deterministic** visual capability instead:

- an SVG/canvas editor with layers, shapes, text, masks and export,
- a constrained **text-to-layout** renderer (`hcs_therapy/svg.render_scene`)
  where the model outputs a validated scene dictionary and *we* emit the SVG.

The model never emits markup. That removes the injection surface entirely and
makes the feature testable without a diffusion runtime.

## Consequences

- No photorealistic generation. This is stated in the README.
- If a model later passes the full chain (all components permissive, runtime
  proven, evaluation run), a new ADR is required — including GenEval 2 and
  GEditBench v2 results and a memory budget.

## Rollback

N/A.
