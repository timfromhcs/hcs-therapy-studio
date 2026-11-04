"""SVG sanitisation and the constrained scene renderer."""

from __future__ import annotations

import pytest

from hcs_therapy.svg import SceneError, SvgError, render_scene, sanitize_svg

CLEAN = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<rect x="1" y="2" width="10" height="10" fill="#ff0000"/></svg>'
)


def test_clean_svg_survives_untouched() -> None:
    result = sanitize_svg(CLEAN)
    assert result.clean
    assert "rect" in result.svg


def test_script_element_is_removed() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        "<script>alert(1)</script><rect width='5' height='5'/></svg>"
    )
    result = sanitize_svg(svg)
    assert "script" not in result.svg
    assert "element:script" in result.removed


def test_event_handlers_are_removed() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<rect width="5" height="5" onload="alert(1)"/></svg>'
    )
    result = sanitize_svg(svg)
    assert "onload" not in result.svg
    assert "attribute:onload" in result.removed


def test_foreign_object_is_removed() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">x</div></foreignObject></svg>'
    )
    assert "foreignObject" not in sanitize_svg(svg).svg


def test_javascript_href_is_removed() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<a href="javascript:alert(1)"><rect width="5" height="5"/></a></svg>'
    )
    result = sanitize_svg(svg)
    assert "javascript" not in result.svg


def test_doctype_and_entity_declarations_are_rejected() -> None:
    with pytest.raises(SvgError, match="DOCTYPE"):
        sanitize_svg('<!DOCTYPE svg [<!ENTITY x "y">]><svg/>')


def test_oversized_input_is_rejected() -> None:
    with pytest.raises(SvgError, match="MiB"):
        sanitize_svg("<svg>" + "a" * (2 * 1024 * 1024) + "</svg>")


def test_malformed_xml_is_rejected() -> None:
    with pytest.raises(SvgError, match="well-formed"):
        sanitize_svg("<svg><rect></svg>")


def test_missing_dimensions_are_rejected() -> None:
    with pytest.raises(SvgError, match="viewBox"):
        sanitize_svg('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')


def test_empty_input_is_rejected() -> None:
    with pytest.raises(SvgError):
        sanitize_svg("   ")


# ---------------------------------------------------------------------------
# scene renderer
# ---------------------------------------------------------------------------


def test_scene_renders_valid_svg() -> None:
    svg = render_scene(
        {
            "width": 400,
            "height": 300,
            "background": "#ffffff",
            "elements": [
                {"type": "rect", "x": 10, "y": 10, "w": 100, "h": 50, "fill": "#333333"},
                {"type": "text", "x": 20, "y": 100, "text": "Hallo Welt", "fontSize": 24},
                {"type": "circle", "x": 200, "y": 200, "r": 30, "fill": "#88aaff"},
            ],
        }
    )
    assert svg.startswith("<svg")
    assert 'viewBox="0 0 400 300"' in svg
    assert "Hallo Welt" in svg


def test_scene_escapes_text_injection() -> None:
    svg = render_scene(
        {
            "width": 200,
            "height": 200,
            "elements": [{"type": "text", "x": 5, "y": 20, "text": "<script>alert(1)</script>"}],
        }
    )
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_scene_rejects_out_of_range_values() -> None:
    with pytest.raises(SceneError):
        render_scene({"width": 50, "height": 100, "elements": []})
    with pytest.raises(SceneError):
        render_scene({"width": 200, "height": 200, "elements": [{"type": "rect", "x": -5}]})


def test_scene_rejects_bad_colour() -> None:
    with pytest.raises(SceneError, match="colour"):
        render_scene({"width": 200, "height": 200, "elements": [{"type": "rect", "fill": "red"}]})


def test_scene_rejects_unknown_element() -> None:
    with pytest.raises(SceneError, match="unsupported"):
        render_scene({"width": 200, "height": 200, "elements": [{"type": "image"}]})


def test_scene_rejects_too_many_elements() -> None:
    with pytest.raises(SceneError, match="200"):
        render_scene(
            {
                "width": 200,
                "height": 200,
                "elements": [{"type": "rect"} for _ in range(201)],
            }
        )


def test_scene_output_is_itself_sanitisable() -> None:
    svg = render_scene({"width": 300, "height": 300, "elements": [{"type": "rect"}]})
    assert sanitize_svg(svg).clean
