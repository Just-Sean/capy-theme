import json

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .active import get_active_theme
from .branding import branding
from .editor import (
    can_edit,
    can_publish,
    draft_state,
    editor_theme,
    preview,
    save_draft,
    suggestions,
)
from .images import add_asset, asset_data
from .manifest import build as build_manifest
from .mode import COOKIE_MAX_AGE, COOKIE_NAME, MODES, mode_settings
from .models import Theme, ThemeRevision
from .publishing import NothingToPublish, publish
from .showcase import shape_samples, swatches, typography
from .stylesheet import render_css

ONE_YEAR = 60 * 60 * 24 * 365


def theme_css(request, version):
    """Serve a revision's stylesheet. Every URL names one revision, so it never changes."""
    revision = get_object_or_404(ThemeRevision.objects.select_related("theme"), css_version=version)
    response = HttpResponse(render_css(revision), content_type="text/css; charset=utf-8")
    response["Cache-Control"] = f"public, max-age={ONE_YEAR}, immutable"
    return response


def manifest(request):
    """The active theme's web app manifest (JSON). 404 if no theme is published."""
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        raise Http404("No theme is active.")
    response = JsonResponse(
        build_manifest(theme.live_revision), content_type="application/manifest+json"
    )
    # A short cache: the URL stays the same when the theme is published again.
    response["Cache-Control"] = "public, max-age=300"
    return response


# The showcase page. Each section is its own template in
# templates/capy_theme/showcase/sections/, shown once per mode. Later phases add
# their sections by adding a template and a name here.
SHOWCASE_SECTIONS = [
    "branding",
    "colors",
    "shape",
    "fonts",
    "typography",
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
SHOWCASE_ACCESS = ("staff", "public", "off")


def showcase(request):
    """Show the active theme's choices on every kind of component, in light and dark."""
    access = getattr(settings, "CAPY_THEME_SHOWCASE", "staff")
    if access not in SHOWCASE_ACCESS:
        raise ImproperlyConfigured(
            f"CAPY_THEME_SHOWCASE must be one of {', '.join(SHOWCASE_ACCESS)}, not {access!r}."
        )
    if access == "off":
        raise Http404("The theme showcase is turned off.")
    if access == "staff" and not (request.user.is_active and request.user.is_staff):
        return redirect_to_login(request.get_full_path(), reverse("admin:login"))

    theme = get_active_theme(request)
    revision = theme.live_revision if theme else None
    context = {
        "base_template": getattr(
            settings, "CAPY_THEME_BASE_TEMPLATE", "capy_theme/showcase/standalone.html"
        ),
        "active_theme": theme,
        "revision": revision,
        "brand": branding(revision) if revision else {},
        "modes": ["light", "dark"],
        "sections": [f"capy_theme/showcase/sections/{name}.html" for name in SHOWCASE_SECTIONS],
        "swatches": swatches(revision),
        "shape_samples": shape_samples(revision),
        "type_samples": typography(revision),
        "editor": _editor_context(request),
    }
    return render(request, "capy_theme/showcase/page.html", context)


def set_mode(request, mode):
    """Remember a visitor's light/dark/auto choice in a cookie, then go back.

    Used by {% theme_mode_toggle %} when JavaScript is off (with JavaScript the
    script sets the cookie itself). Ignored if the theme doesn't allow switching.
    """
    if mode not in MODES:
        raise Http404("Unknown mode.")
    target = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = "/"
    response = HttpResponseRedirect(target)
    theme = get_active_theme(request)
    if theme is not None and theme.live_revision is not None:
        if mode_settings(theme.live_revision)[1]:
            response.set_cookie(
                COOKIE_NAME, mode, max_age=COOKIE_MAX_AGE, samesite="Lax", httponly=False
            )
    return response


def _editor_context(request):
    """Whether to show the showcase's Edit theme button (the editor itself comes
    from {% theme_head %})."""
    if not can_edit(request.user):
        return None
    theme = editor_theme(request)
    if theme is None:
        return None
    return {"theme": theme}


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
