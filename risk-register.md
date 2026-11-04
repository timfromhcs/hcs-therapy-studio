# risk-register.md

Severity is about user harm, not engineering inconvenience. Every entry has an
owner and a mitigation that is either implemented or scheduled. "Accepted" means
we ship with eyes open and say so in the README.

| id | Risk | Sev | Likelihood | Mitigation | State |
|---|---|---|---|---|---|
| R-01 | A person in crisis gets a delayed or evasive answer | High | Low | deterministic crisis gate runs before the model and bypasses it entirely; verified resource pack; tests for negation/third-party/quoted/injection | mitigated |
| R-02 | Missed crisis signal because of paraphrase, dialect or slang | High | Medium | layered patterns, conservative escalation, tests; explicitly documented as imperfect (README, known limitations); no claim of completeness | partially mitigated, accepted |
| R-03 | Assistant appears to diagnose or prescribe | High | Medium | scope prompt + output guard + fallback text + tests; deterministic fallback replaces offending output | mitigated |
| R-04 | Invented hotline number | High | Low | pack is closed; output guard rejects unrecognised service numbers | mitigated |
| R-05 | Journal or message content leaks on disk | High | Low | AES-256-GCM at rest, key file beside DB, no plaintext in SQLite | mitigated |
| R-06 | Losing the encryption key destroys journal data | Medium | Medium | documented limitation; export path exists; UI must warn before enabling | accepted, needs UI warning |
| R-07 | Over-promising VRAM causes OOM / desktop freeze | Medium | Medium | integrated-GPU heap treated as shared RAM; budget = min(heap share, safe RAM commit); profile reasons surfaced | mitigated |
| R-08 | Model output treated as therapy | High | Medium | scope label on every response, README, intended-purpose doc, no clinical claims anywhere | mitigated |
| R-09 | Prompt injection via retrieved file or imported SVG disables safety | Medium | Medium | safety layer is deterministic and outside the model; SVG rebuilt from allow-list; injection detection is recorded | mitigated |
| R-10 | Tool call escapes the sandbox | High | Low | no shell tool, path confinement, schema validation, permission gate, budgets, audit | mitigated |
| R-11 | Local API reached by another process on the machine | Medium | Low | 127.0.0.1 bind, per-launch bearer token, strict CORS allow-list | mitigated |
| R-12 | Licence violation by bundling a model or dataset | High | Low | licence manifest with verified revisions; `approved: false` blocks installation; SBOM generation | mitigated |
| R-13 | Benchmark contamination (eval data in training) | High | Low | `data leakage` command, separate directories, gating tests | mitigated |
| R-14 | Fake success reporting by the agent | High | Medium | every claim must cite a command and its output; `status.md` records unexecuted work as unexecuted | mitigated by process |
| R-15 | Smoke corpus mistaken for a therapeutic dataset | High | Medium | `engineering-smoke` status is refused by the trainer unless explicitly allowed, and marked non-promotable | mitigated |
| R-16 | German tone sounds translated | Medium | Medium | no native review yet; documented as untested | open |
| R-17 | Vulkan driver crash takes down the app | Medium | Medium | CPU fallback is a first-class profile, not an afterthought; sidecar isolation | partially mitigated |
| R-18 | Model license chain broken by a transitive component | High | Low | `components` field in manifests; Sana/Janus/PixArt rejected with reasons | mitigated for shipped set |
| R-19 | Local model produces harmful advice at scale | Medium | Medium | output guard, eval suite, no clinical claims | partially mitigated |
| R-20 | Dependency supply-chain compromise | Medium | Low | minimal dependency surface (pyyaml, cryptography), pinned lockfile, SBOM | partially mitigated |

## Reporting

Security issues: see [`SECURITY.md`](SECURITY.md). Safety issues follow the same
private-reporting path and are triaged with the same severity scale.
