"""Tests for the showcase's images and icons section (issue #39)."""

import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from capy_theme.active import activate
from capy_theme.icons import icon_urls
from capy_theme.images import add_asset
from capy_theme.models import Theme
from capy_theme.publishing import publish
from capy_theme.showcase import images

pytestmark = pytest.mark.django_db
URL = "/theme/showcase/"


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff(client, django_user_model):
    client.force_login(django_user_model.objects.create_user("s", password="pw", is_staff=True))
    return client


def png(size=(300, 100), colour="red", name="img.png"):
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue())


@pytest.fixture
def theme():
    return Theme.objects.create(
        name="Main", slug="main", settings={"site_name": "Capy", "tagline": "Hello"}
    )


def choose(theme, **slots):
    theme.settings = {
        **theme.settings,
        "images": {s: {m: a.pk for m, a in modes.items()} for s, modes in slots.items()},
    }
    theme.save()
    revision = publish(theme)
    activate(theme)
    return revision


def logos(revision, mode):
    return {logo["slot"]: logo for logo in images(revision)[mode]["logos"]}


def test_the_issue_check_empty_slots_show_their_fallback(theme):
    main = add_asset(theme, "logo_main", "light", png(name="main.png"))
    mark = add_asset(theme, "logo_mark", "light", png((100, 100), name="mark.png"))
    revision = choose(theme, logo_main={"light": main}, logo_mark={"light": mark})
    light, dark = logos(revision, "light"), logos(revision, "dark")
    assert light["logo_main"]["source"] == "Its own image"
    assert light["logo_stacked"]["source"] == "Empty: falls back to the main logo"
    assert light["logo_stacked"]["url"] == f"/media/{main.original.name}"
    assert dark["logo_mark"]["source"] == "No dark version: uses the light one"
    assert dark["logo_mark"]["url"] == f"/media/{mark.original.name}"
    assert light["logo_main"]["formats"] == ["AVIF", "PNG", "WEBP"]
    assert light["logo_main"]["widths"][-1] == 300
    assert light["logo_email"]["formats"] == []  # email logos have no copies


def test_email_and_print_logos_stay_light_in_dark_mode(theme):
    main = add_asset(theme, "logo_main", "light", png(name="main.png"))
    main_dark = add_asset(theme, "logo_main", "dark", png(colour="blue", name="dark.png"))
    dark = logos(choose(theme, logo_main={"light": main, "dark": main_dark}), "dark")
    assert dark["logo_stacked"]["url"] == f"/media/{main_dark.original.name}"
    for slot in ("logo_email", "logo_print"):
        assert dark[slot]["url"] == f"/media/{main.original.name}"
        assert dark[slot]["source"].startswith("Always the light version")


def test_without_any_logo_slots_show_the_site_name(theme, staff):
    revision = choose(theme)
    assert logos(revision, "light")["logo_main"]["source"] == "Empty: shows the site name"
    content = staff.get(URL).content.decode()
    assert "Images and icons" in content
    assert "No icon chosen" in content
    assert "No sharing image chosen" in content


def test_the_issue_check_new_logo_and_icon_update_every_place(theme, staff):
    first = add_asset(theme, "logo_main", "light", png(name="first.png"))
    icon = add_asset(theme, "icon", "light", png((256, 256), name="icon-one.png"))
    first_revision = choose(theme, logo_main={"light": first}, icon={"light": icon})
    content = staff.get(URL).content.decode()
    # The main logo shows for all four header slots plus email and print, in both modes.
    assert content.count(f'src="/media/{first.original.name}"') >= 12
    old_icons = icon_urls(first_revision.snapshot)
    assert old_icons["icon-192.png"] in content

    second = add_asset(theme, "logo_main", "light", png(colour="blue", name="second.png"))
    icon_two = add_asset(theme, "icon", "light", png((256, 256), "blue", name="icon-two.png"))
    second_revision = choose(theme, logo_main={"light": second}, icon={"light": icon_two})
    content = staff.get(URL).content.decode()
    assert first.original.name not in content
    assert content.count(f'src="/media/{second.original.name}"') >= 12
    for name, url in icon_urls(second_revision.snapshot).items():
        assert url in content, name
    assert old_icons["icon-192.png"] not in content


def test_every_icon_is_shown(theme, staff):
    icon = add_asset(theme, "icon", "light", png((256, 256)))
    revision = choose(theme, icon={"light": icon})
    content = staff.get(URL).content.decode()
    for name in icon_urls(revision.snapshot):
        assert f'data-capy-icon="{name}"' in content
    assert "Maskable icon in a circle" in content
    assert "Maskable icon in a squircle" in content
    assert 'width="180" height="180"' in content  # the Apple icon at its real size


def test_sharing_image(theme, staff):
    share = add_asset(theme, "social", "light", png((1300, 700)), "Our shop")
    choose(theme, social={"light": share})
    content = staff.get(URL).content.decode()
    image = content.split("data-capy-sharing-image", 1)[0].rsplit("<img", 1)[1]
    assert "-1200x630.png" in image
    assert 'alt="Our shop"' in image
    assert "manifest" not in content.lower()


def test_backgrounds_use_the_helper_classes(theme, staff):
    pattern = add_asset(theme, "background_pattern", "light", png((16, 16)))
    choose(theme, background_pattern={"light": pattern})
    content = staff.get(URL).content.decode()
    assert 'class="capy-bg-pattern h-24' in content
    assert "Page background pattern: <code>.capy-bg-pattern</code>" in content
    assert "Login background: not set" in content


def test_without_an_active_theme(staff):
    assert images(None) is None
    assert "there are no images to show" in staff.get(URL).content.decode()
