"""Tests for contrast warnings (issue #17)."""

import pytest
from django.urls import reverse

from capy_theme.admin import ThemeForm
from capy_theme.builtin_themes import THEMES
from capy_theme.colors import CONTRAST_PAIRS, contrast, contrast_report, draft_values, rating
from capy_theme.models import Theme
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db

LIGHT_GREY = "oklch(85% 0 0)"
WHITE = "oklch(100% 0 0)"


def test_ratings():
    assert rating(7) == "AAA"
    assert rating(4.5) == "AA"
    assert rating(4.49) == "fail"
    assert round(contrast("#000", "#fff"), 1) == 21.0


def test_report_covers_every_pair():
    report = contrast_report(THEMES["light"]["values"])
    assert len(report) == len(CONTRAST_PAIRS) == 11
    assert {"background", "text", "ratio", "rating"} <= set(report[0])


def grey_on_white():
    return Theme.objects.create(
        name="Main",
        slug="main",
        settings={"colors": {"light": {"base-100": WHITE, "base-content": LIGHT_GREY}}},
    )


def test_the_issue_check_light_grey_on_white_fails_aa():
    report = contrast_report(draft_values(grey_on_white(), "light"))
    entry = next(e for e in report if (e["background"], e["text"]) == ("base-100", "base-content"))
    assert entry["rating"] == "fail"


def test_rating_shows_next_to_each_colour_in_the_form():
    form = ThemeForm(instance=grey_on_white())
    help_text = form.fields["color_light_base_content"].help_text
    assert "fails AA" in help_text
    assert "Contrast Background / Text on background:" in help_text
    assert "passes" in form.fields["color_light_primary"].help_text


def test_warnings_dont_stop_saving_or_publishing():
    theme = grey_on_white()
    form = ThemeForm(
        data={
            "name": "Main",
            "slug": "main",
            "light_base": "light",
            "dark_base": "dark",
            "visitors_can_switch": "on",
            "color_light_base_100": WHITE,
            "color_light_base_content": LIGHT_GREY,
        },
        instance=theme,
    )
    assert form.is_valid(), form.errors
    form.save()
    assert publish(theme).number == 1


def test_admin_shows_the_contrast_table(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    theme = grey_on_white()
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content.decode()
    assert "WCAG contrast (saved draft)" in content
    assert "⚠ fails AA" in content
    assert "Background / Text on background" in content


def test_new_theme_has_no_ratings_yet():
    form = ThemeForm()
    assert "Contrast" not in form.fields["color_light_primary"].help_text
