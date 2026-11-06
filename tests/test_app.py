"""Checks every module should keep passing."""

from io import StringIO

import pytest
from django.apps import apps
from django.core.management import call_command


def test_app_is_installed():
    config = apps.get_app_config("capy_theme")
    assert config.verbose_name == "Capy Theme"


@pytest.mark.django_db
def test_migrations_are_up_to_date():
    # Fails if a model changed without `makemigrations`, which would break
    # every project that installs this version.
    call_command(
        "makemigrations",
        "capy_theme",
        "--check",
        "--dry-run",
        stdout=StringIO(),
    )
