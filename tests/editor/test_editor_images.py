"""The live editor's images (#271): slots described like the admin, uploads chosen
where they're used, editable alt text, and the draft's logos and icon shown on the
page before publishing."""

import io
from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import reverse
from django.utils.translation import gettext_lazy
from PIL import Image

from capy_theme.images.models import ThemeAsset
from capy_theme.images.uploads import add_asset
from capy_theme.models import Theme
from capy_theme.portability.export import export_theme
from capy_theme.portability.importing import import_theme
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
    # The flag lives outside draw(), so a redraw during an upload can't reset it.
    assert script.index("var uploading = false;") < script.index("function draw()")
    click = script[script.index('button.addEventListener("click"') :]
    assert click.index("if (uploading) return;") < click.index("send(")
    assert click.index("uploading = true;") < click.index("send(")
    assert click.index("select.disabled = true;") < click.index("send(")  # no redraw meanwhile
    assert "button.disabled = uploading;" in script  # a redraw keeps it off
    # A failed upload turns it back on without redrawing (the chosen file stays).
    catch = click[click.index(".catch(") : click.index("box.appendChild(")]
    assert "button.disabled = false;" in catch and "draw()" not in catch


def test_a_late_upload_isnt_chosen_after_the_editor_moved_on():
    script = (STATIC / "controls/image-slot.js").read_text()
    upload = script[script.index("send(ui.saved.urls.upload") :]
    done = upload[upload.index(".then(function (body)") : upload.index(".catch(")]
    guard = "if (!box.isConnected || !editor.panel || editor.panel.hidden) {"
    late = done[done.index(guard) : done.index("return;")]
    assert "remember(body.assets, spec.name);" in late  # listed, not chosen
    assert "but not chosen" in late  # and the user is told
    assert done.index(guard) < done.index("choose(")


def test_a_new_upload_is_listed_in_every_box_for_its_slot():
    script = (STATIC / "controls/image-slot.js").read_text()
    remember = script[script.index("function remember(") : script.index("function fillOptions(")]
    # Only the lists are refreshed, so a file chosen in another box isn't lost.
    assert "box.capyRefreshList();" in remember and "draw" not in remember
    assert "fillOptions(select, spec.name, mode, select.value);" in script


def test_closing_cancels_a_preview_on_its_way():
    editor = (STATIC / "editor.js").read_text()
    close = editor[editor.index("editor.close = function") :]
    close = close[: close.index("};")]
    assert close.index("editor.cancelPreview();") < close.index("removeCss();")
    page = (STATIC / "controls/page-images.js").read_text()
    show = page[page.index("function show(data)") :]
    assert "editor.panel.hidden) return;" in show[: show.index("\n  }\n")]


def test_closing_the_editor_puts_the_published_logos_and_icon_back():
    editor = (STATIC / "editor.js").read_text()
    close = editor[editor.index("editor.close = function") :]
    assert 'new CustomEvent("capy-editor:closed")' in close[: close.index("};")]
    page = (STATIC / "controls/page-images.js").read_text()
    assert 'document.addEventListener("capy-editor:closed", restore);' in page
    assert "spot.originals" in page and "item.link.href = item.href;" in page


def test_the_page_preview_only_copies_safe_attributes():
    page = (STATIC / "controls/page-images.js").read_text()
    # A forged marker (e.g. in content a site's users wrote) can't add event
    # handlers, styles or sources: only these names, with text values, are copied.
    assert "var SAFE = /^(class|title|aria-[a-z-]+)$/;" in page
    assert 'SAFE.test(key) && typeof parsed[key] === "string"' in page
    assert 'var MARKED = ["IMG", "PICTURE", "SPAN"];' in page
    assert 'safeAttrs(node.getAttribute("data-capy-logo-attrs"))' in page
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


# QA (#271)


# Alt text in Save draft


@pytest.mark.parametrize("alts", [None, [], {"OK": None}, {"OK": True}, {"OK": ["x"]}])
def test_odd_alts_are_refused_and_nothing_is_saved(editor_client, theme, alts):
    asset = add_asset(theme, "logo_main", "light", png(), "Kept")
    if isinstance(alts, dict):
        alts = {str(asset.pk): v for v in alts.values()}
    reply = post(editor_client, "editor_save", theme, {"alts": alts, "light_base": "cupcake"})
    assert reply.status_code == 400
    asset.refresh_from_db()
    theme.refresh_from_db()
    assert (asset.alt_text, theme.light_base) == ("Kept", "light")


