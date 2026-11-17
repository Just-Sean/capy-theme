"""The draft's custom CSS for the Components view, and which selectors it styles.

Only for users who may edit custom CSS (the draft isn't public). Others see the
published custom CSS, which is public anyway.
"""

import re

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from ..css.custom import can_edit_custom_css
from ..models import Theme
from .access import can_edit

_BRACES = re.compile(r"([{}])")


def selectors(css, limit=50):
    """The selectors a stylesheet styles (e.g. [".hero", "h1"]), in order, without
    at-rules like @media.

    Linear time, because custom CSS can be long and crafted (#238): a rule's
    prelude is the text before its "{", back to the previous brace.
    """
    found = []
    pieces = _BRACES.split(_without_comments(css))
    for text, brace in zip(pieces[::2], pieces[1::2], strict=False):
        prelude = text.strip()
        if brace != "{" or not prelude or prelude.startswith("@"):
            continue
        for selector in prelude.split(","):
            selector = " ".join(selector.split())
            if selector and selector not in found:
                found.append(selector)
    return found[:limit]


def _without_comments(css):
    """`css` with its /* comments */ removed (an unclosed one stays as text)."""
    kept = []
    start = 0
    while (opening := css.find("/*", start)) != -1:
        closing = css.find("*/", opening + 2)
        if closing == -1:
            break
        kept.append(css[start:opening])
        start = closing + 2
    kept.append(css[start:])
    return "".join(kept)


@require_GET
def editor_custom_css(request, pk):
    """The draft's custom CSS (if it's on), for editors who may edit custom CSS:
    active staff who can edit themes, like every editor address (#275)."""
    if not (can_edit(request.user) and can_edit_custom_css(request.user)):
        return HttpResponseForbidden("You can't edit custom CSS.")
    theme = get_object_or_404(Theme, pk=pk)
    custom = theme.settings.get("custom_css", {})
    css = custom.get("css", "") if custom.get("enabled", True) else ""
    response = HttpResponse(css, content_type="text/css; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response
