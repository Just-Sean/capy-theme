"""The live editor's JSON views: state, preview, suggestions, save, publish, upload."""

import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from ..images.assets import asset_data
from ..images.uploads import add_asset
from ..models import Theme
from ..themes.active import NotPublished, default_themes, not_published_message
from ..themes.publishing import (
    NOTE_MAX,
    NOTHING_TO_PUBLISH,
    NothingToPublish,
    publish,
    publish_and_activate,
)
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

    Returns the CSS, every color's value and the contrast ratings, from the same
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
    """Palette suggestions (JSON) from {"primary": "<any color>"} and the theme's logo."""
    if not can_edit(request.user):
        return JsonResponse({"error": "You can't edit themes."}, status=403)
    theme = get_object_or_404(Theme, pk=pk)
    try:
        data = json.loads(request.body or b"{}")
        primary = str(data.get("primary") or "") if isinstance(data, dict) else ""
        result = suggestions(theme, primary)
    except ValueError:
        return JsonResponse({"errors": ["That isn't a color."]}, status=400)
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


def _showing_instead(theme):
    """The theme the site shows right now for this scheme if it isn't `theme`
    (a schedule), else None."""
    showing = default_themes().get(theme.scheme)
    return str(showing) if showing is not None and showing.pk != theme.pk else None


@require_POST
def editor_publish(request, pk):
    """Publish the theme's saved draft from the editor. Needs publish_theme.

    Takes an optional {"note": "...", "activate": true}; goes through the same
    publish() and revisions as the admin's buttons. With "activate", the theme also
    becomes the site's theme, even if there was nothing new to publish (#273).
    """
    if not can_publish(request.user):
        return JsonResponse({"error": "You can't publish themes."}, status=403)
    theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=pk)
    try:
        data = _json_body(request)
    except ValueError:
        return JsonResponse({"errors": ["The request must be a JSON object."]}, status=400)
    note = str(data.get("note", "")).strip()[:NOTE_MAX]
    activate_too = data.get("activate") is True
    try:
        if activate_too:
            revision = publish_and_activate(theme, user=request.user, note=note)
        else:
            revision = publish(theme, user=request.user, note=note)
    except NothingToPublish:
        return JsonResponse({"errors": [NOTHING_TO_PUBLISH]}, status=409)
    except NotPublished:  # the message is built, not taken from the exception
        return JsonResponse({"errors": [not_published_message(theme)]}, status=400)
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
    return JsonResponse(
        {
            "published": revision.number if revision else None,
            "activated": activate_too,
            # A running theme schedule can show another theme for now (#273).
            "showing": _showing_instead(theme) if activate_too else None,
            "state": draft_state(theme, request.user),
        }
    )


@require_POST
def editor_upload(request, pk):
    """Upload an image from the editor (multipart: slot, alt_text, file).

    The file is checked and cleaned by the same code as the admin and stored as a
    new asset. Returns the theme's images (JSON).
    """
    if not can_edit(request.user):
        return JsonResponse({"error": "You can't edit themes."}, status=403)
    theme = get_object_or_404(Theme, pk=pk)
    upload = request.FILES.get("file")
    if upload is None:
        return JsonResponse({"errors": ["Choose an image to upload."]}, status=400)
    slot = request.POST.get("slot", "")
    try:
        asset = add_asset(theme, slot, upload, request.POST.get("alt_text", ""))
    except ValidationError as error:
        return JsonResponse({"errors": error.messages}, status=400)
    return JsonResponse(
        {"uploaded": asset_data(asset), "assets": [asset_data(a) for a in theme.assets.all()]}
    )
