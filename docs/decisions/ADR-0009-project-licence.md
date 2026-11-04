# ADR-009 — Project licence and distribution model

- **Status:** accepted
- **Date:** 2026-11-04

## Context

The project ships application code plus third-party model weights. Those are two
different legal objects and must not be conflated.

## Options

| Option | Assessment |
|---|---|
| Apache-2.0 for our code, separate model licences | **chosen** |
| MIT for our code | fine, but Apache-2.0 adds an explicit patent grant, which matters for model tooling |
| GPL for our code | conflicts with the intent of permissive redistribution and with some downstream embedding |
| Call the whole release "open source AI" | inaccurate: the OSI Open Source AI Definition expects data information, training code and parameters. We do not publish the full training data. |

## Decision

- Application code: **Apache-2.0** (`LICENSE`).
- Model weights: their own upstream licences, recorded in
  `licenses/manifest.yaml` with pinned revisions and verified licence files.
  Apache-2.0 on a Qwen model is not our licence to relicense.
- README wording: "open-source application code plus permissively licensed
  open-weight components". Never "fully open source AI" unless the OSI
  definition is actually met.
- `NOTICE`, `THIRD_PARTY_NOTICES.md`, `MODEL_ATTRIBUTION.md`,
  `DATASET_ATTRIBUTION.md` and `SBOM.spdx.json` are generated from manifests, so
  they cannot drift from the shipped set.
- No upstream organisation endorses this product; each attribution says so.

## Consequences

- Adding a dependency requires a manifest entry; `license verify` fails on
  non-permissive terms for approved assets.
- Assets that fail the filter (PixArt-Sigma, CBT-Bench, ESConv, Janus, Sana) can
  be used for evaluation only where lawful, and are listed as rejected so a
  future contributor does not silently re-add them.
