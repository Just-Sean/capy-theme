"""The type scale: base text size, heading sizes, line height and heading weight.

Stored in Theme.settings["type"]. Unset values leave the project's own styles alone.
"""

# name: (label, unit, minimum, maximum, step, help)
TYPE_SETTINGS = {
    "base_size": (
        "Base text size",
        "px",
        14,
        24,
        0.5,
        "The size of body text. Everything sized in rem scales with it. At least 14px, "
        "so text stays readable.",
    ),
    "scale": (
        "Heading scale",
        "×",
        1.05,
        1.6,
        0.01,
        "How much bigger each heading level is than the next (h6 is the base size). "
        "1.25 is a common choice.",
    ),
    "line_height": (
        "Line height",
        "×",
        1.1,
        2.2,
        0.05,
        "Space between lines of body text, e.g. 1.5.",
    ),
    "heading_weight": (
        "Heading weight",
        "",
        100,
        900,
        100,
        "400 is regular, 700 bold.",
    ),
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
