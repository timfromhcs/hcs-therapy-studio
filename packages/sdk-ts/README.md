# `@hcsmedia/therapy-sdk`

Typed client for the [HCS Therapy Studio](../../README.md) loopback API.

The studio runs entirely on your machine. This package is the wire format and
nothing else: no model, no bundled weights, no network access of its own, no Node
built-ins. That is why it works in a browser, an editor extension, or a local
script.

```bash
npm install @hcsmedia/therapy-sdk
```

```ts
import { createClient } from "@hcsmedia/therapy-sdk"

const studio = createClient({
  token: process.env.HCS_TOKEN!, // printed by `hcs-therapy serve`
})

const { profile } = await studio.deviceProfile()
console.log(profile?.profile, profile?.context)

await studio.chatStream(
  { messages: [{ role: "user", content: "Ich schlafe schlecht." }] },
  {
    onDelta: (delta) => process.stdout.write(delta),
    onMeta: (meta) => console.error(`\n[${meta.policy_mode}] ${meta.ttft_ms} ms`),
  },
)
```

## What it exposes

| Group | Methods |
|---|---|
| Liveness | `health()` (needs no token, returns no user data), `version()` |
| Device | `deviceProfile()` — the chosen compute profile **and the reasons** |
| Models | `models()`, `storage()` |
| Privacy | `journal()`, `createJournal()`, `deleteJournal()`, `exportData()`, `wipeData()`, `audit()` |
| Safety | `resources()` — verified numbers with source and review date |
| Knowledge | `knowledgeStats()`, `knowledgeDocuments()`, `knowledgeSearch()`, `knowledgeReindex()` |
| Chat | `chat()`, `chatStream()` |

## Two contract details that surprise people

1. **Every mutating call sends `confirmed: true`.** The server rejects writes
   without it, so a stray call in a script cannot delete a journal entry. There is
   no "unsafe mode" flag.
2. **`knowledgeStats().vector_index` is always `null`.** The retriever in this
   build is lexical (BM25 over words, BM25 over character trigrams, fused with RRF,
   diversified with MMR). No embedding model is installed, and the type says so
   rather than leaving a field that implies otherwise.

## Errors

`HcsApiError.status` carries the HTTP status, so you can distinguish:

| Status | Meaning |
|---|---|
| 401 | missing or wrong token |
| 403 | a browser origin the server does not allow, or a missing confirmation |
| 400 | malformed body |
| 503 | the local model backend is not running |
| 502 | the backend answered with something unusable |

## Licence

Apache-2.0, same as the application. The SDK contains no model weights and no
third-party code. Upstream projects do not endorse this application.

Made with love by hcsmedia and timfromhcs.
