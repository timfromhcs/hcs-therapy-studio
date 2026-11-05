"""German address register: ``du`` or ``Sie``, and whether a reply mixes them.

Why this exists
---------------

``status.md`` has recorded this limitation since M1: *"the 1.7B model mixed German
``du`` and ``Sie`` inside one answer, and appended an emoji. The output guard does
not catch register."* Mixing the two inside a single reply is not a typo. In a
German therapeutic-support context it reads as a form letter that forgot who it
was talking to, and it undermines exactly the register of care the product claims.

The fix has two halves and this module is both:

1. **Anchoring** — read the register of the user's own message and tell the model,
   in the system prompt, which form to use. Prevention beats correction.
2. **Detection** — measure the reply, so a mixed answer is visible in the API
   payload and the UI instead of being invisible.

What this module deliberately does **not** do: rewrite the text. German formal and
informal differ in verb conjugation ("Sie fühlen" / "du fühlst"), not only in
pronouns, so a pronoun substitution would produce grammatically wrong German —
worse than the mixed register it was meant to fix. Detection plus anchoring is
honest; silent bad grammar is not.

Linguistic rules encoded here
-----------------------------

German ``Sie`` (formal you) is **capitalised mid-sentence**; lowercase ``sie``
means *she* or *they*. So the case is the signal, and a tokeniser that lowercases
first destroys it. ``Ihnen`` is unambiguous — it has no lowercase homograph in
common use. Sentence-initial ``Sie``/``Ihr`` is genuinely ambiguous (*She says…*),
so it is counted separately and never on its own switches the verdict to formal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "Register",
    "RegisterReport",
    "analyse",
    "anchor_instruction",
    "is_mixed",
]


class Register(StrEnum):
    DU = "du"
    SIE = "sie"
    NEUTRAL = "neutral"

    @property
    def label_de(self) -> str:
        return {
            Register.DU: "du",
            Register.SIE: "Sie",
            Register.NEUTRAL: "neutral",
        }[self]


# Lowercase informal forms. "Du"/"Dir"/"Dich" at a sentence start are still
# informal, so the pattern is case-insensitive for these: there is no capitalised
# homograph of "du".
_DU = re.compile(
    r"\b(du|dich|dir|dein|deine|deinem|deinen|deiner|deines|deines?)\b",
    re.IGNORECASE,
)

# Unambiguous formal forms: no lowercase homograph worth worrying about.
_SIE_UNAMBIGUOUS = re.compile(r"\b(Ihnen|Ihrem|Ihren|Ihrer|Ihres|Ihre|Ihr)\b")
_SIE_PRONOUN = re.compile(r"\bSie\b")

# A sentence ends at one of these, optionally followed by quote characters and
# whitespace. Anchored to the END of the prefix, never searched over a slice:
# an unanchored ``^`` in the pattern matches every slice and made every token look
# sentence-initial, which silently disabled the whole formal-address detector.
_SENTENCE_END = re.compile(r"(?:[.!?:;]|\n)\s*$")
_SURROUNDING = " \t\n\u201e\u201c\u201a\u2018\"'()[]"

# A sentence-initial "Sie" could be *she* or formal *you*. German disambiguates it
# by the following verb: formal "Sie" takes the 3rd-person *plural* form
# ("Sie können"), while "she" takes the 3rd-person *singular* ("Sie kann"). Using
# the verb rather than a word list generalises; these two small sets cover the
# irregular auxiliaries that morphology cannot resolve.
_PLURAL_IRREGULAR = {
    "sind", "seid", "waren", "wären", "haben", "hatten", "hätten",
    "werden", "wurden", "würden", "müssen", "dürfen", "können", "wollen", "mögen",
}
_SINGULAR_IRREGULAR = {
    "ist", "war", "wäre", "hat", "hatte", "hätte", "wird", "wurde", "würde",
    "muss", "darf", "kann", "will", "mag", "soll",
}
_NEXT_WORD = re.compile(r"\s+([A-Za-zÄÖÜäöüß]+)")


@dataclass
class RegisterReport:
    register: Register
    du_forms: int
    sie_forms: int
    ambiguous_sie: int
    examples: dict[str, list[str]] = field(default_factory=dict)

    @property
    def mixed(self) -> bool:
        """Both registers used without ambiguity, inside one text."""
        return self.du_forms > 0 and self.sie_forms > 0

    @property
    def total(self) -> int:
        return self.du_forms + self.sie_forms

    def to_dict(self) -> dict[str, object]:
        return {
            "register": self.register.value,
            "label_de": self.register.label_de,
            "mixed": self.mixed,
            "du_forms": self.du_forms,
            "sie_forms": self.sie_forms,
            "ambiguous_sie": self.ambiguous_sie,
            "examples": self.examples,
            "advice": _advice(self),
        }


def _advice(report: RegisterReport) -> str | None:
    if report.mixed:
        return (
            "Die Antwort wechselt zwischen 'du' und 'Sie'. Das ist kein Tippfehler, "
            "sondern ein Anredebruch; die Antwort sollte in einer Form bleiben."
        )
    if report.total == 0:
        return None
    return None


def _sentence_initial(text: str, position: int) -> bool:
    """Whether the match at ``position`` begins a sentence."""
    prefix = text[:position]
    if not prefix.strip(_SURROUNDING):
        return True
    return bool(_SENTENCE_END.search(prefix))


def _collect(pattern: re.Pattern[str], text: str) -> list[tuple[int, str]]:
    return [(match.start(), match.group(0)) for match in pattern.finditer(text)]


def _verb_number(word: str) -> str | None:
    """Plural or singular for a German verb form, or ``None`` when unclear.

    Formal ``Sie`` is conjugated in the 3rd person **plural**, which is exactly the
    form that also means *they*. 3rd person singular ("Sie kommt") can only mean
    *she*, so it is excluded from the formal count.
    """
    lowered = word.lower()
    if lowered in _PLURAL_IRREGULAR:
        return "plural"
    if lowered in _SINGULAR_IRREGULAR:
        return "singular"
    if len(lowered) <= 3:
        return None
    # Regular verbs: -en is plural (auch formell), -t is singular. Anything else
    # (an adjective, a noun) falls through to ``None`` instead of being guessed.
    if lowered.endswith("en"):
        return "plural"
    if lowered.endswith("t"):
        return "singular"
    return None


def _sentence_initial_sie_is_formal(text: str, position: int) -> bool | None:
    """Resolve a sentence-initial ``Sie`` by the verb that follows it."""
    match = _NEXT_WORD.match(text, position + 3)
    if not match:
        return None
    number = _verb_number(match.group(1))
    if number == "plural":
        return True
    if number == "singular":
        return False
    return None


def analyse(text: str) -> RegisterReport:
    """Classify the address register of one German text."""
    if not text or not text.strip():
        return RegisterReport(Register.NEUTRAL, 0, 0, 0, {})

    du_hits = _collect(_DU, text)

    sie_hits: list[tuple[int, str]] = []
    ambiguous: list[tuple[int, str]] = []
    excluded: list[tuple[int, str]] = []
    for position, token in _collect(_SIE_PRONOUN, text):
        if not _sentence_initial(text, position):
            sie_hits.append((position, token))
            continue
        verdict = _sentence_initial_sie_is_formal(text, position)
        if verdict is True:
            sie_hits.append((position, token))
        elif verdict is False:
            # "Sie kommt" is *she*, not *you*. Counting it would make every
            # third-person report look like formal address.
            excluded.append((position, token))
        else:
            ambiguous.append((position, token))
    for position, token in _collect(_SIE_UNAMBIGUOUS, text):
        # "Ihr" at a sentence start is ambiguous ("Ihr Tag war lang" vs formal),
        # the rest are not.
        if token == "Ihr" and _sentence_initial(text, position):
            ambiguous.append((position, token))
        else:
            sie_hits.append((position, token))

    du_forms = len(du_hits)
    sie_forms = len(sie_hits)

    if du_forms and sie_forms:
        register = Register.DU if du_forms >= sie_forms else Register.SIE
    elif du_forms:
        register = Register.DU
    elif sie_forms:
        register = Register.SIE
    else:
        # Only ambiguous markers: a sentence-initial "Sie" is far more often
        # formal address in a reply to a user than a report about a third party,
        # but claiming certainty would be dishonest, so the verdict stays neutral
        # and the raw count is still exposed.
        register = Register.NEUTRAL

    examples: dict[str, list[str]] = {}
    if du_hits:
        examples["du"] = [token for _, token in du_hits[:4]]
    if sie_hits:
        examples["sie"] = [token for _, token in sie_hits[:4]]
    if excluded:
        examples["third_person"] = [token for _, token in excluded[:4]]

    return RegisterReport(register, du_forms, sie_forms, len(ambiguous), examples)


def is_mixed(text: str) -> bool:
    return analyse(text).mixed


def anchor_instruction(
    user_message: str,
    *,
    locale: str = "de",
    default: str | None = "du",
) -> str | None:
    """System-prompt line that pins the address register for the reply.

    ``default`` is what to use when the person gave no signal. It is **not**
    invented: the rest of the interface already addresses the user with "du"
    ("Was beschäftigt dich gerade?"), so defaulting the model to the same form is
    consistency with the product's own voice. Pass ``default=None`` to leave the
    model unanchored instead.

    Measured, not assumed: with ``default=None`` one of five real requests mixed
    ``du`` and ``Sie`` inside a single answer; with the default set, zero did.
    See ``scripts/bench/register_anchoring.py`` and
    ``docs/benchmarks/register-anchoring.md``.
    """
    if not locale.lower().startswith("de"):
        return None

    report = analyse(user_message)
    if report.register is Register.SIE:
        target, why = Register.SIE, "Die Person siezt dich."
    elif report.register is Register.DU:
        target, why = Register.DU, "Die Person duzt dich."
    elif default is None:
        return None
    else:
        target = Register.DU if default == "du" else Register.SIE
        why = "Die Person verwendet keine Anrede; die App selbst duzt."

    if target is Register.DU:
        return (
            f"{why} Antworte durchgehend mit \"du\" und passenden Verbformen. "
            "Verwende in dieser Antwort kein \"Sie\" als Anrede."
        )
    return (
        f"{why} Antworte durchgehend mit \"Sie\" und passenden Verbformen. "
        "Verwende in dieser Antwort kein \"du\" als Anrede."
    )


def instruction_for(register: Register) -> str | None:
    """The anchor text for an explicit target register."""
    if register is Register.DU:
        return (
            "Antworte durchgehend mit \"du\" und passenden Verbformen. "
            "Verwende in dieser Antwort kein \"Sie\" als Anrede."
        )
    if register is Register.SIE:
        return (
            "Antworte durchgehend mit \"Sie\" und passenden Verbformen. "
            "Verwende in dieser Antwort kein \"du\" als Anrede."
        )
    return None
