"""Tests for SVG cleaning (issue #33)."""

import xml.etree.ElementTree as ET

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from capy_theme.images.svg import clean_svg
from capy_theme.images.uploads import add_asset, prepare_image
from capy_theme.models import Theme

NS = 'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'


def svg(body, attrs='viewBox="0 0 40 20"'):
    return f"<svg {NS} {attrs}>{body}</svg>".encode()


def cleaned(body, attrs='viewBox="0 0 40 20"'):
    return clean_svg(svg(body, attrs))[0].decode()


def test_the_issue_check_script_is_removed():
    out = cleaned('<rect width="40" height="20" fill="red"/><script>alert("hi")</script>')
    assert "script" not in out
    assert "alert" not in out
    assert '<rect width="40" height="20" fill="red" />' in out


def test_event_handlers_are_removed():
    out = cleaned('<rect onclick="alert(1)" width="4"/>', attrs='onload="alert(2)"')
    assert "alert" not in out
    assert "onclick" not in out and "onload" not in out
    assert 'width="4"' in out


def test_embedded_html_is_removed():
    out = cleaned(
        '<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">'
        "<iframe src='https://evil.example'/></div></foreignObject><circle r='3'/>"
    )
    assert "foreignObject" not in out and "iframe" not in out and "evil" not in out
    assert "circle" in out


def test_external_references_are_removed():
    out = cleaned(
        '<image href="https://evil.example/track.png" width="4" height="4"/>'
        '<use xlink:href="https://evil.example/sprite.svg#a"/>'
        '<rect fill="url(https://evil.example/x)" width="4"/>'
        '<rect style="fill: url(\'//evil.example/y\')" width="5"/>'
        "<style>@import url(https://evil.example/a.css); rect { fill: red }</style>"
    )
    assert "evil" not in out
    assert "@import" not in out


def test_internal_references_are_kept():
    out = cleaned(
        '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient>'
        '<path id="p" d="M0 0h10"/></defs>'
        '<rect fill="url(#g)" width="40" height="20"/><use href="#p"/><use xlink:href="#p"/>'
        "<style>.a { fill: url(#g) }</style>"
    )
    assert 'fill="url(#g)"' in out
    assert 'href="#p"' in out
    assert 'xlink:href="#p"' in out
    assert ".a { fill: url(#g) }" in out


def test_javascript_links_are_removed_but_their_contents_kept():
    out = cleaned('<a xlink:href="javascript:alert(1)"><text x="1">Brand</text></a>')
    assert "javascript" not in out and "<a" not in out
    assert ">Brand</text>" in out


def test_embedded_raster_images_are_kept():
    data = "data:image/png;base64,iVBORw0KGgo="
    assert data in cleaned(f'<image href="{data}" width="4" height="4"/>')
    assert "data:" not in cleaned('<image href="data:image/svg+xml;base64,PHN2Zz4=" />')
    assert "data:" not in cleaned('<rect fill="data:text/html,hi" />')


def test_animation_and_other_namespaces_are_removed():
    out = cleaned(
        '<rect width="4"><set attributeName="fill" to="red"/>'
        '<animate attributeName="href" values="javascript:alert(1)"/></rect>'
        '<sodipodi:namedview xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"/>'
    )
    assert "<set" not in out
    assert "animate" not in out and "sodipodi" not in out


def test_text_after_a_removed_element_is_kept():
    out = cleaned("<text>Capy<script>x()</script> Theme</text>")
    assert ">Capy Theme</text>" in out


def test_doctypes_and_entities_are_rejected():
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaaaaaaaa">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg">&a;</svg>'
    )
    with pytest.raises(ValidationError, match="DOCTYPE"):
        clean_svg(bomb)


def test_utf16_cant_hide_a_doctype():
    data = '<!DOCTYPE svg [<!ENTITY a "x">]><svg xmlns="http://www.w3.org/2000/svg"/>'
    with pytest.raises(ValidationError, match="UTF-8"):
        clean_svg(data.encode("utf-16"))


@pytest.mark.parametrize(
    "data",
    [b"<html><body>hi</body></html>", b"<svg", b"<not xml at all", b"<?xml version='1.0'?>"],
)
def test_other_text_is_rejected(data):
    with pytest.raises(ValidationError):
        clean_svg(data)


