"""The live editor's images (#271): slots described like the admin, uploads chosen
where they're used, editable alt text, and the draft's logos and icon shown on the
page before publishing."""

import io
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import reverse
from PIL import Image

from capy_theme.images.uploads import add_asset
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
STATIC = Path(__file__).resolve().parents[2] / "src/capy_theme/static/capy_theme/editor"
TEMPLATES = Path(__file__).resolve().parents[2] / "src/capy_theme/templates/capy_theme"


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def png(name="logo.png", size=(60, 20)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (30, 90, 200)).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def theme():
    return Theme.objects.create(
        name="Main", slug="main", settings={"site_name": "Capy Co", "tagline": "Calm"}
    )


@pytest.fixture
def editor(django_user_model):
    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    return user


@pytest.fixture
def editor_client(client, editor):
    client.force_login(editor)
    return client


def post(client, name, theme, data):
    url = reverse(f"capy_theme:{name}", args=[theme.pk])
    return client.post(url, data, content_type="application/json")


# What the editor offers


def test_every_slot_is_described_like_in_the_admin(editor_client, theme):
    state = editor_client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    slots = {s["name"]: s for s in state["controls"]["image_slots"]}
    assert "Most sites only need this one" in slots["logo_main"]["help"]["light"]
    assert "Up to 2 MB" in slots["logo_main"]["help"]["light"]
    assert slots["logo_main"]["empty"]["light"] == "No image: the site name is shown instead."
    assert slots["logo_mark"]["empty"]["light"] == "No image: the main logo is used."
    assert slots["logo_main"]["empty"]["dark"].startswith("No dark image")
    assert slots["logo_email"]["modes"] == ["light"]  # emails have no dark mode
    assert slots["logo_print"]["modes"] == ["light"]
    assert slots["logo_email"]["svg"] is False
    assert "logo_slots" not in state["controls"]


# Alt text, saved with the draft


