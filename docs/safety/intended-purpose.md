# Intended purpose, scope and limitations

**Product:** HCS Therapy Studio
**Version:** 0.1.0 (pre-release)
**Last reviewed:** 2026-11-04

## Intended purpose

A local-first desktop and browser tool for adults who want to reflect, journal,
learn about psychological topics in general terms, and do creative or research
work — using a language model that runs on their own machine.

Supported uses:

1. **Supportive conversation** — listening, accurate paraphrase, clarifying
   questions, non-directive help.
2. **Psychoeducation** — general explanation with visible sources, uncertainty
   and a non-clinical boundary.
3. **Guided self-reflection** — thought records, needs and values exercises,
   clearly labelled as self-reflection and not as treatment.
4. **Journal** — private local notes, mood check-ins, tags, export, delete.
5. **Creative studio** — an editable SVG/layout editor and text-to-layout, not a
   generative image model.
6. **Research lab** — model management, dataset gating, evaluation, bounded
   local tools.

## Explicitly not intended

- Diagnosing any condition, including depression, ADHD, PTSD, bipolar disorder,
  personality disorders, or any other.
- Interpreting a screening questionnaire as a diagnosis.
- Recommending, starting, stopping, changing or dosing medication.
- Producing a treatment plan for an individual.
- Acting as a crisis service, emergency service, therapist, doctor, or
  replacement for any of them.
- Decisions about a person's fitness, legal status, benefits, employment,
  insurance, or access to care.
- Inferring diagnosis, personality, trauma, intent or emotional state from a
  face, voice, appearance or image.
- Training on real patient records or private user conversations.

## Regulatory position

A software product that claims to diagnose or guide treatment can be a medical
device (see EU MDR Rule 11 and MDCG 2021-24). This product does not make those
claims and is not marketed for those purposes. Any future clinical product is a
separate regulatory workstream, not a feature flag.

GDPR Article 9 treats health data as a special category. Local storage reduces
exposure; it does not by itself make every processing activity lawful. Users
control export and deletion; there is no server-side processing and no telemetry.

## Crisis behaviour

The app runs a deterministic crisis check before the model is used:

1. explicit imminent danger → the model is skipped entirely and a reviewed
   response appears with verified numbers for the user's region;
2. explicit but non-imminent signal → supportive response with the same verified
   resources, no tool calls;
3. concern about someone else → supportive response, no assumption about the
   user's own state;
4. clear negation → no escalation, but the negation is recorded so the assistant
   does not push a crisis frame onto someone who rejected it.

The app never invents a hotline, never claims to be a crisis service, never
requires a questionnaire before showing urgent resources, and never gives
procedural detail about methods.

**A rule set is not a guarantee.** Detection can miss phrasing it has not seen.
The app says so, and says so in the interface, not only in this document.

## Known limitations

- Detection quality is bounded by the patterns and tests in
  `python/hcs_therapy/safety/crisis.py`. German dialect, youth slang and heavy
  irony are under-covered.
- The shipped model is a general open-weight model with a scope prompt. It is not
  a therapeutic model and has no clinical validation of any kind.
- No external benchmark has been run against it. The local evaluation suite
  measures behaviour on this project's own prompts only.
- German tone has not been reviewed by native speakers.
- Encryption protects data at rest on a machine the user controls. It does not
  protect against a compromised operating system or a keylogger.
- Losing the content key means losing the journal entries. There is no recovery
  service, because there is no service.

## What the user is told in the interface

- The scope label on every session: "Supportive conversation · not diagnosis,
  not treatment".
- The model, backend and compute profile in use.
- Whether content is stored, and how to export or delete it.
- The verified resource panel, with its review date and source.
