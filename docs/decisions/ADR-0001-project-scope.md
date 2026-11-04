# ADR-0001 — Project scope and intended purpose

- **Status:** accepted
- **Date:** 2026-11-04
- **Deciders:** project owner (hcsmedia)

## Context

The research pass (`RESEARCH-AND-ROADMAP.md`) defines a local-first wellbeing
platform. The same document, plus EU MDR Rule 11 and MDCG 2021-24, establishes
that a product claiming to diagnose or guide treatment becomes medical-device
software. A consumer laptop cannot host a clinically validated system, and this
project has no clinical review capacity.

## Options considered

1. **Clinical product** — requires regulatory pathway, clinical validation,
   notified body, pharmacovigilance-like incident handling. Not feasible here.
2. **Wellbeing tool with a hard non-clinical boundary** — supportive
   conversation, psychoeducation, reflection, journaling, creative work, research
   tooling. No diagnosis, no treatment.
3. **General chat front-end** — abandons the safety work, which is the main point.

## Evidence

- MDR Rule 11 and MDCG 2021-24 classify software intended to inform diagnostic or
  therapeutic decisions as medical-device software.
- MentalHealthBench, CBT-Bench and HealthBench exist precisely because general
  models are not clinically reliable; their publication is evidence that a
  consumer build must not claim clinical performance.
- The AI Act timeline (Annex III high-risk from 2027-12-02, Annex I from
  2028-08-02) means later releases must be re-checked, not assumed.

## Decision

Option 2. The product is a wellbeing and research studio. Every user-facing
surface states the boundary. Diagnosis, medication and treatment planning are
excluded by policy, by prompt, by output guard, and by tests.

## Consequences

- Marketing and README language is constrained: no "therapy", "clinical",
  "diagnosis", "treatment" claims.
- Crisis handling is mandatory and conservative, because a supportive tool will
  still be used by people in distress — saying "not a medical device" does not
  remove that duty.
- A future clinical product is a separate workstream with its own ADR.

## Rollback

If the scope must widen, the change requires: a new ADR, legal review, a clinical
review board, and removal of this document's exclusions. It cannot be done by
editing a prompt.
