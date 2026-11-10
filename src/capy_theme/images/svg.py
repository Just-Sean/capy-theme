"""Cleaning uploaded SVGs with a strict allow-list.

An SVG is XML that browsers run like a small web page: it can contain scripts,
event handlers (onload=...), links to other sites and embedded HTML. clean_svg()
keeps only the drawing elements and attributes listed in svg_allowlist.json and drops
everything else, so what's stored can only draw shapes, text and gradients.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from django.core.exceptions import ValidationError

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)

MAX_ELEMENTS = 20000

# What SVGs may keep, from svg_allowlist.json ("xlink:" and "xml:" are namespaces).
_ALLOW = json.loads(Path(__file__).with_name("svg_allowlist.json").read_text(encoding="utf-8"))
_NAMESPACES = {"xlink:": f"{{{XLINK}}}", "xml:": f"{{{XML}}}"}


def _expand(name):
    for prefix, namespace in _NAMESPACES.items():
        if name.startswith(prefix):
            return namespace + name.removeprefix(prefix)
    return name


# Drawing elements. Anything else (script, foreignObject, iframe, animation,
# elements from other namespaces) is removed with everything inside it.
ELEMENTS = set(_ALLOW["elements"])

# Links (<a>) are removed but what they contain is kept.
UNWRAP = set(_ALLOW["unwrap"])

ATTRIBUTES = {_expand(name) for name in _ALLOW["attributes"]}

HREF = {"href", f"{{{XLINK}}}href"}
# <image> may only embed raster images inside the file, never load one.
DATA_IMAGE = re.compile(r"^data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\s]+$")
# In attribute values and CSS: url() may only point inside the file (url(#id)).
UNSAFE_CSS = re.compile(
    r"@import|url\(\s*['\"]?\s*[^#'\"\s)]|expression\s*\(|javascript:|behavior\s*:|-moz-binding",
    re.IGNORECASE,
)


def clean_svg(data):
    """Return (clean SVG bytes, width, height), or raise ValidationError.

    Width and height come from the viewBox (or the width and height attributes)
    and are 0 if the SVG doesn't say.
    """
    not_svg = "That file isn't a valid SVG image."
    try:
        text = data.decode("utf-8-sig")  # UTF-8 only, so the checks below see the real text
    except UnicodeDecodeError as error:
        raise ValidationError("SVGs must be saved as UTF-8.") from error
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.IGNORECASE):
        # Entities can expand to huge sizes or read local files; logos don't need them.
        raise ValidationError("SVGs with a DOCTYPE or entities aren't accepted.")
    try:
        # Safe without defusedxml: its protections are against DOCTYPEs and
        # entities, which are rejected above (and expat never fetches anything).
        root = ET.fromstring(text)  # noqa: S314
    except ET.ParseError as error:
        raise ValidationError(not_svg) from error
    if root.tag not in (f"{{{SVG}}}svg", "svg"):
        raise ValidationError(not_svg)
    if sum(1 for _ in root.iter()) > MAX_ELEMENTS:
        raise ValidationError(f"The SVG has more than {MAX_ELEMENTS} elements.")
    # Some editors leave out xmlns; browsers need it, so it's added.
    plain = root.tag == "svg"
    _clean(root, plain)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), *_size(root)


def _name(tag, plain):
    """The SVG element name, or None if it's from another namespace."""
    if tag.startswith(f"{{{SVG}}}"):
        return tag[len(SVG) + 2 :]
    if plain and not tag.startswith("{"):
        return tag
    return None


def _clean(element, plain):
    name = _name(element.tag, plain)
    element.tag = f"{{{SVG}}}{name}"
    for attribute, value in list(element.attrib.items()):
        if not _attribute_ok(name, attribute, value):
            del element.attrib[attribute]
    if name == "style" and UNSAFE_CSS.search(element.text or ""):
        element.text = ""
    index = 0
    while index < len(element):
        child = element[index]
        child_name = _name(child.tag, plain) if isinstance(child.tag, str) else None
        if child_name in ELEMENTS:
            _clean(child, plain)
            index += 1
        elif child_name in UNWRAP:
            _clean_unwrapped(element, index, child, plain)
        else:
            _remove(element, index)


def _attribute_ok(element, attribute, value):
    if attribute not in ATTRIBUTES:
        return False  # also every on* event handler
    if attribute in HREF:
        if element == "image":
            return bool(DATA_IMAGE.match(value.strip()))
        return value.strip().startswith("#")
    lowered = value.lower()
    if "javascript:" in lowered or "data:" in lowered:
        return False
    return not UNSAFE_CSS.search(value)


def _remove(parent, index):
    """Remove parent[index] and everything in it, keeping the text after it."""
    child = parent[index]
    _keep_tail(parent, index, child.tail)
    del parent[index]


def _clean_unwrapped(parent, index, link, plain):
    """Replace a link with its contents."""
    _keep_tail(parent, index, link.text)
    tail = link.tail
    children = list(link)
    del parent[index]
    for offset, child in enumerate(children):
        parent.insert(index + offset, child)
    if children:
        children[-1].tail = (children[-1].tail or "") + (tail or "")
    else:
        _keep_tail(parent, index, tail)


def _keep_tail(parent, index, text):
    if not text:
        return
    if index == 0:
        parent.text = (parent.text or "") + text
    else:
        parent[index - 1].tail = (parent[index - 1].tail or "") + text


def _size(root):
    numbers = re.split(r"[\s,]+", root.get("viewBox", "").strip())
    if len(numbers) == 4:
        try:
            return round(float(numbers[2])), round(float(numbers[3]))
        except ValueError:
            pass
    sizes = []
    for attribute in ("width", "height"):
        match = re.fullmatch(r"\s*(\d+(\.\d+)?)\s*(px)?\s*", root.get(attribute, ""))
        sizes.append(round(float(match.group(1))) if match else 0)
    return tuple(sizes)
