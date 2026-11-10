"""The CSS for a theme's fonts: @font-face rules, variables and element rules."""

from .library import stack


def font_css(fonts):
    """Return CSS lines for a snapshot's fonts: @font-face rules, variables and rules.

    - Body sets Tailwind's --font-sans (and body's font), mono sets --font-mono.
    - Headings and display get --capy-font-heading / --capy-font-display, used by
      h1–h6 and the .capy-display class.
    Element rules are in @layer base, so a project's own utility classes still win.
    They start with :root, so they beat Tailwind's reset (also in @layer base)
    even when Tailwind's stylesheet loads after this one.
    """
    if not fonts:
        return []
    lines = []
    seen = set()
    for font in fonts.values():
        for f in font["files"]:
            # The same file can serve several weights (variable fonts), so each
            # weight and style still gets its own rule; only exact repeats are skipped.
            key = (font["family"], f["url"], f["weight"], f["style"], f["unicode_range"])
            if key in seen:
                continue
            seen.add(key)
            lines += [
                "@font-face {",
                f'  font-family: "{font["family"].replace(chr(34), "")}";',
                f'  src: url("{f["url"]}") format("woff2");',
                f"  font-weight: {f['weight']};",
                f"  font-style: {f['style']};",
                "  font-display: swap;",
            ]
            if f["unicode_range"]:
                lines.append(f"  unicode-range: {f['unicode_range']};")
            lines.append("}")
    variables = {
        "body": ["--font-sans", "--capy-font-body"],
        "mono": ["--font-mono", "--capy-font-mono"],
        "heading": ["--capy-font-heading"],
        "display": ["--capy-font-display"],
    }
    lines.append(":root {")
    for role, font in fonts.items():
        for variable in variables.get(role, []):
            lines.append(f"  {variable}: {stack(role, font)};")
    lines.append("}")
    lines.append("@layer base {")
    if "body" in fonts:
        lines.append("  :root body { font-family: var(--capy-font-body); }")
    if "heading" in fonts:
        lines.append(
            "  :root :is(h1, h2, h3, h4, h5, h6) { font-family: var(--capy-font-heading); }"
        )
    if "mono" in fonts:
        lines.append("  :root :is(code, kbd, samp, pre) { font-family: var(--capy-font-mono); }")
    if "display" in fonts:
        lines.append("  :root .capy-display { font-family: var(--capy-font-display); }")
    lines.append("}")
    return lines
