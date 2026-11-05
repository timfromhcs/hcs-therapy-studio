"""Every relative link and image in README.md must resolve.

A README is the first thing a stranger runs. A broken link is the cheapest
possible signal that nobody checked. This test runs in CI and locally.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\]\(([^)\s]+)\)")
IMAGE = re.compile(r"<img[^>]+src=\"([^\"]+)\"")
SRC = re.compile(r"src=\"([^\"]+)\"")


def _relative_targets(text: str) -> list[str]:
    targets: list[str] = []
    for raw in LINK.findall(text) + IMAGE.findall(text) + SRC.findall(text):
        if raw.startswith(("http://", "https://", "mailto:", "data:")):
            continue
        path = raw.split("#", 1)[0]
        if path:
            targets.append(path)
    return targets


def test_readme_relative_links_resolve() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = [target for target in _relative_targets(text) if not (ROOT / target).exists()]
    assert not missing, f"README links that do not resolve: {missing}"


def test_readme_has_the_sections_a_stranger_needs() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for heading in (
        "## Quick start",
        "## What is implemented",
        "## Honest limitations",
        "## Licence and attribution",
        "## Table of contents",
    ):
        assert heading in text, f"README lost its {heading!r} section"


def test_readme_does_not_link_the_vite_scaffold() -> None:
    """The shipped favicon and title are part of the product, not the template."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "vite.svg" not in text
    index = (ROOT / "apps" / "web" / "index.html").read_text(encoding="utf-8")
    assert "vite.svg" not in index, "the Vite scaffold favicon is still referenced"
    assert "<title>HCS Therapy Studio</title>" in index
    assert "default-src 'self'" in index, "the client CSP is missing"


def test_ci_runs_the_commands_that_were_actually_passed() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "ruff check ." in workflow
    assert "pytest" in workflow
    assert "npm run build" in workflow


def test_banner_and_logo_are_authored_in_repo() -> None:
    """The mark must be self-contained: no remote image, font or href.

    ``xmlns="http://www.w3.org/2000/svg"`` is a namespace identifier, not a
    fetch, so it is allowed; an ``href`` or an ``@import`` is not.
    """
    forbidden = ("href=", "xlink:href", "@import", "url(http", "<image")
    for path in sorted((ROOT / "assets").glob("*.svg")):
        body = path.read_text(encoding="utf-8")
        assert body.startswith("<svg"), f"assets/{path.name} is not an SVG"
        for needle in forbidden:
            assert needle not in body, f"assets/{path.name} references a remote resource ({needle})"


def test_every_diagram_in_the_readme_parses_as_xml() -> None:
    """A diagram that does not parse renders as a broken-image icon on GitHub."""
    import xml.etree.ElementTree as ET

    text = (ROOT / "README.md").read_text(encoding="utf-8")
    diagrams = [name for name in re.findall(r"assets/[\w.-]+\.svg", text)]
    assert len(diagrams) >= 4, f"expected the README to carry its diagrams, found {diagrams}"
    for name in sorted(set(diagrams)):
        path = ROOT / name
        assert path.is_file(), f"{name} is referenced but missing"
        root = ET.parse(path).getroot()
        assert root.tag.endswith("svg")
        # A diagram without an accessible name is invisible to a screen reader.
        assert root.get("aria-label") or root.get("role") == "img", name


def test_the_readme_shows_what_is_not_built() -> None:
    """The limitations table is the honest part; it must not be trimmed away."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for missing in ("one-file installer", "browser edition", "Clinician review"):
        assert missing in text, f"the README stopped naming {missing!r} as unbuilt"
