"""Checks the demo site in demo/ still starts, so it can't break unnoticed.

The demo runs in a separate process because it has its own settings.
"""

import os
import subprocess  # noqa: S404
import sys
from pathlib import Path

MANAGE = Path(__file__).resolve().parents[1] / "demo" / "manage.py"


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


def test_demo_header_logo_uses_the_themes_header_height():
    # A huge logo is shown at the theme's header height (issue #91, then #34).
    code = (
        "import io; from PIL import Image; "
        "from django.core.files.base import ContentFile; "
        "from django.core.management import call_command; "
        "call_command('migrate', verbosity=0); "
        "from django.conf import settings; import tempfile; "
        "settings.MEDIA_ROOT = tempfile.mkdtemp(); "
        "from capy_theme.models import Theme; "
        "from capy_theme.themes.publishing import publish; "
        "from capy_theme.themes.active import activate; "
        "b = io.BytesIO(); Image.new('RGB', (2000, 1000), 'red').save(b, 'PNG'); "
        "from django.core.files.uploadedfile import SimpleUploadedFile; "
        "from capy_theme.images.uploads import add_asset; "
        "t = Theme.objects.create(name='Big', slug='big'); "
        "a = add_asset(t, 'logo_main', 'light', SimpleUploadedFile('big.png', b.getvalue())); "
        "t.settings = {'images': {'logo_main': {'light': a.pk}}}; t.save(); "
        "r = publish(t); activate(t); "
        "from capy_theme.css.stylesheet import render_css; "
        "from django.test import Client; "
        "html = Client().get('/', SERVER_NAME='localhost').content.decode(); "
        "print('class=\"capy-logo\"' in html, 'img.capy-logo { height: 40px' in render_css(r))"
    )
    result = run_manage("shell", "--no-imports", "-c", code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["True", "True"], result.stdout


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


def test_demo_showcase_keeps_the_demo_navbar():
    # The demo sets CAPY_THEME_BASE_TEMPLATE = "base.html" (issue #90).
    code = (
        "from django.core.management import call_command; "
        "call_command('migrate', verbosity=0); "
        "from django.contrib.auth.models import User; "
        "from django.test import Client; "
        "c = Client(); "
        "c.force_login(User.objects.create_user('s', password='pw', is_staff=True)); "
        "html = c.get('/theme/showcase/', SERVER_NAME='localhost').content.decode(); "
        "print('Theme showcase' in html, 'Capy Theme demo' in html, "
        "'href=\"/admin/\"' in html, 'href=\"/\"' in html)"
    )
    result = run_manage("shell", "--no-imports", "-c", code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["True", "True", "True", "True"], result.stdout


def test_demo_navbar_has_the_mode_toggle():
    # The demo shows {% theme_mode_toggle %} in its navbar (issue #46).
    code = (
        "from django.core.management import call_command; "
        "call_command('migrate', verbosity=0); "
        "from capy_theme.models import Theme; "
        "from capy_theme.themes.publishing import publish; "
        "from capy_theme.themes.active import activate; "
        "t = Theme.objects.create(name='M', slug='m'); publish(t); activate(t); "
        "from django.test import Client; "
        "html = Client().get('/', SERVER_NAME='localhost').content.decode(); "
        "print(html.count('data-capy-mode='))"
    )
    result = run_manage("shell", "--no-imports", "-c", code)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["3"], result.stdout