def test_alt_text_is_saved_with_the_draft(editor_client, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Typo")
    reply = post(editor_client, "editor_save", theme, {"alts": {str(asset.pk): " Capy Co logo "}})
    assert reply.status_code == 200
    asset.refresh_from_db()
    assert asset.alt_text == "Capy Co logo"
    assert reply.json()["state"]["assets"][0]["alt_text"] == "Capy Co logo"


@pytest.mark.parametrize(
    "alts",
    [{"999999": "x"}, {"ID": "x"}, "not an object", {"OK": 5}, {"OK": "x" * 201}],
)
def test_bad_alt_text_is_refused_and_nothing_is_saved(editor_client, theme, alts):
    asset = add_asset(theme, "logo_main", "light", png(), "Kept")
    other = Theme.objects.create(name="Other", slug="other")
    theirs = add_asset(other, "logo_main", "light", png())
    if isinstance(alts, dict):
        alts = {
            {"ID": str(theirs.pk), "OK": str(asset.pk)}.get(key, key): value
            for key, value in alts.items()
        }
    reply = post(editor_client, "editor_save", theme, {"alts": alts, "light_base": "cupcake"})
    assert reply.status_code == 400
    asset.refresh_from_db()
    theirs.refresh_from_db()
    theme.refresh_from_db()
    assert (asset.alt_text, theirs.alt_text, theme.light_base) == ("Kept", "", "light")


# The draft's logos and icon on the page


def test_the_preview_has_the_drafts_logos_with_fallbacks_and_the_icon(editor_client, theme):
    light = add_asset(theme, "logo_main", "light", png("light.png"), "Light")
    dark = add_asset(theme, "logo_main", "dark", png("dark.png"))
    icon = add_asset(theme, "icon", "light", png("icon.png", (64, 64)))
    images = {"logo_main": {"light": light.pk, "dark": dark.pk}, "icon": {"light": icon.pk}}
    reply = post(editor_client, "editor_preview", theme, {"settings": {"images": images}})
    page = reply.json()["page_images"]
    main = page["logos"]["logo_main"]
    assert main["light"] == {"src": light.original.url, "alt": "Light", "width": 60, "height": 20}
    assert main["dark"]["src"] == dark.original.url
    assert main["dark"]["alt"] == "Capy Co"  # no alt of its own: the site name
    assert page["logos"]["logo_mark"] == main  # an empty slot uses the main logo
    assert page["logos"]["logo_email"]["dark"] is None  # always the light one
    # No dark icon: dark mode uses the light one, as when published.
    assert page["icon"] == {"light": icon.original.url, "dark": icon.original.url}
    assert page["site_name"] == "Capy Co"
    # Nothing was saved.
    theme.refresh_from_db()
    assert "images" not in theme.settings


def test_without_a_logo_the_preview_says_so(editor_client, theme):
    page = post(editor_client, "editor_preview", theme, {}).json()["page_images"]
    assert page["logos"]["logo_main"] == {"light": None, "dark": None}


def render_logo(user, source="{% theme_logo %}"):
    request = RequestFactory().get("/")
    request.user = user
    return Template("{% load capy_theme %}" + source).render(Context({"request": request}))


def published_with_logo(theme):
    asset = add_asset(theme, "logo_main", "light", png())
    theme.settings = {**theme.settings, "images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    publish(theme)
    activate(theme)


def test_logos_are_marked_for_editors_so_the_preview_can_find_them(theme, editor):
    published_with_logo(theme)
    html = render_logo(editor, '{% theme_logo slot="mark" class="h-8" %}')
    assert 'data-capy-logo-slot="logo_mark"' in html
    assert 'data-capy-logo-attrs="{&quot;class&quot;: &quot;h-8&quot;}"' in html


def test_visitors_get_the_same_logo_html_as_before(theme):
    from django.contrib.auth.models import AnonymousUser

    published_with_logo(theme)
    html = render_logo(AnonymousUser())
    assert "<img" in html and "data-capy-logo" not in html


def test_editors_get_a_hidden_marker_where_there_is_no_logo_yet(editor):
    theme = Theme.objects.create(name="Bare", slug="bare")
    publish(theme)
    activate(theme)
    html = render_logo(editor)
    assert html == (
        '<span data-capy-logo-attrs="{}" data-capy-logo-slot="logo_main" hidden></span>'
    )


def test_the_live_edit_page_header_shows_the_theme_being_edited(editor_client, theme):
    other = Theme.objects.create(
        name="Other", slug="other", settings={"site_name": "Other Co", "tagline": "Loud"}
    )
    publish(other)
    activate(other)  # visitors see Other; we edit Main
    asset = add_asset(theme, "logo_main", "light", png(), "Main logo")
    theme.settings = {**theme.settings, "images": {"logo_main": {"light": asset.pk}}}
    theme.save()  # a draft, never published
    html = editor_client.get(f"/theme/live-edit/?edit={theme.pk}").content.decode()
    header = html[html.index("<header") : html.index("</header>")]
    assert asset.original.url in header and 'alt="Main logo"' in header
    assert 'data-capy-logo-slot="logo_main"' in header
    assert "Capy Co" in header and "Calm" in header
    assert "Other Co" not in header and "Loud" not in header


def test_without_a_logo_the_header_shows_the_site_name_ready_for_a_preview(editor_client, theme):
    html = editor_client.get(f"/theme/live-edit/?edit={theme.pk}").content.decode()
    assert '<span data-capy-logo-slot="logo_main" data-capy-logo-attrs="{}">Capy Co</span>' in html


# The scripts (checked in a browser by hand: the project has no JS test runner)


def test_the_editor_loads_the_new_image_scripts_and_not_the_old_ones():
    mount = (TEMPLATES / "editor/mount.html").read_text()
    for name in ("image-slot.js", "image-sections.js", "page-images.js"):
        assert f"capy_theme/editor/controls/{name}" in mount
        assert (STATIC / "controls" / name).exists()
    for old in ("controls/images.js", "controls/image-choices.js"):
        assert old not in mount
        assert not (STATIC / old).exists()


def test_the_upload_button_cant_send_twice():
    script = (STATIC / "controls/image-slot.js").read_text()
    click = script[script.index('button.addEventListener("click"') :]
    assert click.index("if (button.disabled) return;") < click.index("send(")
    assert click.index("button.disabled = true;") < click.index("send(")
    # Only a failed upload turns it back on; a successful one redraws the slot.
    catch = click[click.index(".catch(") :]
    assert "button.disabled = false;" in catch


def test_closing_the_editor_puts_the_published_logos_and_icon_back():
    editor = (STATIC / "editor.js").read_text()
    close = editor[editor.index("editor.close = function") :]
    assert 'new CustomEvent("capy-editor:closed")' in close[: close.index("};")]
    page = (STATIC / "controls/page-images.js").read_text()
    assert 'document.addEventListener("capy-editor:closed", restore);' in page
    assert "spot.originals" in page and "item.link.href = item.href;" in page


def test_the_page_preview_only_reads_its_own_attribute_as_json():
    page = (STATIC / "controls/page-images.js").read_text()
    assert 'JSON.parse(node.getAttribute("data-capy-logo-attrs") || "{}")' in page
    assert "innerHTML" not in page  # nodes are built, never parsed from strings


def test_the_draft_reaches_the_page_on_load_preview_and_revert():
    page = (STATIC / "controls/page-images.js").read_text()
    for event in ("capy-editor:loaded", "capy-editor:preview"):
        assert f'document.addEventListener("{event}"' in page
    actions = (STATIC / "controls/actions.js").read_text()
    assert 'new CustomEvent("capy-editor:preview", { detail: ui.saved })' in actions


def test_alt_text_edits_count_as_unsaved_changes():
    core = (STATIC / "controls/core.js").read_text()
    assert "alts: {}," in core  # part of the values Save sends and Revert discards
