"""Checks the demo site in demo/ still starts, so it can't break unnoticed.

The demo runs in a separate process because it has its own settings.
"""

import os
import subprocess  # noqa: S404
import sys
from pathlib import Path

MANAGE = Path(__file__).resolve().parent.parent / "demo" / "manage.py"


def run_manage(*args):
    # Drop the test settings pytest set, so the demo uses its own, and use a
    # throwaway in-memory database so the tests never read or change
    # demo/db.sqlite3 (and work on a fresh copy of the repo).
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
    env["DATABASE_URL"] = "sqlite://:memory:"
    return subprocess.run(  # noqa: S603
        [sys.executable, str(MANAGE), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_demo_site_passes_django_checks():
    result = run_manage("check")
    assert result.returncode == 0, result.stderr


def test_demo_home_page_renders():
    # Renders / with Django's test client inside the demo's own settings.
    code = (
        "from django.core.management import call_command; "
        "call_command('migrate', verbosity=0); "
        "from django.test import Client; "
        "r = Client().get('/', SERVER_NAME='localhost'); "
        "print(r.status_code); "
        "print('btn-primary' in r.content.decode())"
    )
    result = run_manage("shell", "--no-imports", "-c", code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["200", "True"], result.stdout
