"""Tests for the showcase's colour and shape sections (issue #21)."""

import pytest
from django.core.cache import cache

from capy_theme.active import activate
from capy_theme.builtin_themes import THEMES
from capy_theme.models import Theme
from capy_theme.publishing import publish
from capy_theme.showcase import shape_samples, swatches

pytestmark = pytest.mark.django_db
URL = "/theme/showcase/"
PINK = "oklch(65% 0.24 350)"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff(client, django_user_model):
    client.force_login(django_user_model.objects.create_user("s", password="pw", is_staff=True))
    return client


def live(settings_values):
    theme = Theme.objects.create(name="Main", slug="main", settings=settings_values)
    revision = publish(theme)
    activate(theme)
    return theme, revision


def test_a_swatch_for_every_colour_in_both_modes():
    _, revision = live({})
    result = swatches(revision)
    assert set(result) == {"light", "dark"}
    assert len(result["light"]) == len(result["dark"]) == 20


def test_swatches_say_where_each_colour_comes_from():
    _, revision = live({"colors": {"light": {"primary": PINK}}})
    light = {s["name"]: s for s in swatches(revision)["light"]}
    assert light["primary"]["source"] == "overridden"
    assert light["primary"]["oklch"] == PINK
    assert light["primary-content"]["source"] == "worked out"
    assert light["secondary"]["source"] == "base theme"
    dark = {s["name"]: s for s in swatches(revision)["dark"]}
    assert dark["primary"]["source"] == "base theme"


def test_swatches_have_values_and_contrast():
    _, revision = live({})
    primary = next(s for s in swatches(revision)["light"] if s["name"] == "primary")
    assert primary["hex"].startswith("#")
    assert primary["text"] == "primary-content"
    assert primary["rating"] in ("AA", "AAA", "fail")
    assert primary["fg"] == "primary-content"
    base_text = next(s for s in swatches(revision)["light"] if s["name"] == "base-content")
    assert base_text["fg"] == "base-100"


def test_failing_pair_shows_the_same_warning_as_the_admin(staff):
    live({"colors": {"light": {"base-100": "oklch(100% 0 0)", "base-content": "oklch(85% 0 0)"}}})
    content = staff.get(URL).content.decode()
    assert "⚠ fails AA" in content


def test_changing_a_colour_and_publishing_updates_the_swatch(staff):
    theme, _ = live({})
    assert PINK not in staff.get(URL).content.decode()
    theme.settings = {"colors": {"light": {"primary": PINK}}}
    theme.save()
    publish(theme)
    assert PINK in staff.get(URL).content.decode()


def test_shape_samples_show_current_values(staff):
    theme, revision = live({"shape": {"radius_box": 0, "depth": False}})
    samples = shape_samples(revision)["light"]
    sizes = {s["name"]: s["value"] for s in samples["sizes"]}
    assert sizes["radius_box"] == "0rem"
    effects = {e["name"]: e["on"] for e in samples["effects"]}
    assert effects["depth"] is False
    content = staff.get(URL).content.decode()
    assert "Shape and effects" in content
    assert "<code>0rem</code>" in content
    assert "var(--radius-box)" in content
    assert "Depth on" in content and "Depth off" in content


def test_without_an_active_theme_it_shows_daisyui_defaults(staff):
    result = swatches(None)
    light = {s["name"]: s for s in result["light"]}
    assert light["primary"]["oklch"] == THEMES["light"]["values"]["--color-primary"]
    assert "Colours" in staff.get(URL).content.decode()
