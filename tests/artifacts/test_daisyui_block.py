"""Tests for the daisyUI theme block download (issue #55)."""

import subprocess  # noqa: S404
from pathlib import Path

import pytest
from django.core.cache import cache

from capy_theme.colors.values import effective_values
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
URL = "/theme/daisyui-theme.css"
REPO = Path(__file__).resolve().parents[2]
CLI = sorted((REPO / "demo" / ".django_tailwind_cli").glob("tailwindcss-*"))
PLUGINS = REPO / "demo" / "tailwind"


@pytest.fixture(autouse=True)
def clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def live():
    theme = Theme.objects.create(
        name="Main",
        slug="main",
        light_base="cupcake",
        dark_base="dracula",
        settings={
            "colors": {"light": {"primary": "oklch(65% 0.24 350)"}},
            "shape": {"radius_box": 1, "noise": True},
        },
    )
    revision = publish(theme)
    activate(theme)
    return revision


def test_two_blocks_with_every_daisyui_variable(client, live):
    response = client.get(URL)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/css; charset=utf-8"
    assert response["Content-Disposition"] == 'attachment; filename="main.daisyui-theme.css"'
    css = response.content.decode()
    assert css.count('@plugin "daisyui/theme" {') == 2
    light, dark = css.split('@plugin "daisyui/theme" {')[1:]
    assert 'name: "main-light";' in light and "default: true;" in light
    assert "prefersdark: false;" in light and "color-scheme: light;" in light
    assert 'name: "main-dark";' in dark and "prefersdark: true;" in dark
    assert "--color-primary: oklch(65% 0.24 350);" in light
    assert "--radius-box: 1rem;" in light and "--noise: 1;" in light
    dark_values = effective_values(live.snapshot, "dark")
    assert f"--color-primary: {dark_values['--color-primary']};" in dark
    for name in ("--color-base-100", "--radius-field", "--size-selector", "--border", "--depth"):
        assert f"{name}:" in light, name
    assert "--font" not in css  # daisyUI theme blocks don't take fonts


def test_no_published_theme_is_404(client):
    assert client.get(URL).status_code == 404


@pytest.mark.skipif(
    not CLI, reason="the Tailwind CLI isn't downloaded (run the demo's tailwind build)"
)
def test_the_issue_check_tailwind_builds_it(client, live, tmp_path):
    block = client.get(URL).content.decode()
    # The demo uses daisyUI's standalone plugin files instead of the npm package,
    # so point the block at that file (a project using npm pastes it as it is).
    block = block.replace('@plugin "daisyui/theme"', f'@plugin "{PLUGINS / "daisyui-theme.mjs"}"')
    source = tmp_path / "source.css"
    source.write_text(
        '@import "tailwindcss" source(none);\n'
        '@source inline("btn btn-primary");\n'
        f'@plugin "{PLUGINS / "daisyui.mjs"}";\n' + block
    )
    output = tmp_path / "out.css"
    result = subprocess.run(  # noqa: S603
        [str(CLI[-1]), "--input", str(source), "--output", str(output)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    built = output.read_text()
    assert "main-light" in built and "main-dark" in built
    assert "oklch(65% 0.24 350)" in built
    assert "prefers-color-scheme: dark" in built
