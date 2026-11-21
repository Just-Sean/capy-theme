"""Template tags for putting the active theme on a page.

Load them with `{% load capy_theme %}`. Put `{% theme_html_attrs %}` inside the
page's <html> tag and `{% theme_head %}` inside <head>. `{% theme_logo %}` and
`{% theme_mode_toggle %}` go wherever they should appear. The README shows a full example.
"""

import json

from django import template
from django.middleware.csp import get_nonce
from django.template import TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from ..artifacts import get_artifacts
from ..css.custom import custom_css_url
from ..css.stylesheet import stylesheet_url
from ..editor.access import can_edit
from ..editor.mount import mount as editor_mount
from ..fonts.library import external_stylesheets, preload_urls
from ..images.icons import head_links as icon_links
from ..images.logo_tag import logo_html
from ..images.logos import LOGO_SLOTS
from ..themes.active import (
    CHOICE_COOKIE,
    get_active_theme,
    offered_themes,
    picker_state,
    visitor_themes_allowed,
)
from ..themes.branding import branding
from ..themes.mode import (
    MODE_LABELS,
    MODES,
    current_mode,
    head_script,
    html_theme_value,
    mode_settings,
    mode_state,
    theme_color_meta,
)

register = template.Library()


@register.simple_tag(takes_context=True)
def theme_head(context):
    """Output the active theme's stylesheet link, theme-color tags and mode script.

    Also the theme-color meta tags (the browser's address-bar color) and, for
    staff who can edit, the live editor. Outputs nothing (except the editor)
    if no theme is active. The script carries the CSP nonce when
    Django's CSP middleware is on.
    """
    request = context.get("request")
    editor = mark_safe(editor_mount(request))  # noqa: S308 (rendered template)
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        return editor
    revision = theme.live_revision
    # Django's nonce is lazy and counts as false until something reads it, so test
    # for the CSP middleware (a nonce object exists) rather than the nonce's truth.
    # Reading it here generates it, and the middleware then puts it in the header.
    nonce = get_nonce(request) if request is not None else None
    nonce_attr = format_html(' nonce="{}"', str(nonce)) if nonce is not None else ""
    fonts = revision.snapshot.get("fonts")
    return format_html(
        '{}{}<link rel="stylesheet" href="{}">\n{}{}{}<script{}>{}</script>{}',
        format_html_join(
            "",
            '<link rel="preload" href="{}" as="font" type="font/woff2" crossorigin>\n',
            ((url,) for url in preload_urls(fonts)),
        ),
        format_html_join(
            "",
            '<link rel="stylesheet" href="{}">\n',
            ((url,) for url in external_stylesheets(fonts)),
        ),
        stylesheet_url(revision),
        _custom_css_link(revision),
        theme_color_meta(revision, current_mode(request, revision)),
        icon_links(revision.snapshot),
        nonce_attr,
        mark_safe(head_script(revision)),  # noqa: S308 (built from fixed text and JSON values)
        editor,
    )


def _custom_css_link(revision):
    """The <link> to the revision's custom CSS, after the theme stylesheet ("" if none)."""
    url = custom_css_url(revision)
    return format_html('<link rel="stylesheet" href="{}">\n', url) if url else ""


@register.simple_tag(takes_context=True)
def theme_picker(context):
    """Output a list of the themes visitors may choose, plus "Site default".

    Each is a link that sets the choice and reloads the page, so it works without
    JavaScript. Outputs nothing if no theme is offered or the project turns visitor
    themes off (CAPY_THEME_VISITOR_THEMES = False).
    """
    request = context.get("request")
    offered = offered_themes()
    if not offered or not visitor_themes_allowed():
        return ""
    chosen = request.COOKIES.get(CHOICE_COOKIE, "") if request is not None else ""
    if chosen not in {theme.slug for theme in offered}:
        chosen = "default"
    return render_to_string(
        "capy_theme/theme_picker.html",
        {
            "options": [("default", "Site default")] + [(t.slug, t.name) for t in offered],
            "current": chosen,
            "next": request.get_full_path() if request is not None else "/",
        },
    )


@register.simple_tag(takes_context=True)
def theme_artifacts(context):
    """The active theme's artifacts (see capy_theme.artifacts), for templates.

    `{% theme_artifacts as artifacts %}` then e.g.
    `{{ artifacts.logos.logo_email.light.url }}` or `{{ artifacts.icons.icon-192.png }}`
    (use `artifacts.icons|capy_get:"icon-192.png"` for names with dots).
    None if no theme is published. URLs are absolute.
    """
    return get_artifacts(context.get("request"))


