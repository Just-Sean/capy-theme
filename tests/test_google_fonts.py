"""Tests for importing Google Fonts (issue #27). No network: downloads are faked."""

import io
import urllib.error
import urllib.parse

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from fontTools.ttLib import TTFont

from capy_theme.google_fonts import css_url, fetch, import_family, parse
from capy_theme.models import Font, Theme
from capy_theme.publishing import publish
from capy_theme.stylesheet import render_css
from tests.support.fonts import ttf_bytes

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def woff2():
    font = TTFont(io.BytesIO(ttf_bytes()))
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def face(subset, style, weight, name):
    return f"""/* {subset} */
@font-face {{
  font-family: 'Lora';
  font-style: {style};
  font-weight: {weight};
  font-display: swap;
  src: url(https://fonts.gstatic.com/s/lora/v37/{name}.woff2) format('woff2');
  unicode-range: U+0000-00FF;
}}
"""


class FakeGoogle:
    """Answers like the Google Fonts API for a family with 400, 700 and 400 italic."""

    def __init__(self, family="Lora", have=((0, 400), (0, 700), (1, 400))):
        self.family, self.have, self.requests = family, set(have), []

    def __call__(self, url, timeout=60):
        self.requests.append(url)
        if url.startswith("https://fonts.gstatic.com/"):
            return woff2()
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["family"][0]
        name, _, axes = query.partition(":ital,wght@")
        combos = {tuple(int(x) for x in c.split(",")) for c in axes.split(";")}
        if name != self.family or not combos <= self.have:
            raise urllib.error.HTTPError(url, 400, "Bad Request", {}, None)
        css = ""
        for italic, weight in sorted(combos):
            style = "italic" if italic else "normal"
            css += face("latin", style, weight, f"lat-{style}")  # variable: one file per style
            css += face("cyrillic", style, weight, f"cyr-{style}")
        return css.encode()


def test_parse_reads_each_face():
    faces = parse(face("latin", "italic", 400, "abc"))
    assert faces == [
        {
            "subset": "latin",
            "style": "italic",
            "weight": 400,
            "url": "https://fonts.gstatic.com/s/lora/v37/abc.woff2",
            "unicode_range": "U+0000-00FF",
        }
    ]


def test_css_url():
    url = css_url("Open Sans", [(1, 400), (0, 700)])
    assert url.startswith(
        "https://fonts.googleapis.com/css2?family=Open+Sans%3Aital%2Cwght%400%2C700%3B1%2C400"
    )


def test_import_stores_the_files_locally():
    google = FakeGoogle()
    font = import_family("Lora", download=google)
    assert font.source == "google"
    assert "fonts.google.com/specimen/Lora" in font.licence
    files = list(font.files.all())
    assert {(f.weight, f.style, f.subset) for f in files} == {
        (400, "normal", "latin"),
        (700, "normal", "latin"),
        (400, "italic", "latin"),
    }
    assert all(f.file.read()[:4] == b"wOF2" for f in files)
    # Each file downloaded once (variable fonts share one file between weights).
    downloads = [u for u in google.requests if "gstatic" in u]
    assert len(downloads) == len(set(downloads)) == 2


def test_pages_load_the_font_from_this_site_never_from_google():
    font = import_family("Lora", download=FakeGoogle())
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"body": font.pk}})
    css = render_css(publish(theme))
    assert '"Lora"' in css
    assert "/media/capy_theme/fonts/" in css
    assert "googleapis" not in css and "gstatic" not in css


def test_missing_weights_are_skipped():
    google = FakeGoogle(have=((0, 400),))
    font = import_family("Lora", weights=(400, 700), italic=True, download=google)
    assert {(f.weight, f.style) for f in font.files.all()} == {(400, "normal")}


def test_chosen_subsets_only():
    font = import_family("Lora", subsets=("latin", "cyrillic"), download=FakeGoogle())
    assert {f.subset for f in font.files.all()} == {"latin", "cyrillic"}


def test_unknown_family_is_reported():
    with pytest.raises(ValidationError, match="Google Fonts has no “Nope Sans”"):
        import_family("Nope Sans", download=FakeGoogle())
    assert not Font.objects.filter(family="Nope Sans").exists()


def test_bad_names_and_duplicates_are_refused():
    with pytest.raises(ValidationError, match="family name"):
        import_family("../etc/passwd", download=FakeGoogle())
    import_family("Lora", download=FakeGoogle())
    with pytest.raises(ValidationError, match="already in the font library"):
        import_family("lora", download=FakeGoogle())


def test_only_google_addresses_are_downloaded():
    with pytest.raises(ValueError, match="only Google Fonts"):
        fetch("file:///etc/passwd")
    with pytest.raises(ValueError, match="only Google Fonts"):
        fetch("https://example.com/font.woff2")


def test_admin_import_page(client, django_user_model, monkeypatch):
    monkeypatch.setattr("capy_theme.google_fonts.fetch", FakeGoogle())
    monkeypatch.setattr(
        "capy_theme.admin.import_family",
        lambda family, **kw: import_family(family, download=FakeGoogle(), **kw),
    )
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    changelist = client.get(reverse("admin:capy_theme_font_changelist")).content.decode()
    assert reverse("admin:capy_theme_font_import_google") in changelist
    url = reverse("admin:capy_theme_font_import_google")
    assert client.get(url).status_code == 200
    response = client.post(
        url, {"family": "Lora", "weights": ["400", "700"], "italic": "on", "subsets": ["latin"]}
    )
    font = Font.objects.get(family="Lora")
    assert response.url == reverse("admin:capy_theme_font_change", args=[font.pk])
    assert font.files.count() == 3


def test_admin_import_shows_errors(client, django_user_model, monkeypatch):
    monkeypatch.setattr(
        "capy_theme.admin.import_family",
        lambda family, **kw: import_family(family, download=FakeGoogle(), **kw),
    )
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    response = client.post(
        reverse("admin:capy_theme_font_import_google"),
        {"family": "Nope Sans", "weights": ["400"], "subsets": ["latin"]},
    )
    assert response.status_code == 200
    assert "Google Fonts has no" in response.content.decode()


def test_every_weight_gets_a_rule_even_when_files_are_shared():
    # Variable fonts use one file for several weights; each weight needs its own
    # @font-face, or browsers fake the bold.
    font = import_family("Lora", download=FakeGoogle())
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"body": font.pk}})
    css = render_css(publish(theme))
    assert css.count("@font-face") == 3
    assert "font-weight: 700;" in css
