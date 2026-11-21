"""Font names and font fields can't inject script or CSS (#235).

A font's family name, fallback fonts and character range go into the admin's font
previews and every page's stylesheet, so they're limited to characters that can't
end a string, a CSS rule or a <style> block. The import tests started as the
pre-release QA review's bug-proof tests.
"""

import io
import json
import time
import zipfile
from pathlib import Path

import jsonschema
import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.urls import reverse

import capy_theme
from capy_theme.css.stylesheet import render_css
from capy_theme.fonts.css import font_css
from capy_theme.fonts.library import DEFAULT_FALLBACK, css_string, preview_faces
from capy_theme.fonts.models import Font, FontFile, fallback_validator
from capy_theme.fonts.uploads import prepare
from capy_theme.models import Theme
from capy_theme.portability.importing import import_theme
from capy_theme.themes.publishing import publish
from tests.support.fonts import ttf_bytes

pytestmark = pytest.mark.django_db

INJECTED = "} body { display: none } :root { --x: y"
SCRIPT = "</style><img src=x onerror=alert(1)>"
SCHEMA = json.loads(
    (Path(capy_theme.__file__).parent / "portability" / "theme_file.schema.json").read_text()
)
FALLBACK_SCHEMA_PATTERN = SCHEMA["properties"]["fonts"]["additionalProperties"]["properties"][
    "fallback_stack"
]["pattern"]


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield tmp_path
    cache.clear()


