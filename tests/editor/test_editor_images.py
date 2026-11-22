"""The live editor's images (#271): slots described like the admin, uploads chosen
where they're used, editable alt text, and the draft's logos and icon shown on the
page before publishing.

A theme is a single scheme now (light or dark), so images are stored flat
({slot: asset id}) and there are no per-mode image choices."""

import io
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
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
    assert "Most sites only need this one" in slots["logo_main"]["help"]
    assert "Up to 2 MB" in slots["logo_main"]["help"]
    assert slots["logo_main"]["empty"] == "No image: the site name is shown instead."
    assert slots["logo_mark"]["empty"] == "No image: the main logo is used."
    assert slots["logo_email"]["svg"] is False
    assert "modes" not in slots["logo_email"]  # a theme is a single scheme now
    assert "logo_slots" not in state["controls"]


# Alt text, saved with the draft


def test_alt_text_is_saved_with_the_draft(editor_client, theme):
    asset = add_asset(theme, "logo_main", png(), "Typo")
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
    asset = add_asset(theme, "logo_main", png(), "Kept")
    other = Theme.objects.create(name="Other", slug="other")
    theirs = add_asset(other, "logo_main", png())
    if isinstance(alts, dict):
        alts = {
            {"ID": str(theirs.pk), "OK": str(asset.pk)}.get(key, key): value
            for key, value in alts.items()
        }
    reply = post(editor_client, "editor_save", theme, {"alts": alts, "base": "cupcake"})
    assert reply.status_code == 400
    asset.refresh_from_db()
    theirs.refresh_from_db()
    theme.refresh_from_db()
    assert (asset.alt_text, theirs.alt_text, theme.base) == ("Kept", "", "light")


# The draft's logos and icon on the page


def test_the_preview_has_the_drafts_logos_with_fallbacks_and_the_icon(editor_client, theme):
    logo = add_asset(theme, "logo_main", png("logo.png"), "Brand")
    icon = add_asset(theme, "icon", png("icon.png", (64, 64)))
    images = {"logo_main": logo.pk, "icon": icon.pk}
    reply = post(editor_client, "editor_preview", theme, {"settings": {"images": images}})
    page = reply.json()["page_images"]
    main = page["logos"]["logo_main"]
    assert main == {"src": logo.original.url, "alt": "Brand", "width": 60, "height": 20}
    assert page["logos"]["logo_mark"] == main  # an empty slot uses the main logo
    assert page["logos"]["logo_email"] == main  # falls back to the main logo
    assert page["icon"] == icon.original.url
    assert page["site_name"] == "Capy Co"
    # Nothing was saved.
    theme.refresh_from_db()
    assert "images" not in theme.settings


def test_without_a_logo_the_preview_says_so(editor_client, theme):
    page = post(editor_client, "editor_preview", theme, {}).json()["page_images"]
    assert page["logos"]["logo_main"] is None


def published_with_logo(theme):
    asset = add_asset(theme, "logo_main", png())
    theme.settings = {**theme.settings, "images": {"logo_main": asset.pk}}
    theme.save()
    publish(theme)
    activate(theme)


def test_the_live_edit_page_header_shows_the_theme_being_edited(editor_client, theme):
    other = Theme.objects.create(
        name="Other", slug="other", settings={"site_name": "Other Co", "tagline": "Loud"}
    )
    publish(other)
    activate(other)  # visitors see Other; we edit Main
    asset = add_asset(theme, "logo_main", png(), "Main logo")
    theme.settings = {**theme.settings, "images": {"logo_main": asset.pk}}
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
    assert "fillOptions(select, spec.name, select.value);" in script


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
    asset = add_asset(theme, "logo_main", png(), "Kept")
    if isinstance(alts, dict):
        alts = {str(asset.pk): v for v in alts.values()}
    reply = post(editor_client, "editor_save", theme, {"alts": alts, "base": "cupcake"})
    assert reply.status_code == 400
    asset.refresh_from_db()
    theme.refresh_from_db()
    assert (asset.alt_text, theme.base) == ("Kept", "light")


def test_alt_text_of_exactly_200_after_trimming_is_fine(editor_client, theme):
    asset = add_asset(theme, "logo_main", png())
    reply = post(editor_client, "editor_save", theme, {"alts": {asset.pk: "  " + "é" * 200 + " "}})
    assert reply.status_code == 200, reply.content
    asset.refresh_from_db()
    assert asset.alt_text == "é" * 200


