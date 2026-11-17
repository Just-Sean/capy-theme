"""The theme page's images (#271): uploaded and chosen where they're used, with
editable alt text, and a Media list to manage them."""

import io
import re

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
    data["image_logo_main_light_alt"] = "  Capy Co logo  "
    response = staff.post(url(theme), data)
    assert response.status_code == 302, errors(response)
    theme.refresh_from_db()
    asset.refresh_from_db()
    assert theme.settings["images"]["logo_main"] == {"light": asset.pk}
    assert asset.alt_text == "Capy Co logo"  # editable after upload


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
    media = {label: body for _, label, body in panels(response.content.decode())}["Media"]
    assert "can&#x27;t be deleted" in media or "can't be deleted" in media
    assert "set it to None" in media
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
