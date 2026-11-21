"""Tests for the visitor theme picker (issue #47)."""

import pytest
from django.core.cache import cache
from django.template import Context, Template
from django.urls import reverse

from capy_theme.admin.theme_form import ThemeForm
from capy_theme.models import Theme
from capy_theme.themes.active import CHOICE_COOKIE, activate, get_active_theme, picker_state
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear():
    cache.clear()
    yield
    cache.clear()


def published(name, offered=False, **fields):
    theme = Theme.objects.create(
        name=name, slug=name.lower(), offered_to_visitors=offered, **fields
    )
    publish(theme)
    return theme


@pytest.fixture
def themes():
    site = published("Site")
    activate(site)
    return {
        "site": site,
        "ocean": published("Ocean", offered=True, light_base="cupcake"),
        "forest": published("Forest", offered=True, light_base="emerald"),
        "secret": published("Secret"),  # not offered
    }


def request_with(rf, choice=None):
    request = rf.get("/")
    if choice is not None:
        request.COOKIES[CHOICE_COOKIE] = choice
    return request


def test_the_issue_check_switch_between_two_allowed_themes(themes, client):
    assert client.get(reverse("capy_theme:choose_theme", args=["ocean"])).status_code == 302
    assert client.cookies[CHOICE_COOKIE].value == "ocean"
    request = request_with_cookie(client)
    assert get_active_theme(request) == themes["ocean"]
    client.get(reverse("capy_theme:choose_theme", args=["forest"]))
    assert get_active_theme(request_with_cookie(client)) == themes["forest"]


def request_with_cookie(client):
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.COOKIES[CHOICE_COOKIE] = client.cookies[CHOICE_COOKIE].value
    return request


def test_the_issue_check_a_theme_not_on_the_list_cant_be_forced(themes, rf, client):
    # Through the view: nothing is stored.
    client.get(reverse("capy_theme:choose_theme", args=["secret"]))
    assert CHOICE_COOKIE not in client.cookies
    # And a hand-made cookie is ignored.
    assert get_active_theme(request_with(rf, "secret")) == themes["site"]
    assert get_active_theme(request_with(rf, "nonsense")) == themes["site"]


def test_unpublished_themes_arent_offered(themes, rf):
    Theme.objects.create(name="Draft", slug="draft", offered_to_visitors=True)
    assert get_active_theme(request_with(rf, "draft")) == themes["site"]


def test_default_clears_the_choice(themes, client):
    client.get(reverse("capy_theme:choose_theme", args=["ocean"]))
    response = client.get(reverse("capy_theme:choose_theme", args=["default"]) + "?next=/x/")
    assert response["Location"] == "/x/"
    assert client.cookies[CHOICE_COOKIE].value == ""


def test_next_must_be_this_site(themes, client):
    url = reverse("capy_theme:choose_theme", args=["ocean"]) + "?next=https://evil.example/"
    assert client.get(url)["Location"] == "/"


def test_without_a_request_its_the_site_theme(themes):
    assert get_active_theme() == themes["site"]


def test_project_can_turn_visitor_themes_off(themes, rf, settings, client):
    settings.CAPY_THEME_VISITOR_THEMES = False
    assert get_active_theme(request_with(rf, "ocean")) == themes["site"]
    client.get(reverse("capy_theme:choose_theme", args=["ocean"]))
    assert CHOICE_COOKIE not in client.cookies
    assert render(rf) == ""


def render(rf, choice=None):
    return Template("{% load capy_theme %}{% theme_picker %}").render(
        Context({"request": request_with(rf, choice)})
    )


def test_picker_lists_site_default_and_offered_themes(themes, rf):
    html = render(rf, "forest")
    assert html.count("<li>") == 3
    assert ">Site default</a>" in html
    assert 'data-capy-theme-choice="forest" class="menu-active" aria-current="true"' in html
    assert ">Ocean</a>" in html and ">Secret</a>" not in html
    assert "/theme/choose/ocean/?next=/" in html


def test_picker_is_empty_without_offered_themes(rf):
    activate(published("Only"))
    assert render(rf) == ""


def test_whole_page_uses_the_chosen_theme(themes, rf):
    from capy_theme.css.stylesheet import stylesheet_url

    html = Template("{% load capy_theme %}{% theme_head %}").render(
        Context({"request": request_with(rf, "ocean")})
    )
    assert stylesheet_url(themes["ocean"].live_revision) in html


def test_offering_a_theme_clears_the_cache(themes, rf):
    assert get_active_theme(request_with(rf, "secret")) == themes["site"]
    secret = themes["secret"]
    secret.offered_to_visitors = True
    secret.save()
    assert get_active_theme(request_with(rf, "secret")) == secret


def test_admin_field():
    form = ThemeForm(
        data={
            "name": "A",
            "slug": "a",
            "light_base": "light",
            "dark_base": "dark",
            "visitors_can_switch": "on",
            "offered_to_visitors": "on",
        }
    )
    assert form.is_valid(), form.errors
    theme = form.save()
    assert theme.offered_to_visitors


def test_offering_isnt_an_unpublished_change(themes):
    secret = themes["secret"]
    secret.offered_to_visitors = True
    secret.save()
    assert not secret.has_unpublished_changes


@pytest.mark.parametrize("secure", [True, False])
def test_the_choice_cookie_is_secure_on_https(themes, client, secure):
    # #253
    response = client.get(reverse("capy_theme:choose_theme", args=["ocean"]), secure=secure)
    assert bool(response.cookies[CHOICE_COOKIE]["secure"]) is secure


# --- The picker-state data interface (theme_picker_state) -----------------------------


def test_picker_state_lists_default_then_offered_with_urls(themes, rf):
    state = picker_state(request_with(rf, "ocean"))
    assert state["allowed"] is True
    assert state["current"] == "ocean"
    # "Site default" first, then the offered themes by name (Forest, Ocean); "Secret" isn't offered.
    assert [o["value"] for o in state["options"]] == ["default", "forest", "ocean"]
    ocean = next(o for o in state["options"] if o["value"] == "ocean")
    assert ocean["current"] is True and ocean["label"] == "Ocean"
    assert ocean["url"] == reverse("capy_theme:choose_theme", args=["ocean"]) + "?next=%2F"


def test_picker_state_falls_back_to_default_for_an_unknown_choice(themes, rf):
    state = picker_state(request_with(rf, "nonsense"))
    assert state["current"] == "default"
    assert next(o for o in state["options"] if o["value"] == "default")["current"] is True


def test_picker_state_when_visitor_themes_are_off(themes, rf, settings):
    settings.CAPY_THEME_VISITOR_THEMES = False
    state = picker_state(request_with(rf, "ocean"))
    assert state["allowed"] is False
    assert [o["value"] for o in state["options"]] == ["default"]


def test_picker_state_tag_is_none_without_an_active_theme(rf):
    assert (
        Template("{% load capy_theme %}{% theme_picker_state as p %}[{{ p }}]")
        .render(Context({"request": request_with(rf)}))
        .strip()
        == "[None]"
    )


def test_picker_state_tag_exposes_offered_themes(themes, rf):
    out = Template(
        "{% load capy_theme %}{% theme_picker_state as p %}"
        "{% for o in p.options %}{{ o.label }},{% endfor %}"
    ).render(Context({"request": request_with(rf, "ocean")}))
    assert "Site default," in out and "Ocean," in out and "Secret," not in out


def test_picker_state_without_a_request_falls_back_to_the_home_page(themes):
    state = picker_state(None)
    assert state["current"] == "default"
    assert state["options"][0]["url"].endswith("?next=%2F")