def test_alt_text_can_be_cleared(editor_client, theme):
    asset = add_asset(theme, "logo_main", png(), "Old")
    assert post(editor_client, "editor_save", theme, {"alts": {asset.pk: "   "}}).status_code == 200
    asset.refresh_from_db()
    assert asset.alt_text == ""


def test_an_alt_edit_doesnt_change_the_published_alt_until_publish(editor_client, theme):
    published_with_logo(theme)
    asset = theme.assets.get()
    post(editor_client, "editor_save", theme, {"alts": {asset.pk: "Brand new alt"}})
    theme.refresh_from_db()
    live = theme.live_revision.snapshot["images"]["logo_main"]
    assert live["alt"] == ""


def test_alts_need_change_theme(client, django_user_model, theme):
    asset = add_asset(theme, "logo_main", png(), "Kept")
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


def test_an_empty_slot_falls_back_to_the_main_logo(editor_client, theme):
    main = add_asset(theme, "logo_main", png("main.png"))
    page = page_images(editor_client, theme, {"logo_main": main.pk})
    stacked = page["logos"]["logo_stacked"]
    assert stacked["src"] == main.original.url  # no own image: the main logo


def test_a_slots_own_image_wins_over_the_fallback(editor_client, theme):
    main = add_asset(theme, "logo_main", png("main.png"))
    stacked = add_asset(theme, "logo_stacked", png("sd.png"))
    page = page_images(editor_client, theme, {"logo_main": main.pk, "logo_stacked": stacked.pk})
    assert page["logos"]["logo_stacked"]["src"] == stacked.original.url


def test_email_and_print_fall_back_to_the_main_logo_in_the_preview(editor_client, theme):
    main = add_asset(theme, "logo_main", png("main.png"))
    email = add_asset(theme, "logo_email", png("e.png"))
    page = page_images(editor_client, theme, {"logo_main": main.pk, "logo_email": email.pk})
    assert page["logos"]["logo_email"] == {
        "src": email.original.url,
        "alt": "Capy Co",
        "width": 60,
        "height": 20,
    }
    # Print has no image of its own: the main logo.
    assert page["logos"]["logo_print"]["src"] == main.original.url


def test_the_icon_doesnt_fall_back_to_the_logo(editor_client, theme):
    main = add_asset(theme, "logo_main", png())
    page = page_images(editor_client, theme, {"logo_main": main.pk})
    assert page["icon"] == ""


def test_the_icon_shows_its_own_image(editor_client, theme):
    icon = add_asset(theme, "icon", png("i.png", (64, 64)))
    page = page_images(editor_client, theme, {"icon": icon.pk})
    assert page["icon"] == icon.original.url


def test_the_preview_refuses_another_themes_image(editor_client, theme):
    other = Theme.objects.create(name="O", slug="o")
    theirs = add_asset(other, "logo_main", png())
    reply = post(
        editor_client,
        "editor_preview",
        theme,
        {"settings": {"images": {"logo_main": theirs.pk}}},
    )
    assert reply.status_code == 400


def test_the_preview_refuses_an_image_from_another_slot(editor_client, theme):
    mark = add_asset(theme, "logo_mark", png())
    reply = post(
        editor_client,
        "editor_preview",
        theme,
        {"settings": {"images": {"logo_main": mark.pk}}},
    )
    assert reply.status_code == 400


# The upload endpoint


def upload(client, theme, **fields):
    url = reverse("capy_theme:editor_upload", args=[theme.pk])
    return client.post(url, {"file": png(), "slot": "logo_main", **fields})


def test_an_upload_isnt_chosen_until_save(editor_client, theme):
    reply = upload(editor_client, theme, alt_text="Logo")
    assert reply.status_code == 200
    assert reply.json()["uploaded"]["alt_text"] == "Logo"
    theme.refresh_from_db()
    assert "images" not in theme.settings


@pytest.mark.parametrize("fields", [{"slot": "nope"}, {"slot": ""}])
def test_an_upload_to_a_bad_slot_is_refused(editor_client, theme, fields):
    assert upload(editor_client, theme, **fields).status_code == 400
    assert not ThemeAsset.objects.exists()


