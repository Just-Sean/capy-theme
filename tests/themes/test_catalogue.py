"""Tests for the built-in daisyUI theme catalogue (issue #4)."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from capy_theme.themes.catalogue import DAISYUI_VERSION, get_builtin_themes
from scripts.generate_builtin_themes import build_themes, parse_js_export

# The 28 values every daisyUI 5 theme defines.
EXPECTED_VALUES = {
    "--color-base-100",
    "--color-base-200",
    "--color-base-300",
    "--color-base-content",
    "--color-primary",
    "--color-primary-content",
    "--color-secondary",
    "--color-secondary-content",
    "--color-accent",
    "--color-accent-content",
    "--color-neutral",
    "--color-neutral-content",
    "--color-info",
    "--color-info-content",
    "--color-success",
    "--color-success-content",
    "--color-warning",
    "--color-warning-content",
    "--color-error",
    "--color-error-content",
    "--radius-selector",
    "--radius-field",
    "--radius-box",
    "--size-selector",
    "--size-field",
    "--border",
    "--depth",
    "--noise",
}


def test_catalogue_has_35_themes_each_with_all_28_values():
    themes = get_builtin_themes()
    assert len(themes) == 35
    assert len(EXPECTED_VALUES) == 28
    for theme in themes:
        assert set(theme.values) == EXPECTED_VALUES, theme.name
        assert all(theme.values.values()), theme.name


def test_each_theme_is_light_or_dark():
    themes = {theme.name: theme for theme in get_builtin_themes()}
    assert {theme.scheme for theme in themes.values()} == {"light", "dark"}
    assert not themes["light"].is_dark
    assert themes["dark"].is_dark
    assert themes["synthwave"].is_dark


def test_themes_are_in_daisyui_order():
    names = [theme.name for theme in get_builtin_themes()]
    assert names[:3] == ["light", "dark", "cupcake"]


def test_catalogue_records_its_daisyui_version():
    assert DAISYUI_VERSION.startswith("5.")


def test_themes_cannot_be_changed_through_the_catalogue():
    theme = get_builtin_themes()[0]
    with pytest.raises(TypeError):
        theme.values["--color-primary"] = "red"


def test_setting_limits_the_list(settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]
    assert [theme.name for theme in get_builtin_themes()] == ["light", "dark"]


def test_setting_keeps_daisyui_order(settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["synthwave", "light"]
    assert [theme.name for theme in get_builtin_themes()] == ["light", "synthwave"]


def test_unknown_theme_in_setting_raises(settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "lite"]
    with pytest.raises(ImproperlyConfigured, match="lite"):
        get_builtin_themes()


def test_empty_setting_offers_no_themes(settings):
    settings.CAPY_THEME_BUILTIN_THEMES = []
    assert get_builtin_themes() == []


# The generator script's parsing, tested without downloading anything.


def test_parse_js_export_reads_objects_and_arrays_with_trailing_commas():
    assert parse_js_export('export default {"a":{"b":"c"}};') == {"a": {"b": "c"}}
    assert parse_js_export('export default [\n  "light",\n  "dark",\n];\n') == ["light", "dark"]


def test_build_themes_splits_scheme_from_values_in_order():
    themes = {
        "dark": {"color-scheme": "dark", "--border": "1px"},
        "light": {"color-scheme": "light", "--border": "2px"},
    }
    result = build_themes(themes, ["light", "dark"])
    assert list(result) == ["light", "dark"]
    assert result["light"] == {"scheme": "light", "values": {"--border": "2px"}}


def test_build_themes_rejects_mismatched_order():
    with pytest.raises(ValueError, match="different themes"):
        build_themes({"light": {"color-scheme": "light"}}, ["light", "dark"])
