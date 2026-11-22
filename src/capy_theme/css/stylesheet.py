"""The theme stylesheet: a published revision written out as CSS variables."""

import hashlib
import json
from importlib.metadata import version

from django.urls import reverse

from ..colors.color_math import focus_color
from ..colors.values import effective_values
from ..fonts.css import font_css
from ..images.logo_tag import logo_css
from .accessibility import accessibility_css
from .backgrounds import css_variables as background_variables
from .backgrounds import helper_css as background_css
from .typography import type_css

# The class a consumer forces a slot with: <html data-theme="capy-light"> or
# "capy-dark". A theme renders under the one for its own scheme.
FORCE_THEME = {"light": "capy-light", "dark": "capy-dark"}


def css_version(theme_id, number, snapshot):
    """Return the short hash that names a revision's stylesheet.

    It changes with every publish, so browsers can cache each stylesheet URL
    for a year. Kept in step with migration 0004, which fills it in for
    revisions published before it existed.
    """
    data = json.dumps({"theme": theme_id, "number": number, "snapshot": snapshot}, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:12]


def render_css(revision):
    """Return the CSS for a revision.

    A theme is a single scheme (light or dark). Its stylesheet renders only that
    scheme, and a consumer loads a light theme's sheet and a dark theme's sheet
    together (the light slot and the dark slot) so the two compose:

    - A **light** theme renders at ``:root`` (the default) and at
      ``:root[data-theme="capy-light"]`` (forced light).
    - A **dark** theme renders at ``:root`` under ``@media (prefers-color-scheme:
      dark)`` (device dark) and at ``:root[data-theme="capy-dark"]`` (forced dark).

    So with both loaded: the device setting picks light or dark on its own, and
    setting ``data-theme="capy-light"`` / ``"capy-dark"`` on <html> forces one.
    The forced rules use ``:root[data-theme=…]`` (higher specificity than
    ``:root``), so the result doesn't depend on which sheet loads first.

    The rules aren't in a CSS layer, so they override daisyUI's own theme rules
    (which are in `@layer base`) wherever the stylesheet is loaded.
    """
    return snapshot_css(
        revision.snapshot, f"capy-theme: {revision.theme.name}, revision {revision.number}"
    )


def css_comment(text):
    """`text` made safe inside /* ... */: a "*/" in it would end the comment early
    and turn the rest into real CSS (e.g. a theme named "x */ @import ...") (#253)."""
    return text.replace("*/", "* /")


def snapshot_css(snapshot, comment):
    """Return the CSS for a snapshot of a theme's look (published or draft).

    Used for published revisions and, in the editor, for unsaved drafts, so the
    two always match. See render_css for how a light and a dark theme compose.
    """
    scheme = snapshot["scheme"]
    forced = FORCE_THEME[scheme]
    # Colors, plus the background image variables (none if not chosen).
    values = effective_values(snapshot) | background_variables(snapshot)
    lines = [f"/* {css_comment(comment)} */"]
    if scheme == "dark":
        # The device default (only when a light sheet hasn't forced light), then
        # the forced rule.
        lines += [
            "@media (prefers-color-scheme: dark) {",
            '  :root:not([data-theme="capy-light"]) {',
            *_block(scheme, values, indent="    "),
            "  }",
            "}",
            f':root[data-theme="{forced}"] {{',
            *_block(scheme, values, indent="  "),
            "}",
        ]
    else:
        # The default, then the forced rule (higher specificity than :root).
        lines += [
            ":root {",
            *_block(scheme, values, indent="  "),
            "}",
            f':root[data-theme="{forced}"] {{',
            *_block(scheme, values, indent="  "),
            "}",
        ]
    lines += [
        # A keyboard-focus outline that stays visible on the theme's colors.
        ":focus-visible {",
        "  outline: 2px solid var(--capy-focus);",
        "  outline-offset: 2px;",
        "}",
        *font_css(snapshot.get("fonts", {})),
        *type_css(snapshot.get("settings", {})),
        logo_css(snapshot),
        background_css(),
        accessibility_css(),
    ]
    return "\n".join(lines) + "\n"


def _block(scheme, values, indent):
    yield f"{indent}color-scheme: {scheme};"
    for name, value in values.items():
        yield f"{indent}{name}: {value};"
    yield f"{indent}--capy-focus: {focus_color(values)};"


def stylesheet_url(revision):
    """Return the URL pages use for a revision's stylesheet.

    It ends with ?v=<capy-theme version>. Browsers cache each stylesheet for a
    year, so when an upgrade changes how render_css() writes the CSS, the new
    version in the URL makes them fetch it again. The view ignores ?v=.
    """
    url = reverse("capy_theme:theme_css", args=[revision.css_version])
    return f"{url}?v={version('capy-theme')}"