def test_alt_text_of_exactly_200_after_trimming_is_fine(editor_client, theme):
    asset = add_asset(theme, "logo_main", "light", png())
    reply = post(editor_client, "editor_save", theme, {"alts": {asset.pk: "  " + "é" * 200 + " "}})
    assert reply.status_code == 200, reply.content
    asset.refresh_from_db()
    assert asset.alt_text == "é" * 200


def test_alt_text_can_be_cleared(editor_client, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    assert post(editor_client, "editor_save", theme, {"alts": {asset.pk: "   "}}).status_code == 200
    asset.refresh_from_db()
    assert asset.alt_text == ""


def test_an_alt_edit_doesnt_change_the_published_alt_until_publish(editor_client, theme):
    published_with_logo(theme)
    asset = theme.assets.get()
    post(editor_client, "editor_save", theme, {"alts": {asset.pk: "Brand new alt"}})
    theme.refresh_from_db()
    live = theme.live_revision.snapshot["images"]["logo_main"]["light"]
    assert live["alt"] == ""


def test_alts_need_change_theme(client, django_user_model, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Kept")
    user = django_user_model.objects.create_user("v", password="pw", is_staff=True)
    client.force_login(user)
    assert post(client, "editor_save", theme, {"alts": {asset.pk: "x"}}).status_code == 403
    asset.refresh_from_db()
    assert asset.alt_text == "Kept"


# The preview's page images


def page_images(client, theme, images):
    reply = post(client, "editor_preview", theme, {"settings": {"images": images}})
    assert reply.status_code == 200, reply.content
    return reply.json()["page_images"]


def test_a_dark_only_slot_uses_its_dark_image_and_the_main_light(editor_client, theme):
    main = add_asset(theme, "logo_main", "light", png("main.png"))
    stacked_dark = add_asset(theme, "logo_stacked", "dark", png("sd.png"))
    page = page_images(
        editor_client,
        theme,
        {"logo_main": {"light": main.pk}, "logo_stacked": {"dark": stacked_dark.pk}},
    )
    stacked = page["logos"]["logo_stacked"]
    assert stacked["light"]["src"] == main.original.url  # no light: the main logo
    assert stacked["dark"]["src"] == stacked_dark.original.url


def test_email_and_print_are_light_only_in_the_preview(editor_client, theme):
    main = add_asset(theme, "logo_main", "light", png("main.png"))
    main_dark = add_asset(theme, "logo_main", "dark", png("md.png"))
    email = add_asset(theme, "logo_email", "light", png("e.png"))
    page = page_images(
        editor_client,
        theme,
        {"logo_main": {"light": main.pk, "dark": main_dark.pk}, "logo_email": {"light": email.pk}},
    )
    assert page["logos"]["logo_email"] == {
        "light": {"src": email.original.url, "alt": "Capy Co", "width": 60, "height": 20},
        "dark": None,
    }
    # Print has no image: the main light logo, never the main dark one.
    assert page["logos"]["logo_print"]["light"]["src"] == main.original.url
    assert page["logos"]["logo_print"]["dark"] is None


def test_the_icon_doesnt_fall_back_to_the_logo(editor_client, theme):
    main = add_asset(theme, "logo_main", "light", png())
    page = page_images(editor_client, theme, {"logo_main": {"light": main.pk}})
    assert page["icon"] == {"light": "", "dark": ""}


def test_a_dark_icon_only(editor_client, theme):
    dark = add_asset(theme, "icon", "dark", png("i.png", (64, 64)))
    page = page_images(editor_client, theme, {"icon": {"dark": dark.pk}})
    assert page["icon"] == {"light": "", "dark": dark.original.url}


def test_the_preview_refuses_another_themes_image(editor_client, theme):
    other = Theme.objects.create(name="O", slug="o")
    theirs = add_asset(other, "logo_main", "light", png())
    reply = post(
        editor_client,
        "editor_preview",
        theme,
        {"settings": {"images": {"logo_main": {"light": theirs.pk}}}},
    )
    assert reply.status_code == 400


def test_the_preview_refuses_an_image_from_another_slot(editor_client, theme):
    mark = add_asset(theme, "logo_mark", "light", png())
    reply = post(
        editor_client,
        "editor_preview",
        theme,
        {"settings": {"images": {"logo_main": {"light": mark.pk}}}},
    )
    assert reply.status_code == 400


# The upload endpoint


def upload(client, theme, **fields):
    url = reverse("capy_theme:editor_upload", args=[theme.pk])
    return client.post(url, {"file": png(), "slot": "logo_main", "mode": "light", **fields})


def test_an_upload_isnt_chosen_until_save(editor_client, theme):
    reply = upload(editor_client, theme, alt_text="Logo")
    assert reply.status_code == 200
    assert reply.json()["uploaded"]["alt_text"] == "Logo"
    theme.refresh_from_db()
    assert "images" not in theme.settings


@pytest.mark.parametrize("fields", [{"slot": "nope"}, {"mode": "sepia"}, {"slot": ""}])
def test_an_upload_to_a_bad_slot_or_mode_is_refused(editor_client, theme, fields):
    assert upload(editor_client, theme, **fields).status_code == 400
    assert not ThemeAsset.objects.exists()


@pytest.mark.parametrize("slot", ["logo_email", "logo_print", "social"])
def test_a_dark_upload_for_a_light_only_slot_is_refused(editor_client, theme, slot):
    """Email, print and sharing images have no dark choice any more."""
    reply = upload(editor_client, theme, slot=slot, mode="dark")
    assert reply.status_code == 400
    assert not ThemeAsset.objects.exists()


def test_alt_text_on_upload_is_limited(editor_client, theme):
    reply = upload(editor_client, theme, alt_text="  " + "x" * 300)
    assert reply.status_code == 200
    assert reply.json()["uploaded"]["alt_text"] == "x" * 200


def test_uploading_needs_change_theme(client, django_user_model, theme):
    user = django_user_model.objects.create_user("v", password="pw", is_staff=True)
    client.force_login(user)
    assert upload(client, theme).status_code == 403
    client.logout()
    assert upload(client, theme).status_code == 403
    assert not ThemeAsset.objects.exists()


# {% theme_logo %} markers


@pytest.mark.parametrize("who", ["anonymous", "staff_without_perm", "inactive", "not_staff"])
def test_no_marker_for_people_who_cant_edit(theme, django_user_model, who):
    published_with_logo(theme)
    if who == "anonymous":
        user = AnonymousUser()
    else:
        user = django_user_model.objects.create_user(
            "u", password="pw", is_staff=who != "not_staff", is_active=who != "inactive"
        )
        if who != "staff_without_perm":
            user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    html = render_logo(user)
    assert "data-capy-logo" not in html


def test_visitors_with_only_a_site_name_get_no_marker(theme):
    publish(theme)
    activate(theme)
    assert render_logo(AnonymousUser()) == "<span>Capy Co</span>"


def test_no_request_in_the_context_means_no_marker(theme):
    published_with_logo(theme)
    html = Template("{% load capy_theme %}{% theme_logo %}").render(Context({}))
    assert "data-capy-logo" not in html


def test_editor_html_with_a_dark_logo_marks_both_pictures(theme, editor):
    light = add_asset(theme, "logo_main", "light", png("l.png"))
    dark = add_asset(theme, "logo_main", "dark", png("d.png"))
    chosen = {"logo_main": {"light": light.pk, "dark": dark.pk}}
    theme.settings = {**theme.settings, "images": chosen}
    theme.save()
    publish(theme)
    activate(theme)
    html = render_logo(editor, '{% theme_logo class="h-8" %}')
    assert html.count('data-capy-logo-slot="logo_main"') == 2
    assert html.count("<picture") == 2


def test_editor_marker_attrs_are_escaped(theme, editor):
    published_with_logo(theme)
    html = render_logo(editor, '{% theme_logo class="a\\"><script>x</script>" %}')
    assert "<script>" not in html


# The live edit page header


def test_the_header_escapes_the_drafts_site_name_and_tagline(editor_client, theme):
    theme.settings = {"site_name": "<script>a()</script>", "tagline": "<b>t</b>"}
    theme.save()
    html = editor_client.get(f"/theme/live-edit/?edit={theme.pk}").content.decode()
    header = html[html.index("<header") : html.index("</header>")]
    assert "<script>a()" not in header and "<b>t</b>" not in header


def test_the_header_with_no_site_name_and_no_logo(editor_client):
    bare = Theme.objects.create(name="Bare", slug="bare")
    html = editor_client.get(f"/theme/live-edit/?edit={bare.pk}").content.decode()
    header = html[html.index("<header") : html.index("</header>")]
    assert ">Live edit</span>" in header


def test_the_header_for_a_missing_theme_falls_back(editor_client, theme):
    reply = editor_client.get("/theme/live-edit/?edit=999999")
    assert reply.status_code == 200


def test_save_draft_drops_a_dark_choice_for_a_light_only_slot(editor_client, theme):
    """Dropped, like the admin does, rather than refused: a theme saved before 1.0
    may still have one, and refusing would stop its editor from saving at all."""
    email = add_asset(theme, "logo_email", "light", png())
    images = {"logo_email": {"light": email.pk, "dark": email.pk}}
    reply = post(editor_client, "editor_save", theme, {"settings": {"images": images}})
    assert reply.status_code == 200, reply.content
    theme.refresh_from_db()
    assert theme.settings["images"] == {"logo_email": {"light": email.pk}}


# Fixes after review (#271)


def test_the_logo_works_without_djangos_auth_middleware(theme):
    published_with_logo(theme)
    request = RequestFactory().get("/")  # no request.user, as without auth middleware
    html = Template("{% load capy_theme %}{% theme_logo %}").render(Context({"request": request}))
    assert "<img" in html and "data-capy-logo" not in html


def test_any_attribute_value_works_for_editors(theme, editor):
    published_with_logo(theme)
    request = RequestFactory().get("/")
    request.user = editor
    context = Context({"request": request, "label": theme})  # not JSON: a model instance
    html = Template("{% load capy_theme %}{% theme_logo title=label %}").render(context)
    assert 'title="Main"' in html
    assert 'data-capy-logo-attrs="{&quot;title&quot;: &quot;Main&quot;}"' in html


# QA, second round (#271 review fixes)


@pytest.mark.parametrize(
    ("slot", "mode"),
    [
        ("logo_email", "light"),
        ("logo_print", "light"),
        ("social", "light"),
        ("logo_main", "dark"),
        ("icon", "dark"),
        ("background_login", "dark"),
    ],
)
def test_valid_uploads_are_still_accepted(editor_client, theme, slot, mode):
    size = {"icon": (64, 64), "social": (600, 315)}.get(slot, (60, 20))
    url = reverse("capy_theme:editor_upload", args=[theme.pk])
    reply = editor_client.post(url, {"file": png(size=size), "slot": slot, "mode": mode})
    assert reply.status_code == 200, reply.content
    assert ThemeAsset.objects.get().mode == mode


def test_an_upload_without_a_mode_is_light(editor_client, theme):
    url = reverse("capy_theme:editor_upload", args=[theme.pk])
    reply = editor_client.post(url, {"file": png(), "slot": "logo_email"})
    assert reply.status_code == 200, reply.content


def test_save_drops_a_slot_left_with_only_a_dark_email_choice(editor_client, theme):
    email = add_asset(theme, "logo_email", "light", png())
    main = add_asset(theme, "logo_main", "light", png())
    images = {"logo_email": {"dark": email.pk}, "logo_main": {"light": main.pk}}
    reply = post(editor_client, "editor_save", theme, {"settings": {"images": images}})
    assert reply.status_code == 200, reply.content
    theme.refresh_from_db()
    assert theme.settings["images"] == {"logo_main": {"light": main.pk}}


def test_save_with_only_a_dark_email_choice_removes_images(editor_client, theme):
    email = add_asset(theme, "logo_email", "light", png())
    images = {"logo_email": {"dark": email.pk}}
    reply = post(editor_client, "editor_save", theme, {"settings": {"images": images}})
    assert reply.status_code == 200, reply.content
    theme.refresh_from_db()
    assert "images" not in theme.settings


def test_an_old_dark_email_choice_in_the_draft_doesnt_stop_other_edits(editor_client, theme):
    """The editor's change doesn't touch images; the draft has old data."""
    email = add_asset(theme, "logo_email", "dark", png())
    theme.settings = {**theme.settings, "images": {"logo_email": {"dark": email.pk}}}
    theme.save()
    reply = post(editor_client, "editor_save", theme, {"settings": {"shape": {"radius_box": 1}}})
    assert reply.status_code == 200, reply.content
    reply = post(editor_client, "editor_preview", theme, {})
    assert reply.status_code == 200, reply.content


@pytest.mark.parametrize("images", ["x", 5, {"logo_main": 5}, {"logo_main": []}])
def test_odd_images_values_are_refused_not_crashing(editor_client, theme, images):
    reply = post(editor_client, "editor_save", theme, {"settings": {"images": images}})
    assert reply.status_code == 400, reply.content


def test_importing_an_export_with_an_old_dark_email_logo_still_works(theme):
    light = add_asset(theme, "logo_email", "light", png("l.png"))
    dark = add_asset(theme, "logo_email", "dark", png("d.png"))
    theme.settings = {
        **theme.settings,
        "images": {"logo_email": {"light": light.pk, "dark": dark.pk}},
    }
    theme.save()
    data = export_theme(theme)
    import io

    imported = import_theme(io.BytesIO(data))
    assert imported.pk != theme.pk
    assert set(imported.settings["images"]["logo_email"]) >= {"light"}


# {% theme_logo %} attribute values


@pytest.mark.parametrize(
    "value",
    [None, 0, 3.5, True, ["a"], {"a": 1}, gettext_lazy("Logo"), "Capy 🐹", "x" * 5000],
)
def test_theme_logo_takes_any_attribute_value_for_editors(theme, editor, value):
    published_with_logo(theme)
    request = RequestFactory().get("/")
    request.user = editor
    html = Template("{% load capy_theme %}{% theme_logo title=v %}").render(
        Context({"request": request, "v": value})
    )
    assert 'data-capy-logo-slot="logo_main"' in html


def test_theme_logo_with_a_request_whose_user_is_none(theme):
    published_with_logo(theme)
    request = RequestFactory().get("/")
    request.user = None
    html = Template("{% load capy_theme %}{% theme_logo %}").render(Context({"request": request}))
    assert "data-capy-logo" not in html


def test_theme_logo_with_no_active_theme_and_no_user(theme):
    Theme.objects.all().delete()
    request = RequestFactory().get("/")
    html = Template("{% load capy_theme %}{% theme_logo %}").render(Context({"request": request}))
    assert "data-capy-logo" not in html


# QA, third round (#271 review fixes): odd modes reach add_asset's own message


@pytest.mark.parametrize("slot", ["logo_email", "logo_print", "social", "logo_main"])
@pytest.mark.parametrize("mode", ["", "Light", "DARK", " dark", "sepia", "light,dark"])
def test_an_odd_mode_gets_add_assets_message(editor_client, theme, slot, mode):
    reply = upload(editor_client, theme, slot=slot, mode=mode)
    assert reply.status_code == 400
    assert reply.json()["errors"] == ["Choose light or dark mode."]
    assert not ThemeAsset.objects.exists()


def test_a_dark_upload_for_a_light_only_slot_gets_its_own_message(editor_client, theme):
    reply = upload(editor_client, theme, slot="logo_email", mode="dark")
    assert reply.json()["errors"] == ["This image only has a light version."]


def test_an_unknown_slot_with_dark_gets_the_slot_message(editor_client, theme):
    reply = upload(editor_client, theme, slot="nope", mode="dark")
    assert reply.status_code == 400
    assert reply.json()["errors"] == ["Choose where the image goes."]


def test_a_repeated_mode_field_uses_the_last_value(editor_client, theme):
    url = reverse("capy_theme:editor_upload", args=[theme.pk])
    reply = editor_client.post(
        url, {"file": png(), "slot": "logo_email", "mode": ["light", "dark"]}
    )
    assert reply.status_code == 400
    assert not ThemeAsset.objects.exists()
