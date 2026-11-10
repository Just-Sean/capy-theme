"""Tests for the social sharing image and link-preview tags (issue #37)."""

import io
from html.parser import HTMLParser

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse
from PIL import Image

from capy_theme.active import activate
from capy_theme.admin import ThemeForm
from capy_theme.images import add_asset
from capy_theme.models import Theme
from capy_theme.publishing import publish
from capy_theme.social import sharing_image

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def picture(size=(1600, 1600), fmt="JPEG", mode="RGB", colour="red"):
    buffer = io.BytesIO()
    Image.new(mode, size, colour).save(buffer, fmt)
    return SimpleUploadedFile(f"share.{fmt.lower()}", buffer.getvalue())


def live(settings_values=None, image=None, alt=""):
    theme = Theme.objects.create(name="T", slug="t", settings=settings_values or {})
    if image is not None:
        asset = add_asset(theme, "social", "light", image, alt)
        theme.settings = {**theme.settings, "images": {"social": {"light": asset.pk}}}
        theme.save()
    revision = publish(theme)
    activate(theme)
    return revision


class Meta(HTMLParser):
    """Collects <meta property/name=... content=...> like a link-preview checker."""

    def __init__(self):
        super().__init__()
        self.tags = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and (attrs.get("property") or attrs.get("name")):
            self.tags[attrs.get("property") or attrs.get("name")] = attrs["content"]


def meta(html):
    parser = Meta()
    parser.feed(html)
    return parser.tags


def head(rf, source="{% theme_head %}", path="/about/"):
    return Template("{% load capy_theme %}" + source).render(Context({"request": rf.get(path)}))


# The image


def test_sharing_image_is_cropped_to_1200_by_630():
    revision = live(image=picture((1600, 1600)))
    image = sharing_image(revision.snapshot)
    assert (image["width"], image["height"]) == (1200, 630)
    with default_storage.open(image["file"], "rb") as f:
        stored = Image.open(f)
        assert stored.size == (1200, 630)
        assert stored.format == "JPEG"


def test_transparent_parts_become_white():
    revision = live(image=picture((1300, 700), "PNG", "RGBA", (0, 0, 0, 0)))
    with default_storage.open(sharing_image(revision.snapshot)["file"], "rb") as f:
        stored = Image.open(f)
        assert stored.format == "PNG"
        assert stored.convert("RGB").getpixel((600, 315)) == (255, 255, 255)


def test_svg_isnt_accepted_for_sharing():
    theme = Theme.objects.create(name="T", slug="t")
    svg = SimpleUploadedFile("s.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>')
    with pytest.raises(ValidationError, match="Upload a PNG or JPEG"):
        add_asset(theme, "social", "light", svg)


# The tags


def test_the_issue_check_preview_has_image_title_and_description(rf):
    revision = live(
        {"site_name": "Capy Coffee", "tagline": "Good coffee"},
        image=picture(),
        alt="A cup of coffee",
    )
    tags = meta(head(rf))
    image_url = "http://testserver" + default_storage.url(sharing_image(revision.snapshot)["file"])
    assert tags["og:title"] == tags["twitter:title"] == "Capy Coffee"
    assert tags["og:description"] == tags["twitter:description"] == "Good coffee"
    assert tags["og:image"] == tags["twitter:image"] == image_url
    assert (tags["og:image:width"], tags["og:image:height"]) == ("1200", "630")
    assert tags["og:image:alt"] == tags["twitter:image:alt"] == "A cup of coffee"
    assert tags["og:url"] == "http://testserver/about/"
    assert tags["og:site_name"] == "Capy Coffee"
    assert tags["og:type"] == "website"
    assert tags["twitter:card"] == "summary_large_image"


def test_sharing_description_wins_over_the_tagline(rf):
    live({"tagline": "Tag", "social": {"description": "Shared"}})
    assert meta(head(rf))["og:description"] == "Shared"


def test_without_an_image_its_a_small_card(rf):
    live({"site_name": "Capy"})
    tags = meta(head(rf))
    assert tags["twitter:card"] == "summary"
    assert "og:image" not in tags


def test_pages_can_override_with_a_block(rf):
    live({"site_name": "Capy", "tagline": "Default"}, image=picture())
    base = Template(
        "{% load capy_theme %}{% theme_head social=False %}"
        "{% block social %}{% theme_social_tags %}{% endblock %}"
    )
    from django.template import engines

    engine = engines["django"].engine
    page = engine.from_string(
        "{% extends base %}{% load capy_theme %}{% block social %}"
        '{% theme_social_tags title="About us" description="Who we are" '
        'image="/static/about.png" image_alt="Our team" %}{% endblock %}'
    )
    request = rf.get("/about/")
    tags = meta(page.render(Context({"base": base, "request": request})))
    assert tags["og:title"] == "About us"
    assert tags["og:description"] == "Who we are"
    assert tags["og:image"] == "http://testserver/static/about.png"
    assert tags["og:image:alt"] == "Our team"
    assert "og:image:width" not in tags  # unknown for a page's own image
    # And theme_head itself output none, so nothing is doubled.
    assert head(rf, "{% theme_head social=False %}").count("og:title") == 0


def test_tags_are_escaped(rf):
    live({"site_name": 'Capy "&" <Co>'})
    html = head(rf)
    assert 'content="Capy &quot;&amp;&quot; &lt;Co&gt;"' in html


# Controls


def test_admin_link_preview_fields():
    theme = Theme.objects.create(name="T", slug="t")
    asset = add_asset(theme, "social", "light", picture())
    data = {
        "name": "T",
        "slug": "t",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
        "image_social_light": str(asset.pk),
        "social_description": " Hello ",
    }
    form = ThemeForm(data=data, instance=theme)
    assert "image_social_dark" not in form.fields
    assert form.is_valid(), form.errors
    assert form.save().settings == {
        "images": {"social": {"light": asset.pk}},
        "social": {"description": "Hello"},
    }


def test_editor_link_preview_controls(client, django_user_model):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    theme = Theme.objects.create(name="T", slug="t")
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    slots = {s["name"]: s["modes"] for s in state["controls"]["logo_slots"]}
    assert slots["social"] == ["light"]
    assert [s["name"] for s in state["controls"]["social_settings"]] == ["description"]
    url = reverse("capy_theme:editor_save", args=[theme.pk])
    changes = {"settings": {"social": {"description": "Shared"}}}
    assert client.post(url, changes, content_type="application/json").status_code == 200
    theme.refresh_from_db()
    assert theme.settings["social"] == {"description": "Shared"}