@register.simple_tag(takes_context=True)
def theme_mode_state(context):
    """The light/dark/auto state as data, for a consumer to render its own control.

    ``{% theme_mode_state as mode %}``, then e.g. ``{{ mode.current }}``,
    ``{{ mode.next.url }}``, or loop ``mode.options`` ({value, label, url, current}).
    None if no theme is active. See docs/artifacts.md.
    """
    request = context.get("request")
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        return None
    return mode_state(request, theme.live_revision)


@register.simple_tag(takes_context=True)
def theme_picker_state(context):
    """The themes a visitor may choose, as data, for a consumer to render its own picker.

    ``{% theme_picker_state as picker %}``, then loop ``picker.options``
    ({value, label, url, current}); show it only when there's more than one. None if no
    theme is active. See docs/artifacts.md.
    """
    request = context.get("request")
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        return None
    return picker_state(request)


@register.simple_tag(takes_context=True)
def theme_html_attrs(context):
    """Output attributes for the page's <html> tag.

    ``data-theme="capy-light"`` / ``"capy-dark"`` forces a mode (the theme's default or
    the visitor's choice); for "auto" there's no data-theme and the stylesheet follows
    the visitor's device. ``data-capy-color-mode`` always carries the current mode
    (light/dark/auto) so a consumer can style a control (e.g. a mode-toggle icon) by it.
    """
    request = context.get("request")
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        return ""
    mode = current_mode(request, theme.live_revision)
    forced = html_theme_value(mode)
    if forced:
        return format_html('data-theme="{}" data-capy-color-mode="{}"', forced, mode)
    return format_html('data-capy-color-mode="{}"', mode)


@register.simple_tag(takes_context=True)
def theme_mode_toggle(context):
    """Output Light / Dark / Auto buttons for visitors, if the theme allows switching."""
    request = context.get("request")
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        return ""
    if not mode_settings(theme.live_revision)[1]:
        return ""
    return render_to_string(
        "capy_theme/mode_toggle.html",
        {
            "options": [(mode, MODE_LABELS[mode]) for mode in MODES],
            "current": current_mode(request, theme.live_revision),
            "next": request.get_full_path() if request is not None else "/",
        },
    )


@register.simple_tag(takes_context=True)
def theme_logo(context, slot="main", **attrs):
    """Output the active theme's logo for a slot, or its site name if there's no logo.

    `slot` is main, stacked, mark, wordmark, email or print; a slot without an
    image uses the main logo. The logo is a <picture> with smaller copies for
    small screens, and swaps with light and dark mode. Extra attributes go on the
    <img>, e.g. `{% theme_logo slot="mark" class="h-8" %}`. Outputs nothing if
    no theme is active, or it has neither a logo nor a site name.

    For staff who can edit themes, each element also says which slot it is, so
    the live editor can show the draft's logo there before it's published (#271).
    Visitors get the same HTML as always. The preview keeps only the class, title
    and aria-* attributes given here.
    """
    theme = get_active_theme(context.get("request"))
    if theme is None or theme.live_revision is None:
        return ""
    slot = slot if slot.startswith("logo_") else f"logo_{slot}"
    if slot not in LOGO_SLOTS:
        raise TemplateSyntaxError(
            f"theme_logo: unknown slot {slot!r}; use main, stacked, mark, wordmark, email or print."
        )
    brand = branding(theme.live_revision)
    # The user is absent without Django's auth middleware (as in editor/mount.py).
    user = getattr(context.get("request"), "user", None)
    marker = (
        {
            "data-capy-logo-slot": slot,
            # As text, like the HTML attributes themselves (any value works).
            "data-capy-logo-attrs": json.dumps({k: str(v) for k, v in attrs.items()}),
        }
        if user is not None and can_edit(user)
        else {}
    )
    html = logo_html(theme.live_revision.snapshot, slot, brand["logo_alt"], attrs, marker)
    if html:
        return html
    extra = format_html_join("", ' {}="{}"', sorted({**attrs, **marker}.items()))
    if brand["site_name"]:
        return format_html("<span{}>{}</span>", extra, brand["site_name"])
    return format_html("<span{} hidden></span>", extra) if marker else ""


@register.filter
def capy_get(mapping, key):
    """Look up a dict value by a variable key: {{ swatches|capy_get:mode }}."""
    return mapping.get(key) if hasattr(mapping, "get") else None
