# Contributing

Read [`AGENTS.md`](AGENTS.md) first. It is the build contract, not a suggestion.

## Ground rules

1. **No fabricated capability.** A feature is described as working only after a
   command proves it. `status.md` records what was executed.
2. **No clinical claims.** No diagnosis, no treatment recommendation, no
   medication guidance, no "clinically validated" wording. If a change nudges
   toward any of these, it will be rejected.
3. **Local-first.** No network call that carries user content. No telemetry, no
   analytics, no remote crash reporting.
4. **Small, reversible steps.** One concern per change. Keep the tree runnable.
5. **Tests come with the change**, not after it.

## Development setup

```powershell
uv venv --python 3.14
uv pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

## Definition of done for a change

- `pytest` green, `ruff check` clean.
- New behaviour has a test that fails without the change.
- If it touches safety, resources or the guard, the test covers the bypass
  attempt, not just the happy path.
- `status.md` updated when a milestone gate moves.
- No new dependency without a licence entry in `licenses/manifest.yaml`.

## Adding a model or dataset

1. Pin the exact commit SHA — branches are rejected by the manifest validator.
2. Verify the licence file *in the repository*, not the badge on the card.
3. Record the artefact SHA-256.
4. Add an entry to `licenses/manifest.yaml` with `approved: false` until review.
5. Add a manifest under `models/manifests/` or `datasets/manifests/`.
6. Run `hcs-therapy license verify` and `hcs-therapy license generate`.

Non-commercial, research-only and use-restricted assets do not ship. They may be
used for evaluation only, and only where that is lawful.

## Adding a tool

Tools are the highest-risk surface in the product.

- Declare the narrowest JSON Schema that does the job.
- Set the permission level honestly (`read` unless there is a real side effect).
- Confine every path to an approved root.
- Cap output size.
- Add a test proving the tool refuses an out-of-scope request.

## Commit messages

`area: what changed and why it is safe` — for example
`safety: treat quoted fiction as elevated, not imminent`.

## Code of conduct

See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
