"""capy-theme logs its important events through its own loggers (issue #208).

The loggers are named after their modules, all under "capy_theme", and capy-theme
sets up no handlers: the project decides where the messages go.
"""

import io
import logging
import urllib.error

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from capy_theme.fonts.google import import_family
from capy_theme.models import Theme
from capy_theme.portability.export import export_theme
from capy_theme.portability.importing import import_theme
from capy_theme.themes.active import activate
from capy_theme.themes.history import restore
from capy_theme.themes.publishing import publish
from tests.support.google import FakeGoogle

pytestmark = pytest.mark.django_db


@pytest.fixture
def logs(caplog):
    caplog.set_level(logging.INFO, logger="capy_theme")
    return caplog


def messages(logs, level=logging.INFO):
    return [(r.name, r.getMessage()) for r in logs.records if r.levelno == level]


def test_publishing_logs_the_revision_and_the_publishers_id(logs):
    user = get_user_model().objects.create_user("editor", password="pw")
    theme = Theme.objects.create(name="Main", slug="main")
    publish(theme, user=user)
    assert messages(logs) == [
        (
            "capy_theme.themes.publishing",
            f"Published theme 'main' as revision 1 (user ID {user.pk}).",
        )
    ]
    assert "editor" not in logs.text  # an ID, never the person's name


def test_publishing_without_a_user_says_so(logs):
    publish(Theme.objects.create(name="Main", slug="main"))
    assert messages(logs) == [
        ("capy_theme.themes.publishing", "Published theme 'main' as revision 1 (no user).")
    ]


def test_restoring_logs_which_revision(logs):
    theme = Theme.objects.create(name="Main", slug="main")
    publish(theme)
    theme.settings = {"site_name": "New"}
    theme.save()
    publish(theme)
    logs.clear()
    restore(theme, theme.revisions.get(number=1))
    assert ("capy_theme.themes.history", "Restored revision 1 of theme 'main' as revision 3.") in (
        messages(logs)
    )


def test_activating_logs_for_which_sites(logs):
    theme = Theme.objects.create(name="Main", slug="main")
    publish(theme)
    logs.clear()
    activate(theme)
    activate(theme, site="Shop.Example.com")
    assert messages(logs) == [
        ("capy_theme.themes.active", "Activated theme 'main' for every site."),
        ("capy_theme.themes.active", "Activated theme 'main' for shop.example.com."),
    ]


def test_importing_a_theme_logs_it(logs, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    data = export_theme(Theme.objects.create(name="Main", slug="main"))
    imported = import_theme(io.BytesIO(data))
    assert messages(logs) == [
        (
            "capy_theme.portability.importing",
            f"Imported theme {imported.slug!r} as an unpublished draft.",
        )
    ]


def test_importing_a_google_font_logs_it(logs, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    import_family("Lora", weights=(400,), italic=False, download=FakeGoogle())
    assert messages(logs) == [
        ("capy_theme.fonts.google", "Imported Google font 'Lora': 1 font file(s) stored.")
    ]


def test_google_fonts_unreachable_is_a_warning(logs):
    def unreachable(url, timeout=60):
        raise urllib.error.URLError("no route to host")

    with pytest.raises(ValidationError):
        import_family("Lora", download=unreachable)
    assert messages(logs, logging.WARNING) == [
        (
            "capy_theme.fonts.google",
            "Google Fonts couldn't be reached for 'Lora': <urlopen error no route to host>",
        )
    ]


def test_capy_theme_sets_up_no_handlers():
    # capy-theme adds no handlers of its own; the project's LOGGING decides.
    names = [n for n in logging.root.manager.loggerDict if n.split(".")[0] == "capy_theme"]
    assert "capy_theme.themes.publishing" in names
    assert all(not logging.getLogger(n).handlers for n in names)
