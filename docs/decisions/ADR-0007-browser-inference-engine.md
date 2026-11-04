# ADR-007 — Browser inference engine (not implemented)

- **Status:** proposed / not started
- **Date:** 2026-11-04

## Context

A static Vercel deployment must do inference in the browser. No user content may
reach a serverless function.

## Options

| Option | Assessment |
|---|---|
| WebLLM / MLC | Mature path for quantised LLM inference on WebGPU, prebuilt model libraries; **preferred when implemented** |
| Transformers.js + WebGPU | Good for small models, heavier per-token overhead for 1.7B |
| ONNX Runtime WebGPU | Useful for vision encoders, not ideal for autoregressive LLMs |
| WASM-only | Works without WebGPU but slow; acceptable only as a labelled fallback |
| Server-side inference on Vercel | **rejected** — would upload private content |

## Decision (proposal)

1. Static client; WebLLM for text, with a pinned compiled model and an integrity
   hash.
2. WASM fallback only for models where it is actually usable, and labelled as
   slower.
3. Feature detection reports adapter limits and runs a micro-benchmark; it does
   not claim to know VRAM.
4. Browser storage uses OPFS/IndexedDB with quota checks and a visible delete
   control.
5. No MCP parity: a page cannot spawn local stdio servers. A separately installed
   local bridge is required, and the UI says so.

## Status

Not implemented. Nothing is claimed. Any "browser edition" statement in the
README is explicitly marked not started.

## Consequences if implemented

- Model size limits mean the browser build may use a smaller model than the
  desktop build. The feature-parity matrix must show that difference.
- A service worker cache must be versioned and purgeable.
