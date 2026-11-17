"""The theme page's images (#271): uploaded and chosen where they're used, with
editable alt text, and a Media list to manage them."""

import io
import re
from unittest import mock

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from capy_theme.images.assets import refusal, revisions_of, where_used
from capy_theme.images.models import ThemeAsset
from capy_theme.images.uploads import add_asset
from capy_theme.models import Theme
from capy_theme.themes.publishing import publish

from .test_admin_tabs import panels
from .test_admin_tabs_unchanged import _post_back

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def png(name="logo.png", size=(40, 20)):
    buffer = io.BytesIO()
    Image.new("RGBA", size, (0, 128, 255, 255)).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


@pytest.fixture
def staff(client, django_user_model):
    """Staff with only the theme permissions: managing images is part of editing."""
    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(codename__in=["view_theme", "change_theme"])
    )
    client.force_login(user)
    return client


def url(theme):
    return reverse("admin:capy_theme_theme_change", args=[theme.pk])


def page(client, theme):
    return client.get(url(theme)).content.decode()


def errors(response):
    return re.findall(r'<ul class="errorlist[^>]*>.*?</ul>', response.content.decode(), re.S)


# Each slot: what it's for, its current image, earlier uploads, a new upload, alt text


def test_every_slot_explains_what_its_for_and_its_limits(staff, theme):
    html = page(staff, theme)
    assert "Most sites only need this one" in html  # main logo
    assert "Your symbol above your name, for narrow spaces" in html  # stacked
    assert "Just the symbol, without the name" in html  # mark
    assert "show SVG, so use a PNG or JPEG" in html  # email
    assert "Up to 2 MB and 4000 px, PNG, JPEG, WebP, GIF or SVG." in html
    assert "Up to 1 MB and 2000 px, PNG, JPEG, WebP or GIF." in html  # email: no SVG
    assert "The version for dark mode." in html


def test_the_main_logo_is_up_front_and_the_others_are_under_more(staff, theme):
    by_label = {label: body for _, label, body in panels(page(staff, theme))}
    branding = by_label["Branding"]
    logos = branding[branding.index(">Logos<") : branding.index(">More logo versions")]
    assert 'name="image_logo_main_light"' in logos
    assert 'name="image_logo_stacked_light"' not in logos
    more = branding[branding.index(">More logo versions") :]
    for slot in ("stacked", "mark", "wordmark", "email", "print"):
        assert f'name="image_logo_{slot}_light"' in more


def test_a_slot_shows_its_current_image_and_offers_its_earlier_uploads(staff, theme):
    old = add_asset(theme, "logo_main", "light", png("old.png"), "Old logo")
    new = add_asset(theme, "logo_main", "light", png("new.png"), "New logo")
    add_asset(theme, "logo_mark", "light", png("mark.png"))
    theme.settings = {"images": {"logo_main": {"light": new.pk}}}
    theme.save()
    html = page(staff, theme)
    field = html[html.index('name="image_logo_main_light"') :]
    field = field[: field.index("</select>")]
    assert f'<option value="{new.pk}" selected>' in field
    assert f'<option value="{old.pk}">' in field
    assert "mark.png" not in field  # only this slot's images
    assert f'src="{new.original.url}" alt="New logo"' in html  # the current image
    assert re.search(r'name="image_logo_main_light_alt"[^>]*value="New logo"', html)
    # A slot without an image says what happens instead.
    assert "No image: the main logo is used." in html


def test_an_svg_cant_be_picked_where_it_isnt_allowed(staff, theme):
    html = page(staff, theme)
    email = html[html.index('name="image_logo_email_light_upload"') :][:200]
    assert 'accept="image/png,image/jpeg,image/webp,image/gif"' in email
    main = html[html.index('name="image_logo_main_light_upload"') :][:200]
    assert "image/svg+xml" in main


