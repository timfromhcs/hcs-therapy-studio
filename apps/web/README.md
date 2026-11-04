# `apps/web` — static local client

React 19 + Vite + TypeScript client for the local API. It is a **static** app:
it ships no server code, calls only `http://127.0.0.1:8765`, and holds no data of
its own beyond `localStorage` (token, locale, region).

## Run it

```powershell
# terminal 1 — the API
hcs-therapy serve --port 8765

# terminal 2 — this client
cd apps/web
npm install
npm run dev          # http://localhost:5173
```

Copy the token the CLI printed into **Einstellungen → API-Token** and save.

```powershell
npm run build        # type-check + production bundle into dist/
npm run preview      # serve dist/ on http://localhost:4173
```

## Design system

Installed from the Better Design catalogue: **Loam** (warm paper workspace, cream
ground, flat near-black pill controls, 1.5rem card radius, Geist). Tokens live in
`src/index.css`; components live in `src/components/ui/`.

Two deviations, both reported rather than hidden:

1. **Icons.** The Loam kit names Feather, but the icon service returned
   `AGENT_QUOTA_EXHAUSTED` for every lookup, and no Feather package was installed.
   The app uses `lucide-react`, which already ships with the kit and is the same
   geometry lineage (Lucide is a Feather fork, ISC). Swapping to Feather later is
   a one-import change.
2. **Design review.** `review-ui-code`, `get-review-rules`, `check-comprehension`
   and `inspect-spacing` could not run for the same quota reason. The screens were
   reviewed by hand against the kit's rules and verified in a real browser
   (rendered DOM, console, screenshots, 375px and 1440px). That is weaker
   evidence than the tool receipt, and it is recorded as such in `status.md`.

## What is real here

| Screen | Wired to |
|---|---|
| Übersicht | `GET /api/device/profile` — live profile, reasons, warnings |
| Gespräch | `POST /v1/chat/completions` — crisis gate, resources panel, guard badges |
| Tagebuch | `GET/POST /api/journal`, `DELETE /api/journal/{id}`, `POST /api/data/export` |
| Reflexion | `POST /api/journal` with tag `reflexion` (no model involved) |
| Studio | local scene renderer → sanitised SVG download (no model, no network) |
| Labor | `GET /api/models`, `GET /api/audit`, `GET /api/storage/usage` |
| Sicherheit | `GET /api/safety/resources` — verified numbers with source + review date |
| Einstellungen | token/region/locale, export, wipe (`POST /api/data/wipe`, confirmation required) |

## Not here

- No WebLLM/WebGPU inference (ADR-007, not started).
- No Tauri shell (ADR-008, not started).
- No server-side rendering and no remote API.
