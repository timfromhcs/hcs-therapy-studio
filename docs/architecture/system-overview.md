# System overview

## Layers

```
┌──────────────────────────────────────────────────────────────┐
│ UI (React, planned)          local only, no remote calls      │
├──────────────────────────────────────────────────────────────┤
│ Local API     127.0.0.1 + bearer token + CORS allow-list      │
│   /health /version /api/* /v1/models /v1/chat/completions      │
├──────────────────────────────────────────────────────────────┤
│ Safety        crisis gate → turn policy → output guard        │
├──────────────────────────────────────────────────────────────┤
│ Agent         tool registry → policy gate → budgets → audit    │
│               MCP server (stdio, JSON-RPC 2.0)                 │
├──────────────────────────────────────────────────────────────┤
│ Runtime       LlamaServer sidecar (health, logs, hard stop)    │
├──────────────────────────────────────────────────────────────┤
│ Storage       SQLite + AES-256-GCM for content, WAL, migrations│
├──────────────────────────────────────────────────────────────┤
│ Models        manifests → verified downloads → store          │
├──────────────────────────────────────────────────────────────┤
│ Hardware      CPU/RAM/disk probes + real Vulkan enumeration   │
└──────────────────────────────────────────────────────────────┘
```

## Request path for one chat turn

1. Client posts to `/v1/chat/completions` with the bearer token.
2. `Runtime.api._chat_completions` extracts the **last user message**.
3. `safety.crisis.assess()` runs the deterministic rules.
4. `safety.policy.decide()` picks one of three modes:
   - `crisis_imminent` / `crisis_supportive` → **the model is never called**; a
     reviewed template with verified numbers is returned; tool use is blocked.
   - `normal` → continue.
5. The system prompt (scope contract) is prepended; the request is forwarded to
   the loopback `llama-server`.
6. `safety.policy.scan_output()` inspects the answer for diagnostic claims,
   medication advice, false certainty, dependence language and invented service
   numbers. On a hit, a safe fallback replaces the text and the event is audited.
7. An audit row records mode, character count and guard status — never content.

## Invariants

- No component imports torch except the optional training extra.
- No network call carries user content. Model downloads are user-initiated and
  hash-verified; they contain no user data.
- The safety layer never depends on model output to decide whether to be safe.
- Every profile decision prints its numbers; a decision without reasons is a bug.
- Audit rows are metadata only, enforced by the shape of `Database.audit()`.

## Module map

| Module | Responsibility |
|---|---|
| `hardware.py` | OS/CPU/RAM/GPU/Vulkan probes; degrades, never raises |
| `profiles.py` | budget math, context selection, profile decision with reasons |
| `models/manifest.py` | strict manifest schema (pinned revision, licence allow-list) |
| `models/downloader.py` | resumable HTTPS download, atomic promotion, checksum |
| `models/store.py` | install/verify/list/remove with recorded state |
| `runtime/llama_server.py` | process supervision, readiness, guaranteed stop |
| `runtime/api.py` | loopback HTTP API, auth, CORS, confirmation gate |
| `safety/crisis.py` | deterministic crisis detection |
| `safety/resources.py` | verified regional resource pack |
| `safety/policy.py` | turn policy, scope prompt, output guard |
| `storage.py` | SQLite, migrations, encryption, export/delete |
| `agent/tools.py` | tool registry + schema validation + local safe tools |
| `agent/policy.py` | permission decisions, budgets, audit |
| `agent/mcp_server.py` | stdio MCP transport |
| `datasets.py` | provenance, PII, dedup, review gating, leakage |
| `evals.py` | local suite, scorers, reports, regression compare |
| `svg.py` | SVG sanitiser + constrained scene renderer |
| `licensing.py` | attribution and SBOM generation |
