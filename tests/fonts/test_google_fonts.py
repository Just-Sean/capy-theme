"""Tests for importing Google Fonts (issue #27). No network: downloads are faked."""

import urllib.error
import urllib.parse

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from capy_theme.css.stylesheet import render_css
from capy_theme.fonts.google import (
    USER_AGENT,
    available_faces,
    css_url,
    fetch,
    import_family,
    parse,
)
from capy_theme.fonts.models import Font
from capy_theme.models import Theme
from capy_theme.themes.publishing import publish
from tests.support.google import FakeGoogle, face

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


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
    assert "fonts.google.com/specimen/Lora" in font.license
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
    monkeypatch.setattr("capy_theme.fonts.google.fetch", FakeGoogle())
    monkeypatch.setattr(
        "capy_theme.admin.fonts.import_family",
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
        "capy_theme.admin.fonts.import_family",
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


# The checks around downloading (issue #181).


def test_fetch_sends_a_browser_user_agent_and_a_timeout(monkeypatch):
    seen = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"css"

    def fake_urlopen(request, timeout):
        seen.append((request.full_url, request.get_header("User-agent"), timeout))
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    url = "https://fonts.googleapis.com/css2?family=Lora"
    assert fetch(url) == b"css"
    assert len(seen) == 1  # the fake was used, so nothing went to the network
    sent_url, agent, timeout = seen[0]
    assert sent_url == url
    assert agent == USER_AGENT  # asks for WOFF2, like a browser
    assert timeout and timeout > 0  # never waits forever


@pytest.mark.parametrize(
    "url",
    [
        "https://fonts.googleapis.com.evil.example/css2",
        "https://fonts.gstatic.com.evil.example/x.woff2",
        "https://fonts.gstatic.com@evil.example/x.woff2",
        "http://fonts.gstatic.com/x.woff2",
    ],
)
def test_lookalike_addresses_are_never_downloaded(url):
    with pytest.raises(ValueError, match="only Google Fonts"):
        fetch(url)


@pytest.mark.parametrize(
    "elsewhere",
    [
        "https://evil.example/",
        "https://fonts.gstatic.com.evil.example/",
        "https://fonts.gstatic.com@evil.example/",
    ],
)
def test_file_addresses_not_on_fonts_gstatic_are_refused(elsewhere):
    # If the API ever answered with a file somewhere else (including addresses that
    # only look like Google's), nothing is downloaded or kept.
    class Elsewhere(FakeGoogle):
        def __call__(self, url, timeout=60):
            css = super().__call__(url, timeout)
            return css.replace(b"https://fonts.gstatic.com/", elsewhere.encode())

    fake = Elsewhere()
    with pytest.raises(ValidationError, match="unexpected file address"):
        import_family("Lora", weights=(400,), italic=False, download=fake)
    assert not any(url.startswith(elsewhere) for url in fake.requests)
    assert not Font.objects.filter(family="Lora").exists()


def test_faces_without_an_https_address_are_skipped():
    css = face("latin", "normal", 400, "ok") + face("latin", "normal", 700, "plain").replace(
        "https://", "http://"
    )
    assert [f["weight"] for f in parse(css)] == [400]


@pytest.mark.parametrize(
    "problem", [urllib.error.URLError("no route to host"), TimeoutError("timed out")]
)
def test_google_unreachable_is_a_clear_error(problem):
    def unreachable(url, timeout=60):
        raise problem

    with pytest.raises(ValidationError, match="couldn't be reached"):
        import_family("Lora", download=unreachable)
    assert not Font.objects.filter(family="Lora").exists()


def test_a_server_error_isnt_mistaken_for_a_missing_weight():
    # A 400 means "that weight doesn't exist" and is retried per weight; anything
    # else (here a 503) is a real failure and is raised.
    def down(url, timeout=60):
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, None)

    with pytest.raises(urllib.error.HTTPError):
        available_faces("Lora", [(0, 400)], download=down)


def test_a_server_error_while_retrying_each_weight_is_raised():
    calls = []

    def down_after_first(url, timeout=60):
        calls.append(url)
        code = 400 if len(calls) == 1 else 503
        raise urllib.error.HTTPError(url, code, "error", {}, None)

    with pytest.raises(urllib.error.HTTPError) as raised:
        available_faces("Lora", [(0, 400), (0, 700)], download=down_after_first)
    assert raised.value.code == 503


def test_a_server_error_tells_the_user_google_couldnt_be_reached():
    def down(url, timeout=60):
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", {}, None)

    with pytest.raises(ValidationError, match="couldn't be reached"):
        import_family("Lora", download=down)
    assert not Font.objects.filter(family="Lora").exists()
