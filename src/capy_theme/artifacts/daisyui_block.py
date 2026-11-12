"""The theme as daisyUI theme blocks, to compile into a project's own stylesheet.

For projects that build their Tailwind CSS with the theme in it instead of
loading capy-theme's stylesheet. Two blocks: "<slug>-light" (the default) and
"<slug>-dark" (used when the device prefers dark). Only daisyUI's own variables
(colors, radii, sizes, border, depth, noise) are included; fonts and capy-theme's
extras need {% theme_head %}.
"""

from ..colors.values import effective_values

# The variables a daisyUI theme block may set.
_PREFIXES = ("--color-", "--radius-", "--size-")
_EXACT = ("--border", "--depth", "--noise")


def build_block(theme, revision):
    """The CSS text: two @plugin "daisyui/theme" blocks for the published revision."""
    blocks = [
        f"/* {theme.name} (revision {revision.number}), exported by capy-theme as daisyUI\n"
        "   themes. Paste it into your Tailwind source after the daisyUI plugin. */"
    ]
    for scheme in ("light", "dark"):
        values = effective_values(revision.snapshot, scheme)
        lines = [
            '@plugin "daisyui/theme" {',
            f'  name: "{theme.slug}-{scheme}";',
            f"  default: {'true' if scheme == 'light' else 'false'};",
            f"  prefersdark: {'true' if scheme == 'dark' else 'false'};",
            f"  color-scheme: {scheme};",
        ]
        lines += [
            f"  {name}: {value};"
            for name, value in values.items()
            if name.startswith(_PREFIXES) or name in _EXACT
        ]
        lines.append("}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"
