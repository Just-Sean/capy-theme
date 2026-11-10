"""The live editor's JSON views: state, preview, suggestions, save, publish, upload."""

import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from ..images.uploads import add_asset, asset_data
from ..models import Theme
from ..themes.publishing import NothingToPublish, publish
from .access import can_edit, can_publish
from .preview import preview
from .saving import save_draft, suggestions
from .state import draft_state


def editor_state(request, pk):
    """The live editor's view of a theme's draft (JSON). Staff who can change themes only."""
    if not can_edit(request.user):
        return JsonResponse({"error": "You can't edit themes."}, status=403)
    theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=pk)
    response = JsonResponse(draft_state(theme, request.user))
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def editor_preview(request, pk):
    """Preview unsaved editor values (JSON in, JSON out). Never writes anything.

    Returns the CSS, every colour's value and the contrast ratings, from the same
    code as publishing. Invalid values give 400 with the problems listed.
    """
    if not can_edit(request.user):
        return JsonResponse({"error": "You can't edit themes."}, status=403)
    theme = get_object_or_404(Theme, pk=pk)
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"errors": ["The request isn't valid JSON."]}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({"errors": ["The request must be a JSON object."]}, status=400)
    try:
        result = preview(theme, data)
    except ValidationError as error:
        return JsonResponse({"errors": error.messages}, status=400)
    response = JsonResponse(result)
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def editor_suggestions(request, pk):
    """Palette suggestions (JSON) from {"primary": "<any colour>"} and the theme's logo."""
    if not can_edit(request.user):
        return JsonResponse({"error": "You can't edit themes."}, status=403)
    theme = get_object_or_404(Theme, pk=pk)
    try:
        data = json.loads(request.body or b"{}")
        primary = str(data.get("primary") or "") if isinstance(data, dict) else ""
        result = suggestions(theme, primary)
    except ValueError:
        return JsonResponse({"errors": ["That isn't a colour."]}, status=400)
    response = JsonResponse({"suggestions": result})
    response["Cache-Control"] = "no-store"
    return response


def _json_body(request):
    data = json.loads(request.body or b"{}")
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data


@require_POST
def editor_save(request, pk):
    """Save the editor's values as the theme's draft (JSON in, new state out)."""
    if not can_edit(request.user):
        return JsonResponse({"error": "You can't edit themes."}, status=403)
    theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=pk)
    try:
        data = _json_body(request)
    except ValueError:
        return JsonResponse({"errors": ["The request must be a JSON object."]}, status=400)
    try:
        save_draft(theme, data)
    except ValidationError as error:
        return JsonResponse({"errors": error.messages}, status=400)
    return JsonResponse({"saved": True, "state": draft_state(theme, request.user)})


@require_POST
def editor_publish(request, pk):
    """Publish the theme's saved draft from the editor. Needs publish_theme.

    Takes an optional {"note": "..."}; goes through the same publish() and
    revisions as the admin's Publish page.
    """
    if not can_publish(request.user):
        return JsonResponse({"error": "You can't publish themes."}, status=403)
    theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=pk)
    try:
        data = _json_body(request)
    except ValueError:
        return JsonResponse({"errors": ["The request must be a JSON object."]}, status=400)
    try:
        revision = publish(theme, user=request.user, note=str(data.get("note", ""))[:2000])
    except NothingToPublish as error:
        return JsonResponse({"errors": [str(error)]}, status=409)
    except ValidationError as error:
        return JsonResponse({"errors": ["Can't publish: " + " ".join(error.messages)]}, status=400)
    except IntegrityError:
        return JsonResponse(
            {
                "errors": [
                    "Someone else just published this theme. Reload and check, then try again."
                ]
            },
            status=409,
        )
    return JsonResponse({"published": revision.number, "state": draft_state(theme, request.user)})


@require_POST
def editor_upload(request, pk):
    """Upload an image from the editor (multipart: slot, mode, alt_text, file).

    The file is checked and cleaned by the same code as the admin and stored as a
    new asset. Returns the theme's images (JSON).
    """
    if not can_edit(request.user):
        return JsonResponse({"error": "You can't edit themes."}, status=403)
    theme = get_object_or_404(Theme, pk=pk)
    upload = request.FILES.get("file")
    if upload is None:
        return JsonResponse({"errors": ["Choose an image to upload."]}, status=400)
    try:
        asset = add_asset(
            theme,
            request.POST.get("slot", ""),
            request.POST.get("mode", "light"),
            upload,
            request.POST.get("alt_text", ""),
        )
    except ValidationError as error:
        return JsonResponse({"errors": error.messages}, status=400)
    return JsonResponse(
        {"uploaded": asset_data(asset), "assets": [asset_data(a) for a in theme.assets.all()]}
    )


# The Components view's samples, in order (templates/capy_theme/editor/components/).
COMPONENTS = [
    "text",
    "buttons",
    "badges",
    "alerts",
    "cards",
    "tabs",
    "table",
    "forms",
    "progress",
    "modal",
]


@xframe_options_sameorigin
def editor_components(request):
    """Every daisyUI component in light and dark, for the editor's Components view.

    Shown in an iframe beside the editor (so only same-site framing is allowed).
    Staff who can edit themes only.
    """
    if not can_edit(request.user):
        return HttpResponseForbidden("You can't edit themes.")
    return render(
        request,
        "capy_theme/editor/components.html",
        {"modes": ["light", "dark"], "sections": COMPONENTS},
    )
