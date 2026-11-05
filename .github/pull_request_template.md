## What changed

<!-- One paragraph. What is different for a user or a caller? -->

## Why

<!-- The problem this solves. Link the issue if there is one. -->

## Evidence

Every claim in this pull request must name the command that supports it.

```text
$ .\.venv\Scripts\python.exe -m pytest
...
$ .\.venv\Scripts\python.exe -m ruff check .
All checks passed!
$ cd apps/web; npm run build
✓ built in ...
```

- [ ] Tests pass locally (paste the summary line)
- [ ] `ruff check .` is clean
- [ ] `npm run build` in `apps/web` is clean
- [ ] UI changes: verified in a browser at 375 px, 768 px and 1440 px, with console errors checked
- [ ] No personal content, prompts, tokens or model weights added to the repository

## Contract check

- [ ] No placeholder UI, dead button or mock result is presented as real
- [ ] No new model, dataset or dependency without a `licenses/manifest.yaml` entry
- [ ] Safety-relevant change? Tests added for negation, third person, quoted text and injection
- [ ] `status.md` updated if this changes what is verified
- [ ] README updated if a claim in it changed

## What is *not* established by this change

<!--
The honest part. What did you not test? Which platform, which model, which edge case?
"Nothing" is almost never the right answer.
-->
