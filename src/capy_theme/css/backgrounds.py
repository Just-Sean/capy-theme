"""Background images: an optional login-page background and page pattern.

They're CSS variables (`--capy-bg-login`, `--capy-bg-pattern`) in the theme's
stylesheet, set per mode, plus two helper classes. A project uses them where it
wants: `class="capy-bg-pattern"` on <body>, or
`background-image: var(--capy-bg-login)` in its own CSS. Templates also get
their URLs (`theme.background_login_url`, `theme.background_pattern_url`).
"""

from django.core.files.storage import default_storage

from ..images.logos import resolve

# slot: CSS variable
VARIABLES = {
    "background_login": "--capy-bg-login",
    "background_pattern": "--capy-bg-pattern",
}


def css_variables(snapshot, scheme):
    """{variable: 'url("...")'} for the chosen backgrounds in a mode ({} if none).

    Dark mode uses the light image if there's no dark one.
    """
    variables = {}
    for slot, variable in VARIABLES.items():
        image = resolve(snapshot, slot, scheme)
        if image:
            url = default_storage.url(image["file"]).replace("\\", "\\\\").replace('"', '\\"')
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
    """The light-mode background URLs for templates ("" if not set)."""
    values = {}
    for slot in VARIABLES:
        image = resolve(snapshot, slot, "light")
        values[f"{slot}_url"] = default_storage.url(image["file"]) if image else ""
    return values
