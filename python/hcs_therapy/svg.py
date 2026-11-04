"""SVG/text-to-SVG sanitisation.

The Visual Studio lets a model propose a *constraint-checked scene description*
which we render ourselves. Imported SVG is untrusted input: it is parsed, then
rebuilt from an allow-list. Nothing executable survives, and nothing can trigger
a network request.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

MAX_SVG_BYTES = 2 * 1024 * 1024

FORBIDDEN_ELEMENTS = {
    "script",
    "foreignObject",  # can embed arbitrary HTML
    "iframe",
    "audio",
    "video",
    "use",  # can pull in external documents via href
    "animate",
    "animateMotion",
    "animateTransform",
    "set",
    "handler",
}

ALLOWED_ELEMENTS = {
    "svg", "g", "defs", "title", "desc", "path", "rect", "circle", "ellipse",
    "line", "polyline", "polygon", "text", "tspan", "linearGradient",
    "radialGradient", "stop", "clipPath", "mask", "pattern", "symbol", "marker",
}

FORBIDDEN_ATTRIBUTE_PREFIXES = ("on",)
FORBIDDEN_ATTRIBUTES = {"href", "xlink:href", "src", "externalResourcesRequired", "style"}

ALLOWED_URL_SCHEMES = ("data:image/", "#")

DANGEROUS_CONTENT = re.compile(r"<!DOCTYPE|<!ENTITY|<\?xml-stylesheet", re.IGNORECASE)


@dataclass
class SanitizeResult:
    svg: str
    removed: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.removed


class SvgError(ValueError):
    """The input is not usable SVG at all."""


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def sanitize_svg(data: str) -> SanitizeResult:
    if not data or not data.strip():
        raise SvgError("empty SVG")
    if len(data.encode("utf-8")) > MAX_SVG_BYTES:
        raise SvgError(f"SVG exceeds {MAX_SVG_BYTES // (1024 * 1024)} MiB")
    if DANGEROUS_CONTENT.search(data):
        raise SvgError("DOCTYPE/ENTITY/stylesheet instructions are not accepted")

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise SvgError(f"not well-formed XML: {exc}") from exc

    removed: list[str] = []

    def rebuild(element: ET.Element) -> ET.Element | None:
        tag = _strip_namespace(element.tag)
        if tag in FORBIDDEN_ELEMENTS or tag not in ALLOWED_ELEMENTS:
            removed.append(f"element:{tag}")
            return None
        new = ET.Element(tag)
        for key, value in element.attrib.items():
            attr = _strip_namespace(key).lower()
            if attr in FORBIDDEN_ATTRIBUTES or attr.startswith(FORBIDDEN_ATTRIBUTE_PREFIXES):
                removed.append(f"attribute:{attr}")
                continue
            lowered = value.strip().lower()
            if "url(" in lowered and not any(
                scheme in lowered for scheme in ALLOWED_URL_SCHEMES
            ):
                removed.append(f"external-url:{attr}")
                continue
            if attr in {"href", "src"} and not lowered.startswith(ALLOWED_URL_SCHEMES):
                removed.append(f"link:{attr}")
                continue
            # Keep the original spelling: SVG is case-sensitive (viewBox).
            new.set(_strip_namespace(key), value)
        text = (element.text or "").strip()
        if text:
            new.text = text
        for child in list(element):
            rebuilt = rebuild(child)
            if rebuilt is not None:
                new.append(rebuilt)
        return new

    cleaned = rebuild(root)
    if cleaned is None:
        raise SvgError("root element is not an allowed SVG element")
    if cleaned.tag != "svg":
        cleaned.tag = "svg"
    if "xmlns" not in cleaned.attrib:
        cleaned.set("xmlns", "http://www.w3.org/2000/svg")
    if "viewBox" not in cleaned.attrib and not (
        "width" in cleaned.attrib and "height" in cleaned.attrib
    ):
        raise SvgError("SVG needs a viewBox or explicit width and height")

    return SanitizeResult(ET.tostring(cleaned, encoding="unicode"), removed)


# ---------------------------------------------------------------------------
# Constrained scene description -> SVG
# ---------------------------------------------------------------------------

SCENE_SCHEMA = {
    "width": "int (100..4000)",
    "height": "int (100..4000)",
    "background": "#rrggbb",
    "elements": [
        {
            "type": "rect | text | circle | line",
            "x": "int", "y": "int", "w": "int", "h": "int",
            "r": "int", "x2": "int", "y2": "int",
            "fill": "#rrggbb", "stroke": "#rrggbb", "strokeWidth": "int",
            "text": "string", "fontSize": "int", "fontFamily": "string",
            "anchor": "start | middle | end",
        }
    ],
}

_COLOUR = re.compile(r"^#[0-9a-fA-F]{6}$")


class SceneError(ValueError):
    pass


def _clamp(value: object, low: int, high: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SceneError(f"{name} must be an integer")
    if not low <= value <= high:
        raise SceneError(f"{name} must be between {low} and {high}")
    return value


def _colour(value: object, name: str, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or not _COLOUR.match(value):
        raise SceneError(f"{name} must be a #rrggbb colour")
    return value


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_scene(scene: dict) -> str:
    """Deterministic renderer for a constrained layout description.

    The model never emits SVG markup, so there is no injection surface: it emits
    this dictionary, which is validated field by field.
    """
    width = _clamp(scene.get("width", 1080), 100, 4000, "width")
    height = _clamp(scene.get("height", 1080), 100, 4000, "height")
    background = _colour(scene.get("background"), "background", "#ffffff")
    elements = scene.get("elements", [])
    if not isinstance(elements, list) or len(elements) > 200:
        raise SceneError("elements must be a list of at most 200 items")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{background}"/>',
    ]
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            raise SceneError(f"element {index} must be an object")
        kind = element.get("type")
        if kind == "rect":
            parts.append(
                '<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"'
                '{stroke}/>'.format(
                    x=_clamp(element.get("x", 0), 0, width, "x"),
                    y=_clamp(element.get("y", 0), 0, height, "y"),
                    w=_clamp(element.get("w", 10), 1, width, "w"),
                    h=_clamp(element.get("h", 10), 1, height, "h"),
                    fill=_colour(element.get("fill"), "fill", "#000000"),
                    stroke=(
                        f' stroke="{_colour(element.get("stroke"), "stroke", "#000000")}"'
                        if element.get("stroke")
                        else ""
                    ),
                )
            )
        elif kind == "circle":
            parts.append(
                '<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'.format(
                    cx=_clamp(element.get("x", 0), 0, width, "x"),
                    cy=_clamp(element.get("y", 0), 0, height, "y"),
                    r=_clamp(element.get("r", 10), 1, min(width, height), "r"),
                    fill=_colour(element.get("fill"), "fill", "#000000"),
                )
            )
        elif kind == "line":
            parts.append(
                '<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
                'stroke-width="{sw}"/>'.format(
                    x1=_clamp(element.get("x", 0), 0, width, "x"),
                    y1=_clamp(element.get("y", 0), 0, height, "y"),
                    x2=_clamp(element.get("x2", width), 0, width, "x2"),
                    y2=_clamp(element.get("y2", height), 0, height, "y2"),
                    stroke=_colour(element.get("stroke"), "stroke", "#000000"),
                    sw=_clamp(element.get("strokeWidth", 2), 1, 40, "strokeWidth"),
                )
            )
        elif kind == "text":
            text = element.get("text", "")
            if not isinstance(text, str) or len(text) > 500:
                raise SceneError("text must be a string of at most 500 characters")
            anchor = element.get("anchor", "start")
            if anchor not in {"start", "middle", "end"}:
                raise SceneError("anchor must be start, middle or end")
            family = element.get("fontFamily", "system-ui")
            if not isinstance(family, str) or not re.match(r"^[A-Za-z0-9 ,\-]{1,60}$", family):
                raise SceneError("fontFamily contains unsupported characters")
            parts.append(
                '<text x="{x}" y="{y}" font-size="{size}" font-family="{family}" '
                'fill="{fill}" text-anchor="{anchor}">{text}</text>'.format(
                    x=_clamp(element.get("x", 0), 0, width, "x"),
                    y=_clamp(element.get("y", 0), 0, height, "y"),
                    size=_clamp(element.get("fontSize", 24), 6, 400, "fontSize"),
                    family=family,
                    fill=_colour(element.get("fill"), "fill", "#111111"),
                    anchor=anchor,
                    text=_escape(text),
                )
            )
        else:
            raise SceneError(f"element {index}: unsupported type {kind!r}")
    parts.append("</svg>")
    return "".join(parts)
