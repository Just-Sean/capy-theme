"""Background images: an optional login-page background and page pattern.

They're CSS variables (`--capy-bg-login`, `--capy-bg-pattern`) in the theme's
stylesheet, plus two helper classes. A project uses them where it
wants: `class="capy-bg-pattern"` on <body>, or
`background-image: var(--capy-bg-login)` in its own CSS. Templates also get
their URLs (`theme.background_login_url`, `theme.background_pattern_url`).
"""

from ..images.logos import resolve
from ..storage import theme_storage

# slot: CSS variable
VARIABLES = {
    "background_login": "--capy-bg-login",
    "background_pattern": "--capy-bg-pattern",
}


def css_variables(snapshot):
    """{variable: 'url("...")'} for the chosen backgrounds ({} if none)."""
    variables = {}
    for slot, variable in VARIABLES.items():
        image = resolve(snapshot, slot)
        if image:
            url = theme_storage().url(image["file"]).replace("\\", "\\\\").replace('"', '\\"')
            variables[variable] = f'url("{url}")'
    return variables


def helper_css():
    """The helper classes. In @layer base, so a project's utility classes win."""
    return "\n".join(
        [
            "@layer base {",
            "  :root .capy-bg-login {",
            "    background-image: var(--capy-bg-login, none);",
            "    background-size: cover;",
            "    background-position: center;",
            "  }",
            "  :root .capy-bg-pattern {",
            "    background-image: var(--capy-bg-pattern, none);",
            "    background-repeat: repeat;",
            "  }",
            "}",
        ]
    )


def template_values(snapshot):
    """The background URLs for templates ("" if not set)."""
    values = {}
    for slot in VARIABLES:
        image = resolve(snapshot, slot)
        values[f"{slot}_url"] = theme_storage().url(image["file"]) if image else ""
    return values
