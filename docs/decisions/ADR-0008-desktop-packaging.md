# ADR-008 — Desktop packaging strategy

- **Status:** proposed
- **Date:** 2026-11-04

## Context

The release target is one Windows download that installs per-user without
administrator rights, includes the runtime and the default model, and verifies
what it unpacks.

## Options

| Option | Assessment |
|---|---|
| Tauri 2 + bundled sidecar + resource bundle | **chosen direction**: small shell, Rust-side process control, official Windows installer support |
| Electron | heavier (~150 MB baseline), duplicates a Chromium runtime |
| PyInstaller one-file | convenient for the Python CLI, but extraction of a multi-GB model into a temp dir on every run is unacceptable |
| MSIX | signing requirements and per-machine policy friction |

## Decision (direction)

- Tauri 2 shell, React frontend, `llama-server` as a sidecar binary.
- The installer embeds the Q4/Q8 model pack and **streams** it out on first run to
  `%LOCALAPPDATA%\HCS\TherapyStudio`; it must not load the model into RAM during
  extraction.
- Every embedded artefact is SHA-256 verified before first load.
- Repair/upgrade/uninstall paths are part of the milestone, not an afterthought.
- Signing: no certificate is claimed. SmartScreen behaviour is documented honestly
  until a real certificate exists.

## Status

Not implemented. No installer exists, so no installation claim is made anywhere.

## Consequences

- Requires a pinned Rust toolchain and a reproducible `llama.cpp` build with
  `GGML_VULKAN=ON` plus a CPU fallback.
- The `PyInstaller` route remains available for a CLI-only distribution and is
  evaluated separately in ADR-010 if needed.