def test_choosing_an_earlier_upload_and_editing_its_alt_text(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Typo lgo")
    data = _post_back(page(staff, theme))
    data["image_logo_main_light"] = str(asset.pk)
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    theme.refresh_from_db()
    assert theme.settings["images"]["logo_main"] == {"light": asset.pk}
    # Now it's the current image, its alt text can be edited (#271: after upload).
    data = _post_back(page(staff, theme))
    assert data["image_logo_main_light_alt_for"] == str(asset.pk)
    data["image_logo_main_light_alt"] = "  Capy Co logo  "
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    asset.refresh_from_db()
    assert asset.alt_text == "Capy Co logo"


def test_a_new_upload_gets_its_own_alt_text_not_the_current_images(staff, theme):
    current = add_asset(theme, "logo_main", "light", png("old.png"), "Old logo")
    theme.settings = {"images": {"logo_main": {"light": current.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))  # the current image's box says "Old logo"
    data["image_logo_main_light_upload"] = png("new.png")
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    new = ThemeAsset.objects.exclude(pk=current.pk).get()
    assert new.alt_text == ""  # not "Old logo"
    current.refresh_from_db()
    assert current.alt_text == "Old logo"


def test_a_forged_alt_for_another_slots_image_is_ignored(staff, theme):
    current = add_asset(theme, "logo_main", "light", png(), "Main")
    mark = add_asset(theme, "logo_mark", "light", png(), "Mark")
    theme.settings = {"images": {"logo_main": {"light": current.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_alt_for"] = str(mark.pk)
    data["image_logo_main_light_alt"] = "Hijacked"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    mark.refresh_from_db()
    current.refresh_from_db()
    assert (mark.alt_text, current.alt_text) == ("Mark", "Main")


def test_choose_again_is_said_when_the_theme_name_is_taken(staff, theme):
    Theme.objects.create(name="Taken", slug="taken")
    data = _post_back(page(staff, theme))
    data["name"] = "Taken"  # only found by the model's own check, after the form's
    data["image_logo_main_light_upload"] = png()
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert "Choose the file again" in response.content.decode()
    assert not ThemeAsset.objects.exists()


def test_several_uploads_in_one_save(staff, theme):
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_upload"] = png("light.png")
    data["image_logo_main_dark_upload"] = png("dark.png")
    data["image_icon_light_upload"] = png("icon.png", (64, 64))
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    theme.refresh_from_db()
    chosen = theme.settings["images"]
    assert set(chosen) == {"logo_main", "icon"}
    assert ThemeAsset.objects.get(pk=chosen["logo_main"]["dark"]).mode == "dark"


def test_a_file_must_be_chosen_again_if_another_field_has_an_error(staff, theme):
    data = _post_back(page(staff, theme))
    data["name"] = ""  # required
    data["image_logo_main_light_upload"] = png()
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert "Choose the file again" in response.content.decode()
    assert not ThemeAsset.objects.exists()


def test_new_themes_can_have_images_from_the_start(client, django_user_model):
    user = django_user_model.objects.create_user("new", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(codename__in=["view_theme", "add_theme", "change_theme"])
    )
    client.force_login(user)
    add = reverse("admin:capy_theme_theme_add")
    data = _post_back(client.get(add).content.decode())
    data.update({"name": "New", "slug": "new", "image_logo_main_light_upload": png()})
    response = client.post(add, data)
    assert response.status_code == 302, errors(response)
    theme = Theme.objects.get(slug="new")
    assert theme.settings["images"]["logo_main"]["light"] == theme.assets.get().pk


# Media: managing what's there


def test_media_lists_each_image_with_where_its_used(staff, theme):
    used = add_asset(theme, "logo_main", "light", png("used.png"))
    add_asset(theme, "logo_main", "light", png("spare.png"))
    theme.settings = {"images": {"logo_main": {"light": used.pk}}}
    theme.save()
    media = {label: body for _, label, body in panels(page(staff, theme))}["Media"]
    assert "the draft&#x27;s main logo (light)" in media or "the draft's main logo (light)" in media
    assert "Not used: can be deleted" in media
    assert 'class="capy-media-preview"' in media
    assert "style=" not in media  # nothing a strict CSP would block


def stem(html):
    return [s for s in re.findall(r'name="([^"]+)-TOTAL_FORMS"', html) if "asset" in s][0]


def test_an_unused_image_can_be_deleted(staff, theme):
    spare = add_asset(theme, "logo_main", "light", png())
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    assert not ThemeAsset.objects.filter(pk=spare.pk).exists()


def test_an_image_in_use_cant_be_deleted(staff, theme):
    used = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"images": {"logo_main": {"light": used.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    html = response.content.decode()
    media = {label: body for _, label, body in panels(html)}["Media"]
    assert "can&#x27;t be deleted" in media
    assert "choose another image for that slot (or None; for dark mode, Same as light)" in media
    assert ", then publish." not in media  # only the draft uses it
    assert 'class="errornote"' in html  # the page says something went wrong
    assert "<details open" in media or "<details>" not in media  # the list is unfolded
    assert f'name="{stem(html)}-0-DELETE"' in media
    assert not re.search(rf'name="{stem(html)}-0-DELETE"[^>]*checked', media)  # unticked
    assert ThemeAsset.objects.filter(pk=used.pk).exists()


def test_unsetting_an_image_and_deleting_it_in_one_save_works(staff, theme):
    used = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"images": {"logo_main": {"light": used.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data["image_logo_main_light"] = ""
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    assert not ThemeAsset.objects.exists()


def test_alt_text_can_be_edited_in_media(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-alt_text"] = "New"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    asset.refresh_from_db()
    assert asset.alt_text == "New"


def test_media_has_no_upload_form(staff, theme):
    media = {label: body for _, label, body in panels(page(staff, theme))}["Media"]
    assert 'type="file"' not in media


def test_where_used_counts_the_draft_and_the_live_revision(theme):
    asset = add_asset(theme, "logo_main", "light", png())
    assert where_used(theme, theme.settings, asset) == []
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    publish(theme)
    theme.refresh_from_db()
    assert where_used(theme, theme.settings, asset) == [
        "the draft's main logo (light)",
        "the published theme's main logo (light)",
    ]
    # Unset in the draft but still live: still in use.
    assert where_used(theme, {}, asset) == ["the published theme's main logo (light)"]


# QA (#271)


def svg():
    return SimpleUploadedFile(
        "logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 10"/>'
    )


def media_panel(response):
    return {label: body for _, label, body in panels(response.content.decode())}["Media"]


# Alt text follows the image that's chosen


def test_choosing_another_earlier_image_keeps_its_own_alt_text(staff, theme):
    first = add_asset(theme, "logo_main", "light", png("a.png"), "First logo")
    second = add_asset(theme, "logo_main", "light", png("b.png"), "Second logo")
    theme.settings = {"images": {"logo_main": {"light": first.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))  # the alt box shows "First logo"
    data["image_logo_main_light"] = str(second.pk)  # only the choice changes
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    second.refresh_from_db()
    assert second.alt_text == "Second logo"


def test_choosing_an_earlier_image_for_an_empty_slot_keeps_its_alt_text(staff, theme):
    spare = add_asset(theme, "logo_main", "light", png(), "Capy Co logo")
    data = _post_back(page(staff, theme))  # empty slot: the alt box is empty
    data["image_logo_main_light"] = str(spare.pk)
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    spare.refresh_from_db()
    assert spare.alt_text == "Capy Co logo"


# An error elsewhere on the page


def test_a_file_must_be_chosen_again_when_media_has_an_error(staff, theme):
    """Replace the main logo and delete the old one in one save: the delete is
    refused, the page comes back, and the new file is gone."""
    old = add_asset(theme, "logo_main", "light", png("old.png"))
    theme.settings = {"images": {"logo_main": {"light": old.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data["image_logo_main_light_upload"] = png("new.png")
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert ThemeAsset.objects.count() == 1  # nothing stored
    assert "Choose the file again" in response.content.decode()


# Choices that aren't this slot's


@pytest.mark.parametrize("bad", ["other_slot", "other_theme", "abc", "999999", "-1", "1.0"])
def test_a_choice_that_isnt_this_slots_is_refused(staff, theme, bad):
    current = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"images": {"logo_main": {"light": current.pk}}}
    theme.save()
    mark = add_asset(theme, "logo_mark", "light", png())
    theirs = add_asset(Theme.objects.create(name="O", slug="o"), "logo_main", "light", png())
    value = {"other_slot": str(mark.pk), "other_theme": str(theirs.pk)}.get(bad, bad)
    data = _post_back(page(staff, theme))
    data["image_logo_main_light"] = value
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert "Choose one of this slot" in response.content.decode()
    theme.refresh_from_db()
    assert theme.settings["images"] == {"logo_main": {"light": current.pk}}


def test_a_dark_upload_can_be_chosen_for_light(staff, theme):
    """Choices are by slot, not mode (documented: images stay with their slot)."""
    dark = add_asset(theme, "logo_main", "dark", png())
    data = _post_back(page(staff, theme))
    data["image_logo_main_light"] = str(dark.pk)
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)


# Uploads


def test_an_svg_is_refused_in_a_slot_without_svg(staff, theme):
    data = _post_back(page(staff, theme))
    data["image_logo_email_light_upload"] = svg()
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert "can&#x27;t be an SVG" in response.content.decode()
    assert not ThemeAsset.objects.exists()


def test_an_svg_is_fine_in_the_main_logo(staff, theme):
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_upload"] = svg()
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    assert ThemeAsset.objects.get().content_type == "image/svg+xml"


def test_an_oversized_file_is_refused_before_it_is_read(staff, theme, settings):
    settings.CAPY_THEME_IMAGE_MAX_BYTES = 100  # the PNG is bigger than this
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_upload"] = png(size=(400, 400))
    with mock.patch(
        "capy_theme.images.uploads.prepare_image", side_effect=AssertionError("read")
    ) as prepare:
        response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert "too big" in response.content.decode()
    prepare.assert_not_called()
    assert not ThemeAsset.objects.exists()


def test_a_bad_upload_isnt_told_to_choose_again(staff, theme):
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_upload"] = SimpleUploadedFile("x.png", b"not an image")
    response = staff.post(url(theme), data)
    html = response.content.decode()
    assert response.status_code == 200
    assert "isn&#x27;t a supported image" in html
    assert "Choose the file again" not in html


def test_an_upload_wins_over_choosing_an_earlier_image(staff, theme):
    earlier = add_asset(theme, "logo_main", "light", png("earlier.png"))
    data = _post_back(page(staff, theme))
    data["image_logo_main_light"] = str(earlier.pk)
    data["image_logo_main_light_upload"] = png("new.png")
    data["image_logo_main_light_upload_alt"] = "New"  # the new image's own alt box
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    theme.refresh_from_db()
    new = ThemeAsset.objects.exclude(pk=earlier.pk).get()
    assert theme.settings["images"]["logo_main"]["light"] == new.pk
    assert new.alt_text == "New"
    earlier.refresh_from_db()
    assert earlier.alt_text == ""  # the earlier image's alt isn't touched


def test_uploads_in_different_sections_in_one_save(staff, theme):
    data = _post_back(page(staff, theme))
    data["image_social_light_upload"] = png("s.png", (600, 315))
    data["image_background_login_dark_upload"] = png("bg.png", (200, 200))
    data["image_logo_print_light_upload"] = png("p.png")
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    theme.refresh_from_db()
    assert set(theme.settings["images"]) == {"social", "background_login", "logo_print"}
    assert set(theme.settings["images"]["background_login"]) == {"dark"}


def test_email_and_print_dark_fields_posted_anyway_are_ignored(staff, theme):
    data = _post_back(page(staff, theme))
    assert "image_logo_email_dark" not in data
    data["image_logo_email_dark_upload"] = png()
    data["image_logo_print_dark_upload"] = png()
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    theme.refresh_from_db()
    assert "images" not in theme.settings
    assert not ThemeAsset.objects.exists()


# Alt text


@pytest.mark.parametrize(
    ("typed", "stored"),
    [
        ("   ", ""),
        ("  Logo  ", "Logo"),
        ("x" * 250, "x" * 200),
        ("Capy 🐹 Ünïcode", "Capy 🐹 Ünïcode"),
    ],
)
def test_alt_text_is_trimmed_and_limited(staff, theme, typed, stored):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_alt"] = typed
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    asset.refresh_from_db()
    assert asset.alt_text == stored


def test_an_alt_text_edit_in_media_isnt_undone_by_the_slot(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-alt_text"] = "New"  # the slot's box still says "Old"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    asset.refresh_from_db()
    assert asset.alt_text == "New"


# Media: deleting


def test_an_image_only_the_live_revision_uses_cant_be_deleted(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    publish(theme)
    theme.refresh_from_db()
    theme.settings = {}
    theme.save()  # unset in the draft, still live
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert "published theme" in media_panel(response)
    assert ThemeAsset.objects.filter(pk=asset.pk).exists()


def test_deleting_two_where_one_is_in_use_deletes_neither(staff, theme):
    used = add_asset(theme, "logo_main", "light", png("used.png"))
    spare = add_asset(theme, "logo_main", "light", png("spare.png"))
    theme.settings = {"images": {"logo_main": {"light": used.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    prefix = stem(html)
    data[f"{prefix}-0-DELETE"] = "on"
    data[f"{prefix}-1-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert ThemeAsset.objects.filter(pk__in=[used.pk, spare.pk]).count() == 2
    theme.refresh_from_db()
    assert theme.settings["images"]["logo_main"]["light"] == used.pk


def test_an_image_used_in_another_slot_mode_cant_be_deleted(staff, theme):
    """Chosen for dark (by slot, not mode): still counted as in use."""
    asset = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"images": {"logo_main": {"dark": asset.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert ThemeAsset.objects.filter(pk=asset.pk).exists()


def test_a_user_without_change_theme_cant_delete_from_media(client, django_user_model, theme):
    from django.contrib.auth.models import Permission

    asset = add_asset(theme, "logo_main", "light", png())
    user = django_user_model.objects.create_user("viewer", password="pw", is_staff=True)
    user.user_permissions.set(Permission.objects.filter(codename="view_theme"))
    client.force_login(user)
    html = client.get(url(theme)).content.decode()
    assert 'type="file"' not in html
    data = _post_back(html)
    data["form-0-DELETE"] = "on"
    response = client.post(url(theme), data)
    assert response.status_code == 403
    assert ThemeAsset.objects.filter(pk=asset.pk).exists()


# Fixes after review (#271)


def test_an_image_an_earlier_revision_uses_cant_be_deleted(staff, theme):
    """Restoring that revision needs it (restore drops images that are gone)."""
    old = add_asset(theme, "logo_main", "light", png("old.png"))
    new = add_asset(theme, "logo_main", "light", png("new.png"))
    theme.settings = {"images": {"logo_main": {"light": old.pk}}}
    theme.save()
    publish(theme)  # revision 1 uses old
    theme.settings = {"images": {"logo_main": {"light": new.pk}}}
    theme.save()
    publish(theme)  # revision 2 (live) uses new
    theme.refresh_from_db()
    assert where_used(theme, theme.settings, old) == ["1 earlier revision"]
    html = page(staff, theme)
    data = _post_back(html)
    row = [m for m in re.findall(rf'name="({stem(html)}-\d+)-id" value="(\d+)"', html)]
    prefix = next(p for p, pk in row if pk == str(old.pk))
    data[f"{prefix}-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    media = media_panel(response)
    assert "once an image has been published, it stays in Media" in media
    assert ThemeAsset.objects.filter(pk=old.pk).exists()


def test_the_advice_never_sends_people_in_a_circle(theme):
    """Publishing makes the live revision an earlier one, which still keeps the image,
    so "publish, then delete" could never work: a published image stays (#271)."""
    from capy_theme.images.assets import refusal

    asset = add_asset(theme, "logo_main", "light", png())
    assert refusal(theme, {"images": {"logo_main": {"light": asset.pk}}}, asset).endswith(
        "and save; then delete it."
    )  # only the draft uses it: that can be undone
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    publish(theme)
    theme.refresh_from_db()
    text = refusal(theme, {}, asset)  # unset in the draft, still published
    assert "the published theme's main logo (light)" in text
    assert "it stays in Media" in text and "then publish" not in text
    assert refusal(theme, {}, add_asset(theme, "logo_main", "light", png())) == ""


def test_many_revisions_are_counted_not_listed(theme):
    asset = add_asset(theme, "logo_main", "light", png())
    for tagline in ("a", "b", "c"):
        theme.settings = {"tagline": tagline, "images": {"logo_main": {"light": asset.pk}}}
        theme.save()
        publish(theme)
    theme.refresh_from_db()
    assert where_used(theme, {}, asset) == [
        "the published theme's main logo (light)",
        "2 earlier revisions",
    ]


def test_an_old_dark_email_choice_doesnt_block_deleting(theme):
    """Email logos have no dark choice any more; one left in old data doesn't count."""
    asset = add_asset(theme, "logo_email", "light", png())
    assert where_used(theme, {"images": {"logo_email": {"dark": asset.pk}}}, asset) == []


# QA, second round (#271 review fixes)


def row_prefix(html, asset):
    rows = re.findall(rf'name="({stem(html)}-\d+)-id" value="(\d+)"', html)
    return next(p for p, pk in rows if pk == str(asset.pk))


# Alt text: the same image shown in light and dark


def test_editing_the_light_alt_isnt_undone_by_the_dark_box_showing_the_same_image(staff, theme):
    """Same image chosen for light and dark; only the light box is edited."""
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk, "dark": asset.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    assert data["image_logo_main_dark_alt_for"] == str(asset.pk)
    data["image_logo_main_light_alt"] = "New"  # the dark box still says "Old"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    asset.refresh_from_db()
    assert asset.alt_text == "New"


def test_editing_the_dark_alt_of_an_image_also_shown_for_light(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk, "dark": asset.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_dark_alt"] = "New"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    asset.refresh_from_db()
    assert asset.alt_text == "New"


def test_two_different_alt_edits_for_the_same_image_arent_silently_dropped(staff, theme):
    """Light box says "A", dark box says "B" for one image: one edit is lost with
    no message. Expected: a form error (or at least not a silent 302)."""
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk, "dark": asset.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_alt"] = "A"
    data["image_logo_main_dark_alt"] = "B"
    response = staff.post(url(theme), data)
    assert response.status_code == 200, "one of the two alt edits was silently dropped"


# Alt text: choice changed, uploads, forged alt_for


def test_changing_the_choice_and_editing_the_alt_applies_to_the_image_shown(staff, theme):
    first = add_asset(theme, "logo_main", "light", png("a.png"), "First")
    second = add_asset(theme, "logo_main", "light", png("b.png"), "Second")
    theme.settings = {"images": {"logo_main": {"light": first.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_light"] = str(second.pk)
    data["image_logo_main_light_alt"] = "First, fixed"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    first.refresh_from_db()
    second.refresh_from_db()
    assert (first.alt_text, second.alt_text) == ("First, fixed", "Second")
    theme.refresh_from_db()
    assert theme.settings["images"]["logo_main"]["light"] == second.pk


def test_an_upload_and_an_alt_edit_of_the_current_image_both_apply(staff, theme):
    current = add_asset(theme, "logo_main", "light", png("old.png"), "Old")
    theme.settings = {"images": {"logo_main": {"light": current.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_alt"] = "Old, fixed"
    data["image_logo_main_light_upload"] = png("new.png")
    data["image_logo_main_light_upload_alt"] = "New"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    current.refresh_from_db()
    new = ThemeAsset.objects.exclude(pk=current.pk).get()
    assert (current.alt_text, new.alt_text) == ("Old, fixed", "New")


@pytest.mark.parametrize("forged", ["abc", "-1", "1.0", " ", "999999", "other_theme", "dark"])
def test_garbage_alt_for_is_ignored_without_an_error(staff, theme, forged):
    current = add_asset(theme, "logo_main", "light", png(), "Main")
    other = add_asset(Theme.objects.create(name="O", slug="o"), "logo_main", "light", png(), "O")
    theme.settings = {"images": {"logo_main": {"light": current.pk}}}
    theme.save()
    value = {"other_theme": str(other.pk), "dark": "x" * 5000}.get(forged, forged)
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_alt_for"] = value
    data["image_logo_main_light_alt"] = "Hijacked"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    current.refresh_from_db()
    other.refresh_from_db()
    assert (current.alt_text, other.alt_text) == ("Main", "O")


def test_alt_for_an_image_deleted_in_media_in_the_same_save(staff, theme):
    """Choose another image, edit the old one's alt and delete the old one."""
    old = add_asset(theme, "logo_main", "light", png("old.png"), "Old")
    new = add_asset(theme, "logo_main", "light", png("new.png"), "New")
    theme.settings = {"images": {"logo_main": {"light": old.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data["image_logo_main_light"] = str(new.pk)
    data["image_logo_main_light_alt"] = "Old, edited"
    data[f"{row_prefix(html, old)}-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    assert list(ThemeAsset.objects.values_list("pk", flat=True)) == [new.pk]


def test_the_add_page_ignores_alt_fields(client, django_user_model):
    from django.contrib.auth.models import Permission
    from django.urls import reverse

    other = add_asset(Theme.objects.create(name="O", slug="o"), "logo_main", "light", png(), "O")
    user = django_user_model.objects.create_user("new", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(codename__in=["view_theme", "add_theme", "change_theme"])
    )
    client.force_login(user)
    add = reverse("admin:capy_theme_theme_add")
    html = client.get(add).content.decode()
    assert "image_logo_main_light_alt_for" not in html  # no current image yet
    data = _post_back(html)
    data.update(
        {
            "name": "New",
            "slug": "new",
            "image_logo_main_light_alt_for": str(other.pk),
            "image_logo_main_light_alt": "Hijacked",
        }
    )
    response = client.post(add, data)
    assert response.status_code == 302, errors(response)
    other.refresh_from_db()
    assert other.alt_text == "O"


def test_a_typed_alt_is_kept_when_the_page_comes_back_with_errors(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["name"] = ""
    data["image_logo_main_light_alt"] = "Typed"
    data["image_logo_main_light_upload_alt"] = "For the new one"
    response = staff.post(url(theme), data)
    html = response.content.decode()
    assert response.status_code == 200
    assert re.search(r'name="image_logo_main_light_alt"[^>]*value="Typed"', html)
    assert re.search(r'name="image_logo_main_light_upload_alt"[^>]*value="For the new one"', html)


# Choose the file again


def test_choose_again_on_the_add_page(client, django_user_model):
    from django.contrib.auth.models import Permission
    from django.urls import reverse

    user = django_user_model.objects.create_user("new", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(codename__in=["view_theme", "add_theme", "change_theme"])
    )
    client.force_login(user)
    add = reverse("admin:capy_theme_theme_add")
    data = _post_back(client.get(add).content.decode())
    data.update({"name": "", "slug": "new", "image_logo_main_light_upload": png()})
    response = client.post(add, data)
    assert response.status_code == 200
    assert "Choose the file again" in response.content.decode()
    assert not ThemeAsset.objects.exists()


def test_choose_again_is_said_for_every_upload_when_media_has_an_error(staff, theme):
    used = add_asset(theme, "logo_main", "light", png("used.png"))
    theme.settings = {"images": {"logo_main": {"light": used.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-DELETE"] = "on"  # refused
    data["image_logo_mark_light_upload"] = png("m.png")
    data["image_icon_light_upload"] = png("i.png", (64, 64))
    data["image_social_light_upload"] = png("s.png", (600, 315))
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert response.content.decode().count("Choose the file again") == 3
    assert ThemeAsset.objects.count() == 1


def test_choose_again_isnt_said_for_a_slot_without_an_upload(staff, theme):
    data = _post_back(page(staff, theme))
    data["name"] = ""
    response = staff.post(url(theme), data)
    assert "Choose the file again" not in response.content.decode()


def test_choose_again_with_a_bad_media_alt_text(staff, theme):
    """Another kind of Media row error (too long alt text in Media)."""
    add_asset(theme, "logo_main", "light", png())
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-alt_text"] = "x" * 300  # over the model's 200
    data["image_logo_mark_light_upload"] = png("m.png")
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert "Choose the file again" in response.content.decode()
    assert ThemeAsset.objects.count() == 1


# Media delete refusal


def test_after_a_refused_delete_saving_the_page_again_works(staff, theme):
    used = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"images": {"logo_main": {"light": used.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    again = _post_back(response.content.decode())
    assert f"{stem(html)}-0-DELETE" not in again  # unticked
    response = staff.post(url(theme), again)
    assert response.status_code == 302, errors(response)
    assert ThemeAsset.objects.filter(pk=used.pk).exists()


def test_two_deletes_one_refused_then_the_other_alone_works(staff, theme):
    used = add_asset(theme, "logo_main", "light", png("used.png"))
    spare = add_asset(theme, "logo_main", "light", png("spare.png"))
    theme.settings = {"images": {"logo_main": {"light": used.pk}}}
    theme.save()
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{row_prefix(html, used)}-DELETE"] = "on"
    data[f"{row_prefix(html, spare)}-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    back = response.content.decode()
    again = _post_back(back)
    assert f"{row_prefix(html, used)}-DELETE" not in again  # refused row unticked
    assert again.get(f"{row_prefix(html, spare)}-DELETE") == "on"  # the other stays ticked
    response = staff.post(url(theme), again)
    assert response.status_code == 302, errors(response)
    assert list(ThemeAsset.objects.values_list("pk", flat=True)) == [used.pk]


def test_an_image_only_a_dark_revision_choice_uses_cant_be_deleted(staff, theme):
    asset = add_asset(theme, "logo_main", "dark", png())
    theme.settings = {"images": {"logo_main": {"dark": asset.pk}}}
    theme.save()
    publish(theme)
    theme.settings = {}
    theme.save()
    publish(theme)  # revision 2 has no images; revision 1 used it for dark
    theme.refresh_from_db()
    assert where_used(theme, theme.settings, asset) == ["1 earlier revision"]
    html = page(staff, theme)
    data = _post_back(html)
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    assert "it stays in Media" in media_panel(response)


def test_the_refusal_names_draft_live_and_older_revision_together(theme):
    asset = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    publish(theme)  # revision 1
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}, "site_name": "x"}
    theme.save()
    publish(theme)  # revision 2, live
    theme.refresh_from_db()
    text = refusal(theme, theme.settings, asset)
    assert "the draft's main logo (light)" in text
    assert "the published theme's main logo (light)" in text
    assert "1 earlier revision" in text
    assert "then publish" not in text and "it stays in Media" in text


# assets.py with older or odd data


def test_revisions_of_an_unsaved_theme_and_a_theme_without_revisions(theme):
    assert revisions_of(Theme(name="x", slug="x")) == []
    assert revisions_of(theme) == []


def _revision(theme, number, snapshot):
    from capy_theme.models import ThemeRevision

    return ThemeRevision.objects.create(
        theme=theme, number=number, snapshot=snapshot, css_version=f"qa{theme.pk}r{number}"
    )


@pytest.mark.parametrize(
    "snapshot",
    [
        {},
        {"settings": None},
        {"settings": "text"},
        {"settings": [1, 2]},
        {"settings": {"images": None}},
        {"settings": {"images": []}},
        {"settings": {"images": "logo_main"}},
        {"settings": {"images": 7}},
        {"settings": {"images": {"logo_main": None}}},
        {"settings": {"images": {"logo_main": [1]}}},
        {"settings": {"images": {"logo_main": "x"}}},
        {"logo": "capy_theme/logos/old.png"},  # before logo slots
        [],
        "text",
    ],
)
def test_revisions_of_reads_odd_stored_snapshots(theme, snapshot):
    """Through the database (the JSON path query), not a hand-built list."""
    asset = add_asset(theme, "logo_main", "light", png())
    _revision(theme, 1, snapshot)
    revisions = revisions_of(theme)
    assert [number for number, _images, _live in revisions] == [1]
    assert where_used(theme, {}, asset, revisions) == []
    assert refusal(theme, {}, asset) == ""


@pytest.mark.parametrize(
    "images",
    [{}, None, {"unknown_slot": {"light": 1}}, {"logo_email": {"dark": 1}}, "not a dict"],
)
def test_where_used_ignores_odd_or_impossible_revision_choices(theme, images):
    asset = add_asset(theme, "logo_main", "light", png())
    if isinstance(images, dict):
        images = {slot: {m: asset.pk for m in modes} for slot, modes in images.items()}
    assert where_used(theme, {}, asset, [(1, images, True)]) == []


def test_revisions_of_finds_a_stored_choice_through_the_database(theme):
    asset = add_asset(theme, "logo_main", "dark", png())
    _revision(theme, 1, {"settings": {"images": {"logo_main": {"dark": asset.pk}}}})
    _revision(theme, 2, {"settings": {"images": {"logo_main": {"light": asset.pk}}}})
    _revision(theme, 3, {"settings": {}})
    revisions = revisions_of(theme)
    assert [n for n, _i, _l in revisions] == [3, 2, 1]  # newest first
    assert where_used(theme, {}, asset, revisions) == ["2 earlier revisions"]
    assert "it stays in Media" in refusal(theme, {}, asset)


def test_revisions_of_only_reads_this_themes_revisions(theme):
    other = Theme.objects.create(name="Other", slug="other")
    asset = add_asset(theme, "logo_main", "light", png())
    _revision(other, 1, {"settings": {"images": {"logo_main": {"light": asset.pk}}}})
    assert revisions_of(theme) == []
    assert refusal(theme, {}, asset) == ""


def test_a_legacy_revision_logo_file_isnt_counted_as_in_use(theme):
    """Documents current behavior: a revision from before logo slots shows its logo
    by file name ("logo"), and the migrated asset has that same file. It's reported
    as free to delete (the file itself stays, so the revision still shows it)."""
    asset = add_asset(theme, "logo_main", "light", png())
    snapshot = {"logo": asset.original.name, "settings": {}}
    assert where_used(theme, {}, asset, [(1, snapshot, True)]) == []


def test_a_legacy_dark_email_choice_in_draft_and_live_doesnt_block_delete(staff, theme):
    """Old data: a dark email logo chosen and published before #271."""
    from capy_theme.themes.history import restore

    email = add_asset(theme, "logo_email", "dark", png())
    theme.settings = {"images": {"logo_email": {"dark": email.pk}}}
    theme.save()
    first = publish(theme)
    theme.refresh_from_db()
    html = page(staff, theme)  # the page still loads
    data = _post_back(html)
    data[f"{stem(html)}-0-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    assert not ThemeAsset.objects.exists()
    theme.refresh_from_db()
    assert "images" not in theme.settings
    theme.settings = {"site_name": "changed"}
    theme.save()
    publish(theme)
    restore(theme, first)  # restoring the old revision still works


def test_a_light_only_slots_label_has_no_mode(theme):
    asset = add_asset(theme, "logo_print", "light", png())
    assert where_used(theme, {"images": {"logo_print": {"light": asset.pk}}}, asset) == [
        "the draft's print logo"
    ]


# QA, third round (#271 review fixes)


def test_draft_only_advice_even_when_unrelated_revisions_exist(theme):
    """Published revisions that don't use the image don't make it 'published'."""
    asset = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"site_name": "x"}
    theme.save()
    publish(theme)
    theme.settings = {"site_name": "y"}
    theme.save()
    publish(theme)
    theme.refresh_from_db()
    text = refusal(theme, {"images": {"logo_main": {"light": asset.pk}}}, asset)
    assert text.endswith("and save; then delete it.")
    assert "stays in Media" not in text


def test_a_saved_id_that_no_longer_exists_shows_empty_and_saves(staff, theme):
    Theme.objects.filter(pk=theme.pk).update(settings={"images": {"logo_main": {"light": 999999}}})
    theme.refresh_from_db()
    html = page(staff, theme)
    assert "image_logo_main_light_alt_for" not in html
    assert "Saved:" not in html
    data = _post_back(html)
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    theme.refresh_from_db()
    assert "images" not in theme.settings


def test_the_shown_twice_error_keeps_both_typed_texts(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk, "dark": asset.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_alt"] = "A"
    data["image_logo_main_dark_alt"] = "B"
    response = staff.post(url(theme), data)
    html = response.content.decode()
    assert response.status_code == 200
    assert "shown twice" in html
    assert re.search(r'name="image_logo_main_light_alt"[^>]*value="A"', html)
    assert re.search(r'name="image_logo_main_dark_alt"[^>]*value="B"', html)
    asset.refresh_from_db()
    assert asset.alt_text == "Old"


def test_same_edit_in_both_boxes_after_trimming_is_fine(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk, "dark": asset.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_light_alt"] = "  New "
    data["image_logo_main_dark_alt"] = "New"
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    asset.refresh_from_db()
    assert asset.alt_text == "New"


def test_clearing_the_alt_in_one_box_while_the_other_is_unchanged(staff, theme):
    asset = add_asset(theme, "logo_main", "light", png(), "Old")
    theme.settings = {"images": {"logo_main": {"light": asset.pk, "dark": asset.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["image_logo_main_dark_alt"] = ""
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    asset.refresh_from_db()
    assert asset.alt_text == ""


def test_the_preview_follows_the_saved_image_not_the_failed_choice(staff, theme):
    first = add_asset(theme, "logo_main", "light", png("first.png"), "First")
    second = add_asset(theme, "logo_main", "light", png("second.png"), "Second")
    theme.settings = {"images": {"logo_main": {"light": first.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["name"] = ""
    data["image_logo_main_light"] = str(second.pk)
    response = staff.post(url(theme), data)
    html = response.content.decode()
    field = html[html.index('class="capy-slot-image"') :]
    field = field[: field.index('name="image_logo_main_light_upload"')]
    assert "Saved: first.png" in field
    assert f'name="image_logo_main_light_alt_for" value="{first.pk}"' in field
    assert f'<option value="{second.pk}" selected>' in field
    assert re.search(r'name="image_logo_main_light_alt"[^>]*value="First"', field)


def test_alt_kept_after_failed_save_even_with_a_new_choice(staff, theme):
    first = add_asset(theme, "logo_main", "light", png("first.png"), "First")
    second = add_asset(theme, "logo_main", "light", png("second.png"), "Second")
    theme.settings = {"images": {"logo_main": {"light": first.pk}}}
    theme.save()
    data = _post_back(page(staff, theme))
    data["name"] = ""
    data["image_logo_main_light"] = str(second.pk)
    data["image_logo_main_light_alt"] = "First, typed"
    response = staff.post(url(theme), data)
    assert re.search(
        r'name="image_logo_main_light_alt"[^>]*value="First, typed"', response.content.decode()
    )
    # Fix the name and send the page back as it is: both changes apply.
    again = _post_back(response.content.decode())
    again["name"] = "Main"
    response = staff.post(url(theme), again)
    assert response.status_code == 302, errors(response)
    first.refresh_from_db()
    theme.refresh_from_db()
    assert first.alt_text == "First, typed"
    assert theme.settings["images"]["logo_main"]["light"] == second.pk


def test_dark_box_aria_label_names_the_mode_and_light_only_doesnt(staff, theme):
    html = page(staff, theme)
    assert 'aria-label="Main logo (dark): image to use"' in html
    assert 'aria-label="Email logo: image to use"' in html
