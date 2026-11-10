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

_RULE = re.compile(r"([^{}]+)\{")


def selectors(css, limit=50):
    """The selectors a stylesheet styles (e.g. [".hero", "h1"]), in order, without
    at-rules like @media."""
    found = []
    for match in _RULE.finditer(re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        prelude = match.group(1).strip()
        if not prelude or prelude.startswith("@"):
            continue
        for selector in prelude.split(","):
            selector = " ".join(selector.split())
            if selector and selector not in found:
                found.append(selector)
    return found[:limit]


@require_GET
def editor_custom_css(request, pk):
    """The draft's custom CSS (if it's on), for users who may edit custom CSS."""
    if not can_edit_custom_css(request.user):
        return HttpResponseForbidden("You can't edit custom CSS.")
    theme = get_object_or_404(Theme, pk=pk)
    custom = theme.settings.get("custom_css", {})
    css = custom.get("css", "") if custom.get("enabled", True) else ""
    response = HttpResponse(css, content_type="text/css; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response
