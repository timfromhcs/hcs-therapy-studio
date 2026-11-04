"""Safety policy: what the product does *around* the model.

Three responsibilities:

1. ``system_prompt`` — the scope contract handed to the model (no diagnosis, no
   medication, preserve agency, explain uncertainty).
2. ``decide`` — the deterministic gate that runs before generation, can bypass
   the model entirely, and blocks tool use during a crisis.
3. ``scan_output`` — a post-generation guard that flags diagnostic claims,
   medication advice, invented hotline numbers and dependence-fostering phrases.

Nothing here "makes the model safe" on its own. It is one layer of several, and
the test suite proves each layer fires.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import resources
from .crisis import CrisisAssessment, RiskLevel

SCOPE_LABEL_DE = "Unterstützendes Gespräch · keine Diagnose, keine Behandlung"
SCOPE_LABEL_EN = "Supportive conversation · not diagnosis, not treatment"

SYSTEM_PROMPT_CORE = """You are a supportive conversation partner inside a local-first wellbeing app.

Absolute boundaries:
- Never diagnose a mental-health or medical condition, and never use a screening
  score as a diagnosis.
- Never recommend, adjust, stop or dose medication, and never suggest a
  treatment plan for an individual.
- Never claim to be a therapist, doctor, crisis service or emergency service.
- Never infer hidden feelings, motives, trauma or diagnosis from what the person
  wrote, and never state them as fact.
- Never pressure, shame, moralise, flatter excessively, or encourage dependence
  on the assistant.
- Do not present retrieved educational text or your own output as professional
  advice; keep sources visible.

Working style:
- Ask one useful question before assuming context.
- Reflect what was actually said; do not invent history.
- Validate the experience without endorsing a harmful belief or a conclusion the
  person has not verified.
- Preserve agency: offer options, never coercive instructions or commands.
- Prefer concrete, small next steps over generic reassurance.
- Name uncertainty plainly and say when something needs a professional.
- Keep answers concise. Do not pad, do not perform empathy as a script.

