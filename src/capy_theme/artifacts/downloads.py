"""Downloads of the active theme for other tools: design tokens (and, from 7.4,
a daisyUI theme block). Public, like the JSON API: they hold the published theme."""

import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from .api import CACHE_CONTROL
from .build import get_artifacts
from .tokens import build_tokens


def _download(content, content_type, filename):
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = CACHE_CONTROL
    return response


@require_GET
def design_tokens(request):
    """/theme/tokens.json: the theme in the W3C Design Tokens format (2025.10)."""
    artifacts = get_artifacts(request)
    if artifacts is None:
        return JsonResponse({"error": "No theme is published."}, status=404)
    content = json.dumps(build_tokens(artifacts), indent=2, ensure_ascii=False) + "\n"
    filename = f"{artifacts['theme']['slug']}.tokens.json"
    return _download(content, "application/design-tokens+json", filename)