def zip_with(manifest, files=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("theme.json", json.dumps(manifest))
        for name, content in (files or {}).items():
            archive.writestr(name, content)
    buffer.seek(0)
    return buffer


def minimal(fonts=None, **theme):
    return {
        "format": "capy-theme-export/1",
        "theme": {
            "name": "T",
            "slug": "t",
            "base": "light",
            "settings": {},
        }
        | theme,
        "fonts": fonts or {},
        "images": {},
    }


def woff2():
    return prepare(ttf_bytes(), "x.ttf")["file"].read()


# The model: what the admin form and imports check


@pytest.mark.parametrize("family", [SCRIPT, 'Evil"Font', "Evil;Font", "", " Leading space"])
def test_a_family_name_with_unsafe_characters_is_refused(family):
    with pytest.raises(ValidationError) as error:
        Font(family=family, source="upload").full_clean()
    assert "family" in error.value.message_dict


@pytest.mark.parametrize("family", ["Inter", "Source Serif 4", "Josefin-Sans", "IBM Plex Mono"])
def test_real_family_names_are_accepted(family):
    Font(family=family, source="upload").full_clean()


@pytest.mark.parametrize(
    "stack",
    ["serif; " + INJECTED, "serif}", "a, b) url(x", "a < b", "x\\", "a,", "a,,b"],
)
def test_a_fallback_stack_with_unsafe_characters_is_refused(stack):
    with pytest.raises(ValidationError) as error:
        Font(family="Sneaky", source="system", fallback_stack=stack).full_clean()
    assert "fallback_stack" in error.value.message_dict


@pytest.mark.parametrize(
    "stack",
    [
        "ui-sans-serif, system-ui, sans-serif",
        'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace',
        "'Segoe UI', sans-serif",
        "",
    ],
)
def test_real_fallback_stacks_are_accepted(stack):
    Font(family="Fine", source="system", fallback_stack=stack).full_clean()


@pytest.mark.parametrize("value", ["U+0000-00FF; " + INJECTED, "U+0041}", "latin", "U+00GG"])
def test_a_unicode_range_with_unsafe_characters_is_refused(value):
    font = Font.objects.create(family="Fine", source="upload")
    font_file = FontFile(font=font, unicode_range=value, file=ContentFile(b"x", name="f.woff2"))
    with pytest.raises(ValidationError) as error:
        font_file.full_clean()
    assert "unicode_range" in error.value.message_dict


@pytest.mark.parametrize("value", ["U+0000-00FF, U+0131, U+0152-0153", "U+4??", ""])
def test_real_unicode_ranges_are_accepted(value):
    font = Font.objects.create(family="Fine", source="upload")
    FontFile(font=font, unicode_range=value, file=ContentFile(b"x", name="f.woff2")).full_clean()


def test_font_admin_fallback_stack_cant_add_css_rules(settings):
    """A user who can add fonts but not custom CSS (QA review)."""
    settings.CAPY_THEME_CUSTOM_CSS = False
    font = Font(family="Sneaky", source="system", fallback_stack="serif; " + INJECTED)
    with pytest.raises(ValidationError):
        font.full_clean()


# The admin's font previews


def test_the_admin_font_list_escapes_an_unsafe_family_name(client, django_user_model):
    """Saved before this check (or by code that skips it): still no script in the admin."""
    font = Font.objects.create(family=SCRIPT, source="upload")
    FontFile.objects.create(font=font, file=ContentFile(woff2(), name="f.woff2"))
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    html = client.get(reverse("admin:capy_theme_font_changelist")).content.decode()
    assert "<img src=x" not in html
    assert "</style><img" not in html


def test_preview_faces_escapes_every_value():
    font = Font.objects.create(family=SCRIPT, source="upload")
    FontFile.objects.create(font=font, file=ContentFile(woff2(), name="f.woff2"))
    css = preview_faces(font)
    assert "<" not in css and ">" not in css
    assert css.count('"') == 6  # only the quotes around the family, the URL and "woff2"


def test_css_string_keeps_ordinary_text_and_escapes_the_rest():
    assert css_string("Source Serif 4") == '"Source Serif 4"'
    assert css_string("https://x.test/a.woff2?v=1&s=2") == '"https://x.test/a.woff2?v=1&s=2"'
    assert css_string('a"<') == '"a\\22 \\3c "'


# Imports


def test_imported_font_fallback_stack_cant_add_css_rules(settings):
    settings.CAPY_THEME_CUSTOM_CSS = False
    fonts = {
        "font-1": {
            "family": "Evil System",
            "source": "system",
            "fallback_stack": "serif; " + INJECTED,
            "files": [],
        }
    }
    with pytest.raises(ValidationError, match="theme.json isn't a capy-theme export"):
        import_theme(zip_with(minimal(fonts=fonts, font_roles={"body": "font-1"})))
    assert not Theme.objects.exists()


def test_imported_font_unicode_range_cant_add_css_rules(settings):
    settings.CAPY_THEME_CUSTOM_CSS = False
    fonts = {
        "font-1": {
            "family": "Evil Upload",
            "source": "upload",
            "files": [
                {
                    "path": "fonts/1-0.woff2",
                    "weight": 400,
                    "style": "normal",
                    "unicode_range": "U+0000-00FF; " + INJECTED,
                }
            ],
        }
    }
    manifest = minimal(fonts=fonts, font_roles={"body": "font-1"})
    with pytest.raises(ValidationError, match="theme.json isn't a capy-theme export"):
        import_theme(zip_with(manifest, {"fonts/1-0.woff2": woff2()}))
    assert not Theme.objects.exists()


def test_imported_font_family_with_script_is_refused():
    fonts = {"font-1": {"family": SCRIPT, "source": "system", "files": []}}
    with pytest.raises(ValidationError, match="theme.json isn't a capy-theme export"):
        import_theme(zip_with(minimal(fonts=fonts)))


def test_an_imported_font_with_safe_values_still_works():
    fonts = {
        "font-1": {
            "family": "Good Upload",
            "source": "upload",
            "fallback_stack": '"Segoe UI", sans-serif',
            "files": [
                {
                    "path": "fonts/1-0.woff2",
                    "weight": 400,
                    "style": "normal",
                    "unicode_range": "U+0000-00FF, U+0131",
                }
            ],
        }
    }
    manifest = minimal(fonts=fonts, font_roles={"body": "font-1"})
    theme = import_theme(zip_with(manifest, {"fonts/1-0.woff2": woff2()}))
    css = render_css(publish(theme))
    assert '"Good Upload", "Segoe UI", sans-serif' in css
    assert "unicode-range: U+0000-00FF, U+0131;" in css


EXTERNAL = {
    "font-1": {
        "family": "Far Away",
        "source": "external",
        "stylesheet_url": "https://fonts.example/far-away.css",
        "files": [],
    }
}


def test_an_import_adding_an_external_font_needs_permission_to_add_fonts():
    with pytest.raises(ValidationError, match="needs permission to add fonts"):
        import_theme(zip_with(minimal(fonts=EXTERNAL)), can_add_external_fonts=False)
    assert not Theme.objects.exists()
    assert not Font.objects.filter(family="Far Away").exists()


def test_an_import_reusing_an_external_font_already_in_the_library_is_fine():
    Font.objects.create(
        family="Far Away", source="external", stylesheet_url="https://fonts.example/far.css"
    )
    theme = import_theme(zip_with(minimal(fonts=EXTERNAL)), can_add_external_fonts=False)
    assert theme.pk


def test_an_import_with_permission_may_add_an_external_font():
    import_theme(zip_with(minimal(fonts=EXTERNAL)))
    assert Font.objects.get(family="Far Away").source == "external"


def staff(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("s", password="pw", is_staff=True)
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    client.force_login(user)


@pytest.mark.parametrize(("codenames", "added"), [((), False), (("add_font",), True)])
def test_the_admin_import_passes_the_add_font_permission(
    client, django_user_model, codenames, added
):
    staff(client, django_user_model, "view_theme", "change_theme", "import_theme", *codenames)
    upload = zip_with(minimal(fonts=EXTERNAL))
    upload.name = "t.capy-theme.zip"
    response = client.post("/admin/capy_theme/theme/import/", {"file": upload})
    assert Font.objects.filter(family="Far Away").exists() is added
    if not added:
        assert "needs permission to add fonts" in response.content.decode()


# Regular expressions that can't be made slow (final review)


@pytest.mark.parametrize(
    "attack",
    ["a" + " " * 40_000 + "!", "a  ," * 75 + "!", '"a  b" ,' * 40 + "!", "a " * 50_000 + "!"],
)
def test_the_fallback_check_stays_fast_on_crafted_input(attack):
    """A pattern with two places for one space took exponential time (a regex DoS)."""
    started = time.monotonic()
    with pytest.raises(ValidationError):
        fallback_validator(attack)
    jsonschema.Draft7Validator({"pattern": FALLBACK_SCHEMA_PATTERN}).is_valid(attack)
    assert time.monotonic() - started < 0.5


# Values saved before they were checked still can't reach page CSS (final review)


def test_a_revision_with_unsafe_old_font_values_gives_safe_css():
    fonts = {
        "body": {
            "family": SCRIPT,
            "source": "upload",
            "fallback": "serif; " + INJECTED,
            "files": [
                {
                    "url": '/m/f.woff2") ' + INJECTED,
                    "weight": 400,
                    "style": "normal; x",
                    "unicode_range": "U+0000; " + INJECTED,
                },
            ],
        }
    }
    css = "\n".join(font_css(fonts))
    assert INJECTED not in css and "</style>" not in css  # only escaped copies remain
    assert "--font-sans: " in css and DEFAULT_FALLBACK["body"] in css
    assert "unicode-range" not in css
    assert "font-style: normal;" in css