def test_svg_without_xmlns_gets_one():
    out = clean_svg(b'<svg width="10" height="5"><rect width="10" height="5"/></svg>')[0]
    root = ET.fromstring(out)  # noqa: S314 (our own output)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root[0].tag == "{http://www.w3.org/2000/svg}rect"


def test_size_comes_from_the_viewbox_or_width_and_height():
    assert clean_svg(svg("", 'viewBox="0 0 120 30"'))[1:] == (120, 30)
    assert clean_svg(svg("", 'width="64px" height="32"'))[1:] == (64, 32)
    assert clean_svg(svg("", 'width="100%"'))[1:] == (0, 0)


# Uploading


def test_prepare_image_takes_svgs():
    clean = prepare_image(svg("<script>x()</script><circle r='3'/>"), "logo.png", "logo_main")
    assert clean["content_type"] == "image/svg+xml"
    assert clean["file"].name == "logo.svg"
    assert b"script" not in clean["file"].read()
    assert (clean["width"], clean["height"]) == (40, 20)


@pytest.mark.django_db
def test_an_uploaded_svg_is_stored_clean(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    theme = Theme.objects.create(name="Main", slug="main")
    upload = SimpleUploadedFile("logo.svg", svg("<script>alert(1)</script><rect width='4'/>"))
    asset = add_asset(theme, "logo_main", "light", upload, "Logo")
    with asset.original.open("rb") as f:
        stored = f.read()
    assert b"script" not in stored and b"<rect" in stored
    assert asset.content_type == "image/svg+xml"


@pytest.mark.parametrize("slot", ["logo_email", "social", "icon"])
def test_slots_that_cant_use_svg_ask_for_a_png(slot):
    with pytest.raises(ValidationError, match="Upload a PNG or JPEG instead"):
        prepare_image(svg("<rect width='4'/>"), "logo.svg", slot)


@pytest.mark.django_db
def test_editor_marks_slots_without_svg():
    from capy_theme.editor.state import controls

    slots = {s["name"]: s["svg"] for s in controls()["image_slots"]}
    assert slots["logo_main"] and slots["logo_print"]
    assert not slots["logo_email"] and not slots["social"] and not slots["icon"]


# Limits and edge cases (issue #181).


def test_too_many_elements_are_rejected():
    # A size guard: huge SVGs could slow every page that shows them.
    from capy_theme.images.svg import MAX_ELEMENTS

    assert clean_svg(svg("<g/>" * (MAX_ELEMENTS - 1)))  # the <svg> itself is one
    with pytest.raises(ValidationError, match=f"more than {MAX_ELEMENTS} elements"):
        clean_svg(svg("<g/>" * MAX_ELEMENTS))


def test_text_after_an_empty_link_is_kept():
    out = cleaned('<text>A<a href="javascript:alert(1)"></a>B</text>')
    assert "javascript" not in out and ">AB<" in out


def test_text_after_a_removed_element_joins_the_previous_sibling():
    out = cleaned("<text><tspan>A</tspan><script>alert(1)</script>B</text>")
    assert "script" not in out and "</tspan>B</text>" in out


def test_size_falls_back_to_width_and_height_when_the_viewbox_isnt_numbers():
    assert clean_svg(svg("", 'viewBox="a b c d" width="30" height="12px"'))[1:] == (30, 12)


def test_defusedxml_refuses_entities_even_without_the_first_check(monkeypatch):
    # Issue #219: the DOCTYPE check catches these first, with a clear message;
    # defusedxml is a second layer. With the first check switched off, a classic
    # "billion laughs" entity bomb is still refused, never expanded.
    import types

    import capy_theme.images.svg as svg_module

    # Only the SVG module's view of `re` (patching re.search itself would also
    # break pytest's own message matching).
    monkeypatch.setattr(
        svg_module, "re", types.SimpleNamespace(search=lambda *a, **k: None, IGNORECASE=0)
    )
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaaaaaaaa">'
        '<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">'
        '<!ENTITY c "&b;&b;&b;&b;&b;&b;&b;&b;&b;&b;">]>'
        f"<svg {NS}><text>&c;</text></svg>"
    ).encode()
    with pytest.raises(ValidationError, match="DOCTYPE or entities"):
        clean_svg(bomb)
