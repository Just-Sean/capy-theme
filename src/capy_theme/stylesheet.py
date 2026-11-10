"""The theme stylesheet: a published revision written out as CSS variables."""

import hashlib
import json


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

    - The page uses the light values, or the dark ones when the visitor's device
      is in dark mode.
    - Any element with data-theme="capy-light" or "capy-dark" is forced into that
      mode, whatever the device setting. The showcase uses this to show both side
      by side, and the light/dark toggle (6.1) will too.

    The rules aren't in a CSS layer, so they override daisyUI's own theme rules
    (which are in `@layer base`) wherever the stylesheet is loaded.
    """
    snapshot = revision.snapshot
    light, dark = snapshot["light_values"], snapshot["dark_values"]
    lines = [
        f"/* capy-theme: {revision.theme.name}, revision {revision.number} */",
        ":root {",
        *_block("light", light, indent="  "),
        "}",
        "@media (prefers-color-scheme: dark) {",
        "  :root {",
        *_block("dark", dark, indent="    "),
        "  }",
        "}",
        # After the rules above, so these win over them.
        '[data-theme="capy-light"] {',
        *_block("light", light, indent="  "),
        "}",
        '[data-theme="capy-dark"] {',
        *_block("dark", dark, indent="  "),
        "}",
    ]
    return "\n".join(lines) + "\n"


def _block(scheme, values, indent):
    yield f"{indent}color-scheme: {scheme};"
    for name, value in values.items():
        yield f"{indent}{name}: {value};"
