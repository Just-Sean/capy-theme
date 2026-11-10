"""The type scale: base text size, heading sizes, line height and heading weight.

Stored in Theme.settings["type"]. Unset values leave the project's own styles alone.
"""

import json
from pathlib import Path

# From type_settings.json. name: (label, unit, min, max, step, help)
TYPE_SETTINGS = {
    name: (s["label"], s["unit"], s["min"], s["max"], s["step"], s["help"])
    for name, s in json.loads(
        Path(__file__).with_name("type_settings.json").read_text(encoding="utf-8")
    )["settings"].items()
}
MINIMUM_BASE_SIZE = TYPE_SETTINGS["base_size"][2]


def heading_sizes(scale):
    """Return {"h1": rem, ..., "h6": rem}: h6 is 1rem, each level up multiplies by scale."""
    return {f"h{level}": round(scale ** (6 - level), 4) for level in range(1, 7)}


def type_css(settings):
    """CSS lines for a theme's type settings (empty if none are set).

    Variables are unlayered; element rules are in @layer base, so a project's own
    utility classes (e.g. text-5xl, font-bold) still win. They start with :root, so
    they beat Tailwind's reset (also in @layer base) whatever the loading order.
    """
    chosen = settings.get("type", {})
    if not chosen:
        return []
    variables, rules = [], []
    if "base_size" in chosen:
        variables.append(f"  --capy-base-size: {_number(chosen['base_size'])}px;")
        rules.append("  :root { font-size: var(--capy-base-size); }")
    if "line_height" in chosen:
        variables.append(f"  --capy-line-height: {_number(chosen['line_height'])};")
        rules.append("  :root body { line-height: var(--capy-line-height); }")
    if "scale" in chosen:
        for tag, size in heading_sizes(chosen["scale"]).items():
            variables.append(f"  --capy-{tag}: {_number(size)}rem;")
            rules.append(f"  :root {tag} {{ font-size: var(--capy-{tag}); }}")
    if "heading_weight" in chosen:
        variables.append(f"  --capy-heading-weight: {int(chosen['heading_weight'])};")
        rules.append(
            "  :root :is(h1, h2, h3, h4, h5, h6) { font-weight: var(--capy-heading-weight); }"
        )
    return [":root {", *variables, "}", "@layer base {", *rules, "}"]


def _number(value):
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return text or "0"
