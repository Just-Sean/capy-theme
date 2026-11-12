"""Tests for revision history: compare and restore (issue #44)."""

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.models import Theme
from capy_theme.themes.active import activate, get_active_theme
from capy_theme.themes.history import compare, describe, restore
from capy_theme.themes.publishing import NothingToPublish, publish

pytestmark = pytest.mark.django_db
PINK = "oklch(65% 0.24 350)"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def theme():
    """A theme with three revisions: plain, pink primary, then cupcake + square boxes."""
    theme = Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy"})
    publish(theme)
    theme.settings = {"site_name": "Capy", "colors": {"light": {"primary": PINK}}}
    theme.save()
    publish(theme)
    theme.light_base = "cupcake"
    theme.settings = {**theme.settings, "shape": {"radius_box": 0}}
    theme.save()
    publish(theme)
    activate(theme)
    return theme


def rev(theme, number):
    return theme.revisions.get(number=number)


def test_describe_names_every_value(theme):
    rows = describe(rev(theme, 3).snapshot)
    assert rows["Light base"] == "cupcake"
    assert rows["Light colour: Primary"] == PINK
    assert rows["Dark colour: Primary"] is None
    assert rows["Shape: Box corner radius"] == 0
    assert rows["Site name"] == "Capy"


def test_compare_shows_exactly_what_changed(theme):
    assert compare(rev(theme, 1), rev(theme, 2)) == [
        {"name": "Light colour: Primary", "older": None, "newer": PINK}
    ]
    names = [row["name"] for row in compare(rev(theme, 2), rev(theme, 3))]
    assert names == ["Light base", "Shape: Box corner radius"]


def test_compare_identical_revisions(theme):
    assert compare(rev(theme, 2), rev(theme, 2)) == []


def test_restore_publishes_the_old_revision_as_a_new_one(theme):
    new = restore(theme, rev(theme, 1))
    assert new.number == 4
    assert new.note == "Restored revision 1"
    assert compare(rev(theme, 1), new) == []
    theme.refresh_from_db()
    assert theme.live_revision == new
    assert theme.light_base == "light" and "colors" not in theme.settings
    assert theme.revisions.count() == 4  # nothing deleted
    assert get_active_theme().live_revision.number == 4  # the site shows it


def test_restoring_the_live_revision_does_nothing(theme):
    with pytest.raises(NothingToPublish):
        restore(theme, rev(theme, 3))


def test_restore_brings_back_the_old_logo(settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = tmp_path
    png = _png_bytes()
    from capy_theme.images.uploads import add_asset

    theme = Theme.objects.create(name="Logo", slug="logo")
    one = add_asset(theme, "logo_main", "light", SimpleUploadedFile("one.png", png))
    theme.settings = {"images": {"logo_main": {"light": one.pk}}}
    theme.save()
    first = publish(theme)
    two = add_asset(theme, "logo_main", "light", SimpleUploadedFile("two.png", png))
    theme.settings = {"images": {"logo_main": {"light": two.pk}}}
    theme.save()
    publish(theme)
    restore(theme, first)
    theme.refresh_from_db()
    assert theme.settings["images"] == {"logo_main": {"light": one.pk}}
    assert theme.live_revision.snapshot["images"] == first.snapshot["images"]


def test_restore_skips_images_deleted_since(settings, tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from capy_theme.images.uploads import add_asset

    settings.MEDIA_ROOT = tmp_path
    theme = Theme.objects.create(name="Logo", slug="logo")
    upload = SimpleUploadedFile("one.png", _png_bytes())
    one = add_asset(theme, "logo_main", "light", upload)
    theme.settings = {"site_name": "A", "images": {"logo_main": {"light": one.pk}}}
    theme.save()
    first = publish(theme)
    theme.settings = {"site_name": "B"}
    theme.save()
    publish(theme)
    one.delete()
    restore(theme, first)
    theme.refresh_from_db()
    assert theme.settings == {"site_name": "A"}


def _png_bytes():
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, "PNG")
    return buffer.getvalue()


# The admin pages


def login(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)
    )
    client.force_login(user)


def revisions_url(theme):
    return reverse("admin:capy_theme_theme_revisions", args=[theme.pk])


def restore_url(theme, number):
    return reverse("admin:capy_theme_theme_restore", args=[theme.pk, number])


def test_revisions_page_lists_and_compares(client, django_user_model, theme):
    login(client, django_user_model, "view_theme", "change_theme")
    content = client.get(revisions_url(theme) + "?a=1&b=2").content.decode()
    assert "Light colour: Primary" in content
    assert PINK in content
    assert "1 value changed." in content
    assert "(live)" in content


def test_revisions_page_defaults_to_the_last_two(client, django_user_model, theme):
    login(client, django_user_model, "view_theme")
    content = client.get(revisions_url(theme)).content.decode()
    assert "2 values changed." in content


def test_theme_page_links_to_revisions(client, django_user_model, theme):
    login(client, django_user_model, "view_theme", "change_theme")
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content.decode()
    assert revisions_url(theme) in content


def test_restore_needs_publish_permission(client, django_user_model, theme):
    login(client, django_user_model, "view_theme", "change_theme")
    assert restore_url(theme, 1) not in client.get(revisions_url(theme)).content.decode()
    assert client.post(restore_url(theme, 1)).status_code == 403
    assert theme.revisions.count() == 3


def test_restore_through_the_admin(client, django_user_model, theme):
    login(client, django_user_model, "view_theme", "change_theme", "publish_theme")
    confirm = client.get(restore_url(theme, 1)).content.decode()
    assert "publishes it as a new" in confirm.replace("<strong>", "").replace("</strong>", "")
    response = client.post(restore_url(theme, 1), follow=True)
    assert "Restored revision 1. It&#x27;s live as revision 4." in response.content.decode()
    theme.refresh_from_db()
    assert theme.live_revision.number == 4


def test_revisions_page_needs_view_or_change_permission(client, django_user_model, theme):
    # Staff with no theme permissions at all can't see a theme's history (issue #181);
    # change permission alone is enough (view only is tested above).
    login(client, django_user_model)
    assert client.get(revisions_url(theme)).status_code == 403
    django_user_model.objects.filter(username="staff").delete()
    login(client, django_user_model, "change_theme")
    assert client.get(revisions_url(theme)).status_code == 200
