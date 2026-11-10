"""The theme stylesheet: a published revision written out as CSS variables."""

import hashlib
import json
from importlib.metadata import version

from django.urls import reverse


def css_version(theme_id, number, snapshot):
    """Return the short hash that names a revision's stylesheet.

    It changes with every publish, so browsers can cache each stylesheet URL
    for a year. Kept in step with migration 0004, which fills it in for
    revisions published before it existed.
    """
    data = json.dumps({"theme": theme_id, "number": number, "snapshot": snapshot}, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:12]


def render_css(revision):
    """Return the CSS for a revision: light values by default, dark ones in dark mode.

    The rules aren't in a CSS layer, so they override daisyUI's own theme rules
    (which are in `@layer base`) wherever the stylesheet is loaded.
    """
    snapshot = revision.snapshot
    lines = [
        f"/* capy-theme: {revision.theme.name}, revision {revision.number} */",
        ":root {",
        *_block("light", snapshot["light_values"], indent="  "),
        "}",
        "@media (prefers-color-scheme: dark) {",
        "  :root {",
        *_block("dark", snapshot["dark_values"], indent="    "),
        "  }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def _block(scheme, values, indent):
    yield f"{indent}color-scheme: {scheme};"
    for name, value in values.items():
        yield f"{indent}{name}: {value};"


def stylesheet_url(revision):
    """Return the URL pages use for a revision's stylesheet.

    It ends with ?v=<capy-theme version>. Browsers cache each stylesheet for a
    year, so when an upgrade changes how render_css() writes the CSS, the new
    version in the URL makes them fetch it again. The view ignores ?v=.
    """
    url = reverse("capy_theme:theme_css", args=[revision.css_version])
    return f"{url}?v={version('capy-theme')}"
