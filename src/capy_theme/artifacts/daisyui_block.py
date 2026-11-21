"""The theme as a daisyUI theme block, to compile into a project's own stylesheet.

For projects that build their Tailwind CSS with the theme in it instead of
loading capy-theme's stylesheet. One block named "<slug>", the default when the
theme is light and prefersdark when it's dark. Only daisyUI's own variables
(colors, radii, sizes, border, depth, noise) are included; fonts and capy-theme's
extras come from the theme's assets (``get_artifacts`` / the per-theme API).
"""

from ..colors.values import effective_values
from ..css.stylesheet import css_comment

# The variables a daisyUI theme block may set.
_PREFIXES = ("--color-", "--radius-", "--size-")
_EXACT = ("--border", "--depth", "--noise")


def build_block(theme, revision):
    """The CSS text: an @plugin "daisyui/theme" block for the published revision."""
    scheme = revision.snapshot["scheme"]
    values = effective_values(revision.snapshot)
    lines = [
        '@plugin "daisyui/theme" {',
        f'  name: "{theme.slug}";',
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
    header = (
        f"/* {css_comment(theme.name)} (revision {revision.number}), exported by capy-theme as a\n"
        "   daisyUI theme. Paste it into your Tailwind source after the daisyUI plugin. */"
    )
    return header + "\n\n" + "\n".join(lines) + "\n"
