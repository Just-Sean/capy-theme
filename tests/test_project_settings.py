"""One test per CAPY_THEME_* setting, and the README lists them all (issue #61)."""

import io
import re
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse
from PIL import Image

from capy_theme import conf
from capy_theme.artifacts.api import api_mode
from capy_theme.css.custom import custom_css_url
from capy_theme.fonts.uploads import prepare
from capy_theme.images.uploads import add_asset, byte_limit, prepare_image
from capy_theme.models import Theme
from capy_theme.portability.export import export_theme
from capy_theme.portability.importing import import_theme
from capy_theme.themes import active
from capy_theme.themes.catalogue import get_builtin_themes
from capy_theme.themes.publishing import publish
from tests.support.fonts import ttf_bytes

pytestmark = pytest.mark.django_db
README = (Path(__file__).resolve().parents[1] / "README.md").read_text()


@pytest.fixture(autouse=True)
def clear():
    cache.clear()
    yield
    cache.clear()


def test_the_issue_check_readme_lists_every_setting_with_its_default():
    rows = dict(re.findall(r"^\| `(CAPY_THEME_[A-Z_]+)` \| ([^|]+) \|", README, re.M))
    assert set(rows) == set(conf.DEFAULTS)
    for name, default in conf.DEFAULTS.items():
        shown = rows[name].strip()
        if isinstance(default, bool) or isinstance(default, str):
            assert repr(default).replace("'", '"') in shown, name
        elif isinstance(default, int):
            assert str(default) in shown, name


def test_every_setting_has_a_default_and_is_read_through_conf(settings):
    for name in conf.DEFAULTS:
        assert conf.get(name) == conf.DEFAULTS[name]
    settings.CAPY_THEME_CACHE_SECONDS = 7
    assert conf.get("CAPY_THEME_CACHE_SECONDS") == 7


def test_builtin_themes(settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]
    assert [t.name for t in get_builtin_themes()] == ["light", "dark"]


def test_cache_seconds(settings):
    settings.CAPY_THEME_CACHE_SECONDS = 42
    assert active.cache_seconds() == 42


def test_api(settings):
    settings.CAPY_THEME_API = "django"
    assert api_mode() == "django"


def test_visitor_themes(settings, rf):
    theme = Theme.objects.create(name="Ocean", slug="ocean", offered_to_visitors=True)
    publish(theme)
    request = rf.get("/")
    request.COOKIES[active.CHOICE_COOKIE] = "ocean"
    assert active.get_active_theme(request) == theme
    settings.CAPY_THEME_VISITOR_THEMES = False
    assert active.get_active_theme(request) is None


def test_custom_css(settings, client, django_user_model):
    theme = Theme.objects.create(
        name="Main", slug="main", settings={"custom_css": {"css": ".a{}", "enabled": True}}
    )
    revision = publish(theme)
    assert custom_css_url(revision)
    settings.CAPY_THEME_CUSTOM_CSS = False
    assert custom_css_url(revision) is None
    assert client.get(f"/theme/custom/{revision.css_version}.css").status_code == 404
    user = django_user_model.objects.create_superuser("s", "s@e.com", "pw")
    client.force_login(user)
    page = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content
    assert b'name="custom_css"' not in page  # even for a superuser


def test_editor_button(settings, rf, django_user_model):
    theme = Theme.objects.create(name="Main", slug="main")
    active.activate(publish(theme).theme)
    user = django_user_model.objects.create_user("e", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    request = rf.get("/")
    request.user = user
    head = Template("{% load capy_theme %}{% theme_head %}")
    assert 'data-floating-button="true"' in head.render(Context({"request": request}))
    settings.CAPY_THEME_EDITOR_BUTTON = False
    assert 'data-floating-button="false"' in head.render(Context({"request": request}))


def test_font_max_bytes(settings):
    settings.CAPY_THEME_FONT_MAX_BYTES = 100
    with pytest.raises(ValidationError, match="too big"):
        prepare(ttf_bytes(), "font.ttf")


def png(size=(200, 100)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, "PNG")
    return buffer.getvalue()


def test_image_max_bytes(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    theme = Theme.objects.create(name="Main", slug="main")
    data = png()
    assert byte_limit("logo_main") == 2 * 1024 * 1024  # the slot's own limit
    settings.CAPY_THEME_IMAGE_MAX_BYTES = len(data) - 1
    assert byte_limit("logo_main") == len(data) - 1
    with pytest.raises(ValidationError, match="too big"):
        add_asset(theme, "logo_main", "light", SimpleUploadedFile("a.png", data))
    settings.CAPY_THEME_IMAGE_MAX_BYTES = 50 * 1024 * 1024  # higher than the slot's
    assert byte_limit("logo_main") == 2 * 1024 * 1024


def test_import_max_bytes(settings):
    data = export_theme(Theme.objects.create(name="Main", slug="main"))
    settings.CAPY_THEME_IMPORT_MAX_BYTES = 10
    with pytest.raises(ValidationError, match="too big"):
        import_theme(io.BytesIO(data))


def animated_gif(frames, size=(10, 10)):
    images = [Image.new("RGB", size, (i * 40 % 256, 0, 0)) for i in range(frames)]
    buffer = io.BytesIO()
    images[0].save(buffer, "GIF", save_all=True, append_images=images[1:], duration=50)
    return buffer.getvalue()


def test_animation_max_frames(settings):
    data = animated_gif(4)
    assert prepare_image(data, "a.gif", "logo_main")
    settings.CAPY_THEME_ANIMATION_MAX_FRAMES = 3
    with pytest.raises(ValidationError, match="has 4 frames; animated images can have at most 3"):
        prepare_image(data, "a.gif", "logo_main")


def test_animation_max_pixels(settings):
    data = animated_gif(4)  # 4 frames of 10 × 10: 400 pixels in all
    settings.CAPY_THEME_ANIMATION_MAX_PIXELS = 400
    assert prepare_image(data, "a.gif", "logo_main")
    settings.CAPY_THEME_ANIMATION_MAX_PIXELS = 399
    with pytest.raises(ValidationError, match="too big: 4 frames of 10 × 10 pixels"):
        prepare_image(data, "a.gif", "logo_main")