Crisis rule: if there is any indication of imminent danger to the person or
someone else, put safety first, keep it short, encourage contacting local
emergency services or a trusted person, and do not stall with exercises or tool
calls."""

CRISIS_IMMINENT_DE = (
    "Ich nehme das ernst, was du gerade geschrieben hast — und ich möchte, dass du "
    "jetzt nicht allein damit bleibst.\n\n"
    "Bitte wende dich sofort an eine dieser Stellen:\n\n{resources}\n\n"
    "Wenn du gerade in akuter Gefahr bist, ruf den Notruf an oder bitte eine Person "
    "in deiner Nähe, bei dir zu bleiben. Ich kann keine Hilfe zu dir schicken und "
    "kein Krisendienst sein.\n\n"
    "Eine Frage, damit ich dich nicht falsch verstehe: bist du gerade in "
    "unmittelbarer Gefahr?"
)

CRISIS_IMMINENT_EN = (
    "I'm taking what you wrote seriously, and I don't want you to sit with it alone "
    "right now.\n\n"
    "Please contact one of these now:\n\n{resources}\n\n"
    "If you are in immediate danger, call your local emergency number or ask someone "
    "near you to stay with you. I can't send help to you, and I'm not a crisis "
    "service.\n\n"
    "One question so I don't misunderstand you: are you in immediate danger right now?"
)

CRISIS_SUPPORTIVE_DE = (
    "Danke, dass du das schreibst. Das klingt schwer, und ich nehme es ernst.\n\n"
    "Ich möchte dich nicht mit Übungen aufhalten. Wenn es akut wird, sind hier "
    "Stellen, die rund um die Uhr erreichbar sind:\n\n{resources}\n\n"
    "Magst du mir sagen, wie es dir in den letzten Stunden ergangen ist — und ob du "
    "gerade jemanden bei dir hast?"
)

CRISIS_SUPPORTIVE_EN = (
    "Thank you for telling me. That sounds heavy, and I take it seriously.\n\n"
    "I don't want to hold you up with exercises. If it escalates, these are reachable "
    "around the clock:\n\n{resources}\n\n"
    "Could you tell me how the last few hours have been — and whether anyone is with "
    "you right now?"
)

THIRD_PERSON_DE = (
    "Es klingt, als machst du dir Sorgen um jemand anderen — das ist belastend.\n\n"
    "Wenn dort gerade eine akute Gefahr besteht, ist der wichtigste Schritt, den "
    "Notruf zu wählen oder die Person nicht allein zu lassen. Diese Stellen beraten "
    "auch Angehörige:\n\n{resources}\n\n"
    "Damit ich dich richtig verstehe: geht es um eine Person, die gerade in Gefahr "
    "ist, oder um Sorgen, die schon länger da sind?"
)

THIRD_PERSON_EN = (
    "It sounds like you're worried about someone else, and that is a heavy thing to "
    "carry.\n\n"
    "If there is acute danger right now, the most useful step is to call the emergency "
    "number or stay with the person. These lines also advise relatives and friends:\n\n"
    "{resources}\n\n"
    "So I understand you correctly: is someone in danger right now, or is this a "
    "worry that has been there for a while?"
)


class PolicyMode(str):
    NORMAL = "normal"
    CRISIS_IMMINENT = "crisis_imminent"
    CRISIS_SUPPORTIVE = "crisis_supportive"


@dataclass
class PolicyDecision:
    mode: str
    allow_tools: bool
    allow_model: bool
    show_resources: bool
    #: Pre-written text that replaces model generation entirely.
    override_text: str | None = None
    #: Extra lines appended to the system prompt for this turn.
    system_suffix: str = ""
    scope_label: str = SCOPE_LABEL_DE
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "allow_tools": self.allow_tools,
            "allow_model": self.allow_model,
            "show_resources": self.show_resources,
            "has_override": self.override_text is not None,
            "scope_label": self.scope_label,
            "notes": list(self.notes),
        }


def system_prompt(locale: str = "de") -> str:
    extra = (
        "\n\nRespond in German unless the person writes in another language. "
        "German must read naturally, not like a translation."
        if locale.startswith("de")
        else "\n\nRespond in the language the person uses. Keep it natural."
    )
    return SYSTEM_PROMPT_CORE + extra


def decide(
    assessment: CrisisAssessment,
    *,
    locale: str = "de",
    region: str | None = None,
) -> PolicyDecision:
    """Turn a crisis assessment into a concrete turn policy."""
    english = locale.lower().startswith("en")
    resources_block = resources.render(region, "en" if english else "de")

    if assessment.level >= RiskLevel.IMMINENT:
        template = CRISIS_IMMINENT_EN if english else CRISIS_IMMINENT_DE
        return PolicyDecision(
            mode=PolicyMode.CRISIS_IMMINENT,
            allow_tools=False,
            allow_model=False,
            show_resources=True,
            override_text=template.format(resources=resources_block),
            system_suffix="A crisis hand-off has already been shown; do not repeat it.",
            scope_label=SCOPE_LABEL_EN if english else SCOPE_LABEL_DE,
            notes=[
                "deterministic hand-off; the model is not used for the first response",
                "tool use blocked for this turn",
            ],
        )

    if assessment.level == RiskLevel.ELEVATED:
        third = any("third_person" in c for c in assessment.categories)
        if third:
            template = THIRD_PERSON_EN if english else THIRD_PERSON_DE
        else:
            template = CRISIS_SUPPORTIVE_EN if english else CRISIS_SUPPORTIVE_DE
        return PolicyDecision(
            mode=PolicyMode.CRISIS_SUPPORTIVE,
            allow_tools=False,
            allow_model=False,
            show_resources=True,
            override_text=template.format(resources=resources_block),
            system_suffix="A crisis hand-off has already been shown; do not repeat it.",
            scope_label=SCOPE_LABEL_EN if english else SCOPE_LABEL_DE,
            notes=[
                "deterministic supportive response with verified resources",
                "tool use blocked for this turn",
            ],
        )

    return PolicyDecision(
        mode=PolicyMode.NORMAL,
        allow_tools=True,
        allow_model=True,
        show_resources=False,
        scope_label=SCOPE_LABEL_EN if english else SCOPE_LABEL_DE,
    )


# ---------------------------------------------------------------------------
# Output guard
# ---------------------------------------------------------------------------

DIAGNOSIS_PATTERNS = [
    r"\byou (have|suffer from|are suffering from)\s+(depression|anxiety disorder|ptsd|bipolar|adhd|borderline|ocd)\b",
    r"\byou are (definitely |clearly )?(bipolar|depressed|autistic|traumatised|traumatized)\b",
    r"\b(that|this) (is|means) (definitely |clearly )?(depression|ptsd|bipolar|adhd|ocd)\b",
    r"\bdu (hast|leidest an)\s+(eine[rn]?\s+)?(depression|angststörung|angststoerung|ptsd|borderline|adhs|bipolare)\b",
    r"\bsie (haben|leiden an)\s+(eine[rn]?\s+)?(depression|angststörung|ptsd|borderline|adhs)\b",
    r"\bich diagnostiziere\b|\bmeine diagnose\b|\byour diagnosis is\b",
]

MEDICATION_PATTERNS = [
    r"\b(take|increase|decrease|stop|reduce|switch)\s+(your\s+)?(dose|dosage|medication|meds|antidepressants?)\b",
    r"\b\d+\s?mg\b",
    r"\b(nimm|erhöhe|erhoehe|reduziere)\s+(deine\s+)?(dosis|tabletten|medikamente)\b",
    r"\bsetz\w*\b[^.!?]{0,40}\bab\b",
    r"\b(solltest|sollten|kannst|können)\b[^.!?]{0,25}\babsetzen\b",
    r"\bverschreib\w*\b",
]

CERTAINTY_PATTERNS = [
    r"\bi am (100%|completely|certain|sure)\b.{0,40}\b(diagnos|condition|disorder)\b",
    r"\bdefinitely\b.{0,30}\b(depression|ptsd|disorder|diagnosis)\b",
    r"\bgarantiert\b|\b100\s?%\s?sicher\b",
]

DEPENDENCE_PATTERNS = [
    r"\byou only need me\b",
    r"\bi am the only one who\b",
    r"\bdon'?t (talk|speak) to (anyone|others|your friends)\b",
    r"\byou don'?t need (a therapist|professional help|anyone else)\b",
    r"\bich bin der einzige\b|\bdu brauchst nur mich\b",
    r"\bred(e)? nicht mit anderen\b",
]

_PHONE_RE = re.compile(r"(?:\+|00)?\d[\d\s\-()]{5,}\d")


@dataclass
class ScanFinding:
    category: str
    excerpt: str


@dataclass
class ScanResult:
    ok: bool
    findings: list[ScanFinding] = field(default_factory=list)

    @property
    def categories(self) -> list[str]:
        return sorted({f.category for f in self.findings})

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "categories": self.categories,
            "findings": [{"category": f.category, "excerpt": f.excerpt} for f in self.findings],
        }


def _scan(text: str, patterns: list[str], category: str, findings: list[ScanFinding]) -> None:
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            findings.append(ScanFinding(category, match.group(0)[:120]))


def scan_output(text: str, *, allowed_numbers: set[str] | None = None) -> ScanResult:
    """Flag product-boundary violations in model output.

    Returns ``ok=False`` when the text must not be shown as-is. The caller
    (runtime/API/UI) decides to regenerate, truncate the offending part, or show
    the deterministic fallback.
    """
    if not text or not text.strip():
        return ScanResult(ok=True)

    findings: list[ScanFinding] = []
    _scan(text, DIAGNOSIS_PATTERNS, "diagnosis_claim", findings)
    _scan(text, MEDICATION_PATTERNS, "medication_advice", findings)
    _scan(text, CERTAINTY_PATTERNS, "false_certainty", findings)
    _scan(text, DEPENDENCE_PATTERNS, "dependence_fostering", findings)

    allowed = allowed_numbers if allowed_numbers is not None else resources.all_numbers()
    for match in _PHONE_RE.finditer(text):
        digits = resources.normalise_number(match.group(0))
        if len(digits) < 3:
            continue
        if digits in allowed:
            continue
        # Allow dates, doses and other non-hotline numerics to pass; only flag
        # things that look like a service number (>= 3 digits with a separator
        # or a local/international prefix).
        if re.search(r"[\s\-()/]", match.group(0)) or match.group(0).startswith(("+", "00")):
            findings.append(ScanFinding("invented_hotline", match.group(0)[:40]))

    return ScanResult(ok=not findings, findings=findings)


def fallback_after_scan(locale: str = "de") -> str:
    if locale.lower().startswith("en"):
        return (
            "I'd rather not give you a diagnosis or a treatment recommendation — that "
            "needs a qualified professional who can talk with you properly. What I can do "
            "is help you sort out what you're noticing and what a next step could look like."
        )
    return (
        "Ich möchte dir keine Diagnose und keine Behandlungsempfehlung geben — dafür "
        "braucht es eine qualifizierte Person, die mit dir spricht. Was ich gut kann: "
        "mit dir sortieren, was du beobachtest, und was ein nächster Schritt sein könnte."
    )
