# Feature parity matrix

Updated 2026-11-04. A feature appears here only after it exists somewhere. "—"
means not implemented; there is no aspirational column.

| Feature | Desktop (Tauri) | Browser WebGPU | Browser WASM | Model needed | Network | Notes |
|---|---|---|---|---|---|---|
| Local text inference | **verified**: 100/100 gens, CPU 16.6 tok/s, Vulkan 27.4 tok/s | — | — | Qwen3-1.7B Q8_0 GGUF | none after install | `docs/benchmarks/m1-runtime-gate.md` |
| Crisis gate + verified resources | implemented (API + UI) | — | — | none (deterministic) | none | runs before the model |
| Scope prompt + output guard | implemented (API + UI) | — | — | none | none | |
| Journal (encrypted) | implemented (API + UI) | — | — | none | none | UI not built |
| Export / delete personal data | implemented (API + UI) | — | — | none | none | |
| Tool registry + policy gate | implemented | — | — | none | none | |
| MCP server (stdio) | implemented | **not possible** | **not possible** | none | none | a page cannot spawn stdio processes; needs a local bridge |
| SVG sanitise + scene render | implemented (CLI + UI) | — | — | none for render; LLM for layout | none | UI not built |
| Local evaluation suite | implemented (CLI) | — | — | model optional (echo provider) | none | |
| Dataset gating | implemented (CLI) | — | — | none | none | |
| Model management | implemented (CLI/API) | — | — | none | download only | |
| CPU LoRA training | pipeline proven (0.6B, non-promotable) | — | — | Qwen3-1.7B-Base | none | desktop/CLI only |
| VLM (image/document) | — | — | — | Qwen3-VL-2B or SmolVLM2 | none | licence cleared, runtime unproven |
| Generative images | **not planned** | — | — | — | — | deterministic editor instead (ADR-005) |
| Installer / packaging | — | n/a | n/a | — | — | |
| Vercel static deploy | n/a | — | — | — | — | not started |

## Rules for this table

1. A feature marked "implemented" must have a test or a command in `status.md`.
2. Browser columns may not claim desktop parity for filesystem access, stdio MCP,
   model conversion or long-running training. Those are desktop/CLI capabilities.
3. "Not possible" is a legitimate entry. Hiding a platform limit is not.