@pytest.mark.parametrize("slot", ["logo_email", "logo_print", "social"])
def test_an_upload_to_a_no_svg_slot_still_works_for_a_raster(editor_client, theme, slot):
    """These slots don't take SVG, but a valid raster upload is fine (no modes)."""
    size = {"social": (600, 315)}.get(slot, (60, 20))
    url = reverse("capy_theme:editor_upload", args=[theme.pk])
    reply = editor_client.post(url, {"file": png(size=size), "slot": slot})
    assert reply.status_code == 200, reply.content


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


def test_save_keeps_a_flat_image_choice(editor_client, theme):
    """Images are stored flat ({slot: id}); a saved choice is kept as it is."""
    main = add_asset(theme, "logo_main", png())
    images = {"logo_main": main.pk}
    reply = post(editor_client, "editor_save", theme, {"settings": {"images": images}})
    assert reply.status_code == 200, reply.content
    theme.refresh_from_db()
    assert theme.settings["images"] == {"logo_main": main.pk}


# QA, second round (#271 review fixes)


def test_a_valid_upload_is_accepted_for_every_slot(editor_client, theme):
    for slot in ("logo_email", "logo_print", "social", "logo_main", "icon", "background_login"):
        size = {"icon": (64, 64), "social": (600, 315)}.get(slot, (60, 20))
        url = reverse("capy_theme:editor_upload", args=[theme.pk])
        reply = editor_client.post(url, {"file": png(size=size), "slot": slot})
        assert reply.status_code == 200, (slot, reply.content)


def test_an_upload_stores_the_asset_for_its_slot(editor_client, theme):
    url = reverse("capy_theme:editor_upload", args=[theme.pk])
    reply = editor_client.post(url, {"file": png(), "slot": "logo_email"})
    assert reply.status_code == 200, reply.content
    assert ThemeAsset.objects.get().slot == "logo_email"


def test_save_removes_images_when_the_last_choice_is_cleared(editor_client, theme):
    main = add_asset(theme, "logo_main", png())
    theme.settings = {**theme.settings, "images": {"logo_main": main.pk}}
    theme.save()
    reply = post(editor_client, "editor_save", theme, {"settings": {"images": {}}})
    assert reply.status_code == 200, reply.content
    theme.refresh_from_db()
    assert "images" not in theme.settings


def test_a_saved_image_choice_doesnt_stop_other_edits(editor_client, theme):
    main = add_asset(theme, "logo_main", png())
    theme.settings = {**theme.settings, "images": {"logo_main": main.pk}}
    theme.save()
    reply = post(editor_client, "editor_save", theme, {"settings": {"shape": {"radius_box": 1}}})
    assert reply.status_code == 200, reply.content
    reply = post(editor_client, "editor_preview", theme, {})
    assert reply.status_code == 200, reply.content


@pytest.mark.parametrize("images", ["x", 5, {"logo_main": "x"}, {"logo_main": []}])
def test_odd_images_values_are_refused_not_crashing(editor_client, theme, images):
    reply = post(editor_client, "editor_save", theme, {"settings": {"images": images}})
    assert reply.status_code == 400, reply.content


def test_importing_an_export_with_a_flat_image_still_works(theme):
    logo = add_asset(theme, "logo_email", png("l.png"))
    theme.settings = {**theme.settings, "images": {"logo_email": logo.pk}}
    theme.save()
    data = export_theme(theme)
    imported = import_theme(io.BytesIO(data))
    assert imported.pk != theme.pk
    assert "logo_email" in imported.settings["images"]


# QA, third round (#271 review fixes): the slot is still validated


@pytest.mark.parametrize("slot", ["nope", "", "logo_main,icon"])
def test_an_unknown_slot_gets_the_slot_message(editor_client, theme, slot):
    reply = upload(editor_client, theme, slot=slot)
    assert reply.status_code == 400
    assert reply.json()["errors"] == ["Choose where the image goes."]
    assert not ThemeAsset.objects.exists()


def test_an_svg_in_a_no_svg_slot_gets_its_own_message(editor_client, theme):
    url = reverse("capy_theme:editor_upload", args=[theme.pk])
    svg = SimpleUploadedFile(
        "logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 10"/>'
    )
    reply = editor_client.post(url, {"file": svg, "slot": "logo_email"})
    assert reply.status_code == 400
    assert any("SVG" in error for error in reply.json()["errors"])
