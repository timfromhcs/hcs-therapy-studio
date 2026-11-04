# ADR-0004 — Vision-language model choice

- **Status:** deferred (licences cleared, runtime unproven)
- **Date:** 2026-11-04

## Context

The Vision Lab needs image and document understanding: description, OCR-style
extraction and visual question answering on a 20 GiB laptop with a 12-CU iGPU.

## Options

| Candidate | Licence | Revision pinned | Concern |
|---|---|---|---|
| Qwen3-VL-2B-Instruct | Apache-2.0 (verified) | `89644892…4203` | GGUF/ONNX path for the vision tower unproven; image preprocessing adds memory |
| SmolVLM2-2.2B-Instruct | Apache-2.0 (verified) | `482adb53…72e4` | smaller ecosystem for llama.cpp; video-first design is more than we need |

Both repositories were checked on 2026-11-04: licence file contents read, not
just the card badge; both ungated.

## Decision

Neither ships yet. The licence chain is approved; the *runtime* claim is not.
A VLM appears in the product only after:

1. a real export exists at a pinned commit,
2. a smoke test on this device loads it within the measured budget,
3. an OCR-ish sanity set and a POPE-style hallucination check run,
4. the UI never infers psychological state from an image.

## Consequences

- The Vision Lab screen must show "not available on this device" rather than a
  disabled button that implies future magic.
- If neither model runs inside the budget at a useful resolution, the capability
  is documented as unsupported rather than shipped half-working.

## Rollback

N/A — nothing is shipped.
