"""Tests for background images (issue #38)."""

import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from capy_theme.admin.theme_form import ThemeForm
from capy_theme.context_processors import theme as theme_context
from capy_theme.css.stylesheet import render_css
from capy_theme.images.uploads import add_asset
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def png(colour="red", name="bg.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), colour).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue())


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


def choose(theme, **slots):
    theme.settings = {
        "images": {s: {m: a.pk for m, a in modes.items()} for s, modes in slots.items()}
    }
    theme.save()
    revision = publish(theme)
    activate(theme)
    return revision


def test_backgrounds_are_css_variables_per_mode(theme):
    login = add_asset(theme, "background_login", "light", png())
    pattern = add_asset(theme, "background_pattern", "light", png("blue"))
    pattern_dark = add_asset(theme, "background_pattern", "dark", png("black"))
    css = render_css(
        choose(
            theme,
            background_login={"light": login},
            background_pattern={"light": pattern, "dark": pattern_dark},
        )
    )
    login_var = f'--capy-bg-login: url("/media/{login.original.name}");'
    light_pattern = f'--capy-bg-pattern: url("/media/{pattern.original.name}");'
    dark_pattern = f'--capy-bg-pattern: url("/media/{pattern_dark.original.name}");'
    # In :root and [data-theme="capy-light"] for light; in the dark media query
    # and [data-theme="capy-dark"] for dark. The login image has no dark version,
    # so dark mode uses the light one.
    assert css.count(login_var) == 4
    assert css.count(light_pattern) == 2
    assert css.count(dark_pattern) == 2
    dark_block = css.split('[data-theme="capy-dark"] {', 1)[1].split("}", 1)[0]
    assert dark_pattern.strip() in dark_block and login_var in dark_block


def test_helper_classes():
    css = render_css(choose(Theme.objects.create(name="X", slug="x")))
    assert ":root .capy-bg-login {" in css
    assert "background-image: var(--capy-bg-login, none);" in css
    assert "background-image: var(--capy-bg-pattern, none);" in css
    assert "--capy-bg-login:" not in css  # no variable without an image


def test_template_values(theme, rf):
    pattern = add_asset(theme, "background_pattern", "light", png())
    choose(theme, background_pattern={"light": pattern})
    values = theme_context(rf.get("/"))["theme"]
    assert values["background_pattern_url"] == f"/media/{pattern.original.name}"
    assert values["background_login_url"] == ""


def test_an_old_single_logo_never_becomes_a_background(theme):
    from capy_theme.css.backgrounds import css_variables

    assert css_variables({"logo": "capy_theme/logos/a.png"}, "light") == {}


def test_svg_patterns_are_allowed(theme):
    svg = SimpleUploadedFile(
        "dots.svg",
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><circle r="1"/></svg>',
    )
    asset = add_asset(theme, "background_pattern", "light", svg)
    assert asset.content_type == "image/svg+xml"
    assert f'url("/media/{asset.original.name}")' in render_css(
        choose(theme, background_pattern={"light": asset})
    )


def test_the_issue_check_admin_background_shows_on_the_demo_page(client, django_user_model, theme):
    client.force_login(django_user_model.objects.create_superuser("s", "s@e.com", "pw"))
    pattern = add_asset(theme, "background_pattern", "light", png())
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    content = client.get(url).content
    assert b'name="image_background_pattern_light"' in content
    form = ThemeForm(
        data={
            "name": "Main",
            "slug": "main",
            "light_base": "light",
            "dark_base": "dark",
            "visitors_can_switch": "on",
            "image_background_pattern_light": str(pattern.pk),
        },
        instance=theme,
    )
    assert form.is_valid(), form.errors
    revision = publish(form.save())
    activate(theme)
    assert f'--capy-bg-pattern: url("/media/{pattern.original.name}")' in render_css(revision)


def test_editor_preview_shows_backgrounds_straight_away(client, django_user_model, theme):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    login = add_asset(theme, "background_login", "dark", png())
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert {"background_login", "background_pattern"} <= {
        s["name"] for s in state["controls"]["logo_slots"]
    }
    url = reverse("capy_theme:editor_preview", args=[theme.pk])
    changes = {"settings": {"images": {"background_login": {"dark": login.pk}}}}
    css = client.post(url, changes, content_type="application/json").json()["css"]
    assert f'--capy-bg-login: url("/media/{login.original.name}")' in css
