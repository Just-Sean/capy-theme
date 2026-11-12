"""The Components view's final pass (issue #62): every editor setting shows there."""

import io
import json

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from capy_theme.editor.custom_css_view import selectors
from capy_theme.images.uploads import add_asset
from capy_theme.models import Font, Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
SLOTS = [
    "logo_main",
    "logo_stacked",
    "logo_mark",
    "logo_wordmark",
    "logo_email",
    "logo_print",
    "icon",
    "social",
    "background_login",
    "background_pattern",
]


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def png(size=(300, 100), color="red", name="x.png"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue())


@pytest.fixture
def theme():
    theme = Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy"})
    publish(theme)
    activate(theme)
    return theme


def login(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("e", password="pw", is_staff=True)
    for codename in ("change_theme", *codenames):
        user.user_permissions.add(Permission.objects.get(codename=codename))
    client.force_login(user)
    return client


def components(client, theme, changes=None):
    url = reverse("capy_theme:editor_components", args=[theme.pk])
    return client.get(url, {"changes": json.dumps(changes or {})}).content.decode()


def preview_css(client, theme, changes):
    url = reverse("capy_theme:editor_preview", args=[theme.pk])
    return client.post(url, changes, content_type="application/json").json()["css"]


def test_the_issue_check_every_editor_setting_changes_the_components_view(
    client, django_user_model, theme
):
    """Each setting the editor offers changes either the CSS the view gets (colors,
    shape, fonts, type, bases, logo heights) or the view's page (images, icon)."""
    login(client, django_user_model)
    spec = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()["controls"]
    for slot in SLOTS:
        for mode in ("light", "dark"):
            add_asset(theme, slot, mode, png((256, 256), name=f"{slot}-{mode}.png"))
    base_css = preview_css(client, theme, {})
    base_page = components(client, theme)

    def css_changes(changes):
        return preview_css(client, theme, changes) != base_css

    def page_changes(changes):
        return components(client, theme, changes) != base_page

    font = Font.objects.get(family="System serif").pk
    checked = []
    for scheme, names in spec["bases"].items():
        other = next(name for name in names if name != getattr(theme, f"{scheme}_base"))
        assert css_changes({f"{scheme}_base": other}), scheme
        checked.append(f"{scheme} base")
    for group in spec["color_groups"]:
        for color in group["colors"]:
            for mode in ("light", "dark"):
                changes = {"settings": {"colors": {mode: {color["name"]: "oklch(50% 0.2 90)"}}}}
                assert css_changes(changes), color["name"]
                checked.append(f"color {mode} {color['name']}")
    for size in spec["sizes"]:
        assert css_changes({"settings": {"shape": {size["name"]: size["max"]}}}), size["name"]
        checked.append(size["name"])
    for effect in spec["effects"]:
        # On or off, whichever differs from the base theme.
        on = {"settings": {"shape": {effect["name"]: True}}}
        off = {"settings": {"shape": {effect["name"]: False}}}
        assert css_changes(on) or css_changes(off), effect["name"]
        checked.append(effect["name"])
    for role in spec["font_roles"]:
        assert css_changes({"settings": {"fonts": {role["name"]: font}}}), role["name"]
        checked.append(f"font {role['name']}")
    for item in spec["type"]:
        assert css_changes({"settings": {"type": {item["name"]: item["max"]}}}), item["name"]
        checked.append(item["name"])
    for item in spec["logo_heights"]:
        assert css_changes({"settings": {"logo": {item["name"]: 99}}}), item["name"]
        checked.append(item["name"])
    for slot in spec["logo_slots"]:
        for mode in slot["modes"]:
            asset = theme.assets.get(slot=slot["name"], mode=mode)
            changes = {"settings": {"images": {slot["name"]: {mode: asset.pk}}}}
            assert page_changes(changes) or css_changes(changes), (slot["name"], mode)
            checked.append(f"image {slot['name']} {mode}")
    icon = theme.assets.get(slot="icon", mode="light").pk
    for item in spec["icon_settings"]:
        value = "#00ff00" if item["name"] == "background" else 20
        changes = {"settings": {"images": {"icon": {"light": icon}}, "icon": {item["name"]: value}}}
        before = {"settings": {"images": {"icon": {"light": icon}}}}
        assert components(client, theme, changes) != components(client, theme, before)
        checked.append(f"icon {item['name']}")
    assert (
        len(checked)
        == 2 + 40 + len(spec["sizes"]) + len(spec["effects"]) + 4 + len(spec["type"]) + 2 + 19 + 2
    )


def test_unsaved_image_choices_show(client, django_user_model, theme):
    login(client, django_user_model)
    logo = add_asset(theme, "logo_main", "light", png(name="unsaved.png"))
    page = components(client, theme, {"settings": {"images": {"logo_main": {"light": logo.pk}}}})
    assert logo.original.name in page
    assert logo.original.name not in components(client, theme)  # not saved
    theme.refresh_from_db()
    assert "images" not in theme.settings  # nothing was written


def test_says_which_sites_theme_is_showing(client, django_user_model, theme):
    login(client, django_user_model)
    page = components(client, theme)
    assert "on <strong>testserver</strong>" in page
    assert "Visitors on this domain see\n        <strong>Main</strong> (this theme)" in page


def test_text_sample_has_every_heading_and_the_display_font(client, django_user_model, theme):
    login(client, django_user_model)
    page = components(client, theme)
    for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        assert f"<{tag}>" in page
    assert 'class="capy-display' in page


def test_icon_preview(client, django_user_model, theme):
    login(client, django_user_model)
    icon = add_asset(theme, "icon", "light", png((100, 100), "blue", "icon.png"))
    url = reverse("capy_theme:editor_icon_preview", args=[theme.pk])
    response = client.get(url, {"asset": icon.pk, "background": "#00ff00", "padding": "20"})
    assert response["Content-Type"] == "image/png"
    image = Image.open(io.BytesIO(response.content)).convert("RGBA")
    assert image.size == (192, 192)
    assert image.getpixel((5, 5)) == (0, 255, 0, 255)  # padding shows the background
    assert image.getpixel((96, 96))[:3] == (0, 0, 255)
    assert client.get(url, {"asset": 999}).status_code == 400
    client.logout()
    assert client.get(url, {"asset": icon.pk}).status_code == 403


def test_custom_css_for_editors_who_may_edit_it(client, django_user_model, theme):
    theme.settings = {**theme.settings, "custom_css": {"css": ".hero, h1 { color: red }"}}
    theme.save()
    login(client, django_user_model, "edit_custom_css")
    page = components(client, theme)
    assert reverse("capy_theme:editor_custom_css", args=[theme.pk]) in page
    assert "It styles: <code>.hero</code>, <code>h1</code>." in page
    css = client.get(reverse("capy_theme:editor_custom_css", args=[theme.pk]))
    assert css.content.decode() == ".hero, h1 { color: red }"


def test_others_get_only_the_published_custom_css(client, django_user_model, theme):
    theme.settings = {**theme.settings, "custom_css": {"css": ".draft {}"}}
    theme.save()
    login(client, django_user_model)
    page = components(client, theme)
    assert "editor/1/custom.css" not in page and ".draft" not in page
    assert client.get(reverse("capy_theme:editor_custom_css", args=[theme.pk])).status_code == 403


def test_selectors():
    css = "/* a comment { } */ .a, .b > p { x: 1 } @media (min-width: 1px) { .c { y: 2 } } .a {}"
    assert selectors(css) == [".a", ".b > p", ".c"]
