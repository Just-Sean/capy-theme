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

from capy_theme.images.assets import where_used
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
    assert where_used(theme, theme.settings, old) == ["revision 1's main logo (light)"]
    html = page(staff, theme)
    data = _post_back(html)
    row = [m for m in re.findall(rf'name="({stem(html)}-\d+)-id" value="(\d+)"', html)]
    prefix = next(p for p, pk in row if pk == str(old.pk))
    data[f"{prefix}-DELETE"] = "on"
    response = staff.post(url(theme), data)
    assert response.status_code == 200
    media = media_panel(response)
    assert "restoring that revision needs it" in media
    assert ThemeAsset.objects.filter(pk=old.pk).exists()


def test_the_advice_says_to_publish_when_the_published_theme_uses_it(theme):
    from capy_theme.images.assets import refusal

    asset = add_asset(theme, "logo_main", "light", png())
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    publish(theme)
    theme.refresh_from_db()
    text = refusal(theme, {}, asset)  # unset in the draft, still published
    assert "the published theme's main logo (light)" in text
    assert text.endswith("and save, then publish.")
    assert refusal(theme, {}, add_asset(theme, "logo_main", "light", png())) == ""


def test_an_old_dark_email_choice_doesnt_block_deleting(theme):
    """Email logos have no dark choice any more; one left in old data doesn't count."""
    asset = add_asset(theme, "logo_email", "light", png())
    assert where_used(theme, {"images": {"logo_email": {"dark": asset.pk}}}, asset) == []
