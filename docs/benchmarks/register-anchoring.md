# Register anchoring — measured A/B

Measured 2026-11-04 on the development machine. This document exists because
`status.md` carried this limitation from M1 onwards:

> the 1.7B model mixed German `du` and `Sie` inside one answer, and appended an
> emoji. The output guard does not catch register.

Both halves of that sentence are now measurable, and one of them is fixed.

## Setup

| | |
|---|---|
| Runtime | `llama.cpp` b12102 |
| Model | `qwen3-1.7b-gguf-q8-0` (sha256 `061b54da…cb1a`) |
| Backend | Vulkan, `VULKAN_BALANCED` |
| Decoding | `temperature 0.4`, `max_tokens 220`, reasoning phase off |
| Prompts | 5 (2 informal, 2 formal, 1 with no address form) × 3 repeats = **n = 15 per arm** |
| Arms | `register_anchor` on (default) vs off (`hcs.no_register_anchor: true`) |

Commands:

```powershell
hcs-therapy serve --port 8765 --start-backend
.\.venv\Scripts\python.exe scripts\bench\register_anchoring.py --ab --repeat 3
```

## Result

| Arm | n | mixed `du`/`Sie` in one answer | wrong register |
|---|---|---|---|
| anchored (shipped default) | 15 | **0** | **0** |
| unanchored | 15 | 0 | **6** |

The failure mode without anchoring is not random mixing. It is a consistent
default: the model answers every German prompt in `du`, including the four whose
prompt used `Sie`. Four of the six failures are exactly that:

```
expected=sie  detected=du  du=14 sie=0
  "Es ist verständlich, dass du dich vor der Prüfung unsicher fühlst. …"
expected=sie  detected=du  du=6  sie=0
  "Natürlich, das ist eine gute Frage. Abends ist der Körper und der Geist oft am r…"
```

With anchoring, all four formal prompts were answered in `Sie` and both informal
prompts in `du`, in every repeat.

## What this does *not* establish

- **n = 15 per arm is small.** It is enough to see a 6-of-15 failure disappear; it
  is not enough to quote a rate. A larger run is the honest next step, and the
  script takes `--repeat N`.
- **These are five hand-written prompts, not a benchmark.** They measure register
  compliance, nothing else — not empathy, not safety, not accuracy.
- **Mixing did not reproduce in this run** (0/30 across both arms). It was observed
  in an earlier session, and the mechanism is plausible — but a defect that does
  not reproduce is not a defect that is proven fixed. The detector exists so that
  if it happens again it appears in the payload and the suite instead of in a
  paragraph nobody re-reads.
- The emoji problem is now scored (`score_no_emoji`) but was not re-measured here.

## How the detector decides

`Sie` (formal you) is capitalised mid-sentence; lowercase `sie` means *she* or
*they*. A tokeniser that lowercases first destroys the signal, so this one does not.

A sentence-initial `Sie` is genuinely ambiguous (`Sie hat` = she has, `Sie haben` =
you have), so it is resolved by the **following verb**: formal address takes the
3rd-person plural conjugation, which is the same form as *they*; 3rd-person
singular can only be *she*. Irregular auxiliaries (`sind`/`ist`, `haben`/`hat`,
`werden`/`wird`) are listed explicitly because morphology alone cannot resolve them.
Anything else stays ambiguous rather than being guessed.

## Why the reply is never rewritten

German formal and informal differ in verb conjugation, not only in pronouns:

```
du  kannst / fühlst / hast
Sie können  / fühlen / haben
```

A pronoun substitution would produce grammatically wrong German — worse than the
wrong register it was meant to fix. So the product **anchors before generation**
and **reports after**, and the UI shows a badge when an answer broke the anchor.
