"""Deterministic crisis-intent detection.

Why rules and not (only) a classifier: the build contract requires a
deterministic layer that cannot be talked out of firing. A model can be
prompt-injected, paraphrased around, or simply unavailable during warm-up. This
module runs before the model, before any tool call, and before any UI shortcut.

It is intentionally conservative in *both* directions:

* it fires on explicit, first-person intention and on imminence markers;
* it does not fire on clear negation ("I would never kill myself");
* it does not fire on third-person or quoted text at the highest level, but it
  still returns ``elevated`` so the assistant can respond supportively rather
  than ignoring the content;
* it never invents a diagnosis, a plan, or a location.

Every pattern is documented, tested, and language-specific (English/German).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum


class RiskLevel(IntEnum):
    NONE = 0
    ELEVATED = 1
    IMMINENT = 2


@dataclass
class CrisisAssessment:
    level: RiskLevel
    categories: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)
    #: True when tool use and long exercises must be skipped entirely.
    block_tools: bool = False
    #: True when the UI must show the emergency resource panel.
    show_resources: bool = False
    note: str | None = None

    @property
    def is_crisis(self) -> bool:
        return self.level >= RiskLevel.ELEVATED

    def to_dict(self) -> dict:
        return {
            "level": self.level.name,
            "categories": list(self.categories),
            "matched": list(self.matched),
            "block_tools": self.block_tools,
            "show_resources": self.show_resources,
            "note": self.note,
        }


# --- pattern tables --------------------------------------------------------
# Each entry: (category, regex). Patterns are matched case-insensitively on a
# normalised copy of the text (lowercased, umlauts folded) so that "umbringen"
# and "umbringen," behave the same.
_DE_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})

EXPLICIT_INTENT = [
    ("suicide_intent_en", r"\b(i|im|i'm|i am)\s+(going to|gonna|want to|wanna|plan to|will)\s+(kill myself|end my life|end it all|take my own life|die)\b"),
    ("suicide_intent_en", r"\bi\s+(don'?t|do not)\s+want to\s+(live|be alive|exist|wake up)\b"),
    ("suicide_ideation_en", r"\b(suicidal|suicide|kill myself|end my life|better off dead|no reason to live|nothing to live for)\b"),
    ("suicide_plan_en", r"\b(have|got|bought)\b[^.]{0,25}\b(rope|gun|pills|tablets|knife)\b[^.]{0,20}\b(ready|with me)\b"),
    ("suicide_plan_en", r"\b(wrote|written)\s+(a|my)\s+(suicide\s+)?(note|letter)\b"),
    ("suicide_plan_en", r"\b(tonight is the night|today is the day i (die|end it))\b"),
    ("self_harm_en", r"\b(cut(ting)? myself|hurt(ing)? myself|self[- ]harm|burn(ing)? myself|starve myself)\b"),
    ("suicide_intent_de", r"\b(ich\s+)?(will|möchte|moechte|werde|will\s+mich)\s+(mich\s+)?(umbring\w*|um\s+zu\s+bringen|töten|toeten|suizid\s+begehen|sterben)\b"),
    ("suicide_intent_de", r"\b(bring\w*)\s+(mich|ich\s+mich)\b[^.!?]{0,30}\bum\b"),
    ("suicide_intent_de", r"\b(mich\s+umbring\w*|umbring\w*\s+mich|suizid\w*|selbstmord\w*)\b"),
    ("suicide_intent_de", r"\b((mir|sich)\s+das\s+leben\s+(zu\s+)?nehmen|das\s+leben\s+(zu\s+)?nehmen)\b"),
    ("suicide_plan_de", r"\b(habe|hab)\b[^.!?]{0,30}\b(seil|messer|waffe|tabletten)\b[^.!?]{0,25}\b(bereit|dabei)\b"),
    ("suicide_plan_de", r"\babschiedsbrief\b"),
    ("suicide_ideation_de", r"\b(will\s+nicht\s+mehr\s+leben|keinen\s+grund\s+mehr\s+zu\s+leben|besser\s+tot|waere\s+besser\s+tot|wäre\s+besser\s+tot|nicht\s+mehr\s+aufwachen)\b"),
    ("self_harm_de", r"\b(ritz\w*|schneide\s+mich|schneiden\s+mich|mir\s+etwas\s+antun|selbstverletz\w*)\b"),
]

IMMINENCE_MARKERS = [
    ("imminence_en", r"\b(right now|tonight|today|this evening|in a few minutes|already|have (the )?(pills|rope|knife|gun)|wrote (a|my) (note|letter)|goodbye)\b"),
    ("imminence_de", r"\b(jetzt\s+gleich|heute\s+nacht|heute\s+abend|sofort|gleich|habe\s+(die\s+)?(tabletten|seil|messer)|abschiedsbrief|tsch(ü|ue)ss\s+sagen)\b"),
]

NEGATION = [
    r"\b(i\s+)?(would\s+never|don'?t|do\s+not|never)\s+(want\s+to\s+)?(kill myself|hurt myself|die)\b",
    r"\bnot\s+suicidal\b",
    r"\b(ich\s+)?(will|werde|möchte|moechte)\s+(mich\s+)?(nicht|nie|niemals)\s+(umbring\w*|töten|toeten|sterben)\b",
    r"\bkein(?:e)?\s+suizidgedanken\b",
    r"\bnicht\s+suizidal\b",
]

THIRD_PERSON = [
    r"\b(he|she|they|my (friend|partner|brother|sister|son|daughter|mother|father|colleague|ex)|someone|somebody)\b[^.]{0,80}\b(kill(ed|ing)? (him|her|them)self|wants? to (die|kill)|suicidal|suicide)\b",
    r"\b(er|sie|mein freund|meine freundin|mein bruder|meine schwester|mein sohn|meine tochter|jemand)\b[^.]{0,80}\b(umbring\w*|suizid\w*|selbstmord\w*|will\s+nicht\s+mehr\s+leben)\b",
]

#: Fiction/quotation framing. Content like this is still treated as a possible
#: signal (a person may test the waters this way), but it is not escalated to
#: the imminent path on the strength of a quote alone.
QUOTED_CONTEXT = [
    r"\b(in (dem|diesem) buch|im buch|in (dem|diesem) film|im film|songtext|liedtext|zitat|die figur|der charakter|chapter|novel)\b",
    r"\b(in (a|the|this) (book|movie|film|novel|lyrics|song)|the character|the protagonist|quote)\b",
]

#: Instructions that try to switch off safety behaviour. They never suppress the
#: crisis layer; they are recorded so the assistant can refuse the override.
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) (instructions|rules)",
    r"you are now (in )?(developer|dan|god) mode",
    r"disregard (your|the) (safety|policy|rules)",
    r"vergiss (alle )?(deine )?(anweisungen|regeln)",
    r"ignoriere (die )?(sicherheits|vorherigen)\s*(regeln|anweisungen)",
]

_COMPILED_EXPLICIT = [(cat, re.compile(pat, re.IGNORECASE)) for cat, pat in EXPLICIT_INTENT]
_COMPILED_IMMINENCE = [(cat, re.compile(pat, re.IGNORECASE)) for cat, pat in IMMINENCE_MARKERS]
_COMPILED_NEGATION = [re.compile(p, re.IGNORECASE) for p in NEGATION]
_COMPILED_THIRD = [re.compile(p, re.IGNORECASE) for p in THIRD_PERSON]
_COMPILED_INJECTION = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
_COMPILED_QUOTED = [re.compile(p, re.IGNORECASE) for p in QUOTED_CONTEXT]

#: Any of these turns a self-harm mention into "we must not wait".
MAX_LENGTH = 20000


def normalise(text: str) -> str:
    return text.translate(_DE_FOLD).lower()[:MAX_LENGTH]


def assess(text: str) -> CrisisAssessment:
    """Classify one user message. Pure function: no I/O, no model."""
    if not text or not text.strip():
        return CrisisAssessment(RiskLevel.NONE)

    haystack = normalise(text)
    categories: list[str] = []
    matched: list[str] = []

    for category, pattern in _COMPILED_EXPLICIT:
        found = pattern.search(haystack)
        if found:
            categories.append(category)
            matched.append(found.group(0)[:80])

    for pattern in _COMPILED_NEGATION:
        found = pattern.search(haystack)
        if found:
            matched.append(f"negation:{found.group(0)[:60]}")
            return CrisisAssessment(
                RiskLevel.NONE,
                categories=["negated"],
                matched=matched,
                note="explicit negation; do not escalate, but stay attentive",
            )

    injection = [
        p.search(haystack).group(0)[:60]  # type: ignore[union-attr]
        for p in _COMPILED_INJECTION
        if p.search(haystack)
    ]

    third_person = any(p.search(haystack) for p in _COMPILED_THIRD)

    if not categories:
        if third_person:
            # A user describing someone else's risk. We must not remain silent,
            # but we also must not assert anything about the user's own state.
            return CrisisAssessment(
                RiskLevel.ELEVATED,
                categories=["third_person"],
                matched=matched + injection,
                block_tools=True,
                show_resources=True,
                note="concern about another person; support without assuming the user's own risk",
            )
        return CrisisAssessment(RiskLevel.NONE)

    first_person_marker = re.search(r"\b(i|ich|me|mir|mich|my|mein|meine)\b", haystack) is not None

    if third_person and not first_person_marker:
        return CrisisAssessment(
            RiskLevel.ELEVATED,
            categories=categories + ["third_person"],
            matched=matched + injection,
            block_tools=True,
            show_resources=True,
            note="concern about another person; support without assuming the user's own risk",
        )

    imminence = []
    for category, pattern in _COMPILED_IMMINENCE:
        found = pattern.search(haystack)
        if found:
            imminence.append(category)
            matched.append(f"{category}:{found.group(0)[:40]}")

    quoted = any(p.search(haystack) for p in _COMPILED_QUOTED)
    if quoted:
        # Fiction/quote framing must never suppress the resource panel, but it
        # does downgrade the urgent path so we do not dramatise a book line.
        return CrisisAssessment(
            RiskLevel.ELEVATED,
            categories=categories + imminence + ["quoted_context"],
            matched=matched + injection,
            block_tools=True,
            show_resources=True,
            note="quoted/fiction framing; respond supportively and ask one clarifying question",
        )

    if imminence:
        return CrisisAssessment(
            RiskLevel.IMMINENT,
            categories=categories + imminence,
            matched=matched + injection,
            block_tools=True,
            show_resources=True,
            note="explicit intent plus imminence marker: do not run tools or exercises",
        )

    return CrisisAssessment(
        RiskLevel.ELEVATED,
        categories=categories,
        matched=matched + injection,
        block_tools=True,
        show_resources=True,
        note="explicit self-harm/suicide content without imminence marker",
    )


def is_prompt_injection(text: str) -> bool:
    haystack = normalise(text)
    return any(p.search(haystack) for p in _COMPILED_INJECTION)
