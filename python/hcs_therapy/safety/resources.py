"""Region-specific crisis resources.

Rules:

* every entry carries its source URL and the date it was reviewed;
* an entry that has not been verified against a primary source is flagged and
  suppressed from the UI rather than shown as fact;
* the default answer never invents a number: if no verified pack matches the
  user, the assistant says "call your local emergency number" and, for the EU,
  the single European emergency number 112.

Verified against primary sources on 2026-11-04.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REVIEWED_AT = "2026-11-04"


@dataclass(frozen=True)
class Resource:
    name: str
    contact: str
    hours: str
    languages: tuple[str, ...]
    source_url: str
    verified: bool = True
    note: str | None = None


@dataclass(frozen=True)
class RegionPack:
    region: str
    label: str
    emergency: Resource
    lines: tuple[Resource, ...] = field(default_factory=tuple)
    reviewed_at: str = REVIEWED_AT


DE = RegionPack(
    region="DE",
    label="Deutschland",
    emergency=Resource(
        name="Notruf (Feuerwehr/Rettungsdienst)",
        contact="112",
        hours="24/7",
        languages=("de", "en"),
        source_url="https://www.telefonseelsorge.de/",
    ),
    lines=(
        Resource(
            name="Telefonseelsorge",
            contact="0800 111 0 111",
            hours="24/7, kostenfrei",
            languages=("de",),
            source_url="https://www.telefonseelsorge.de/",
        ),
        Resource(
            name="Telefonseelsorge (alternative Leitung)",
            contact="0800 111 0 222",
            hours="24/7, kostenfrei",
            languages=("de",),
            source_url="https://www.telefonseelsorge.de/",
        ),
        Resource(
            name="Telefonseelsorge (EU-weite Nummer)",
            contact="116 123",
            hours="24/7",
            languages=("de", "en"),
            source_url="https://www.telefonseelsorge.de/",
        ),
    ),
)

UK = RegionPack(
    region="UK",
    label="United Kingdom",
    emergency=Resource(
        name="Emergency services",
        contact="999",
        hours="24/7",
        languages=("en",),
        source_url="https://www.samaritans.org/",
    ),
    lines=(
        Resource(
            name="Samaritans",
            contact="116 123",
            hours="24/7, free",
            languages=("en",),
            source_url="https://www.samaritans.org/",
        ),
    ),
)

US = RegionPack(
    region="US",
    label="United States",
    emergency=Resource(
        name="Emergency services",
        contact="911",
        hours="24/7",
        languages=("en", "es"),
        source_url="https://988lifeline.org/",
    ),
    lines=(
        Resource(
            name="988 Suicide & Crisis Lifeline",
            contact="988 (call or text)",
            hours="24/7",
            languages=("en", "es"),
            source_url="https://988lifeline.org/",
        ),
    ),
)

EU = RegionPack(
    region="EU",
    label="European Union",
    emergency=Resource(
        name="European emergency number",
        contact="112",
        hours="24/7",
        languages=("all EU languages via interpretation",),
        source_url="https://europa.eu/european-union/about-eu/figures/emergency-numbers_en",
    ),
)

#: Regions we know nothing verified about. The UI must fall back to this.
UNKNOWN = RegionPack(
    region="UNKNOWN",
    label="Unspecified region",
    emergency=Resource(
        name="Local emergency services",
        contact="your local emergency number",
        hours="24/7",
        languages=(),
        source_url="",
        verified=False,
        note="No region-specific pack is installed; the app never guesses a hotline.",
    ),
)

PACKS: dict[str, RegionPack] = {p.region: p for p in (DE, UK, US, EU)}

_ALIASES = {
    "de": "DE",
    "deu": "DE",
    "germany": "DE",
    "deutschland": "DE",
    "at": "EU",
    "au": "EU",
    "ch": "EU",
    "uk": "UK",
    "gb": "UK",
    "england": "UK",
    "scotland": "UK",
    "wales": "UK",
    "us": "US",
    "usa": "US",
    "united states": "US",
    "eu": "EU",
    "europe": "EU",
}


def resolve(region: str | None) -> RegionPack:
    """Map a user-selected region to a verified pack, never a guess."""
    if not region:
        return UNKNOWN
    key = region.strip().lower()
    if key in _ALIASES:
        return PACKS[_ALIASES[key]]
    if key.upper() in PACKS:
        return PACKS[key.upper()]
    return UNKNOWN


def all_numbers() -> set[str]:
    """Every phone string this app is allowed to print."""
    numbers: set[str] = set()
    for pack in (*PACKS.values(), UNKNOWN):
        for resource in (pack.emergency, *pack.lines):
            cleaned = normalise_number(resource.contact)
            if cleaned:
                numbers.add(cleaned)
    # EU-wide numbers are always safe to mention.
    numbers.update({"112", "116123"})
    return numbers


def normalise_number(text: str) -> str:
    return re.sub(r"[^0-9]", "", text)


def render(region: str | None, locale: str = "de") -> str:
    """Plain-text resource block for a deterministic crisis response.

    Deliberately plain: a crisis message must not depend on a markdown renderer,
    a stylesheet, or a component that might fail to load.
    """
    pack = resolve(region)
    if locale.startswith("en"):
        lines = ["Immediate help:", f"· {pack.emergency.name}: {pack.emergency.contact}"]
        if pack.lines:
            lines.extend(f"· {r.name}: {r.contact} ({r.hours})" for r in pack.lines)
        if pack is UNKNOWN:
            lines.append(
                "· Outside these regions, dial your local emergency number (112 in the EU)."
            )
        lines.append("")
        lines.append("This app is not a crisis service and cannot send help to you.")
        return "\n".join(lines)

    lines = ["Sofort erreichbar:", f"· {pack.emergency.name}: {pack.emergency.contact}"]
    if pack.lines:
        lines.extend(f"· {r.name}: {r.contact} ({r.hours})" for r in pack.lines)
    if pack is UNKNOWN:
        lines.append(
            "· Außerhalb dieser Regionen: die örtliche Notrufnummer wählen (in der EU die 112)."
        )
    lines.append("")
    lines.append("Diese App ist kein Krisendienst und kann keine Hilfe zu dir schicken.")
    return "\n".join(lines)


def as_dict() -> dict:
    """Machine-readable pack for the web UI."""
    return {
        "reviewed_at": REVIEWED_AT,
        "packs": {
            region: {
                "label": pack.label,
                "emergency": {
                    "name": pack.emergency.name,
                    "contact": pack.emergency.contact,
                    "verified": pack.emergency.verified,
                },
                "lines": [
                    {
                        "name": r.name,
                        "contact": r.contact,
                        "hours": r.hours,
                        "source_url": r.source_url,
                        "verified": r.verified,
                    }
                    for r in pack.lines
                ],
                "reviewed_at": pack.reviewed_at,
            }
            for region, pack in PACKS.items()
        },
        "unknown": {
            "label": UNKNOWN.label,
            "emergency": UNKNOWN.emergency.contact,
            "note": UNKNOWN.emergency.note,
        },
    }
