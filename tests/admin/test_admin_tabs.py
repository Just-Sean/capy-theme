"""Tests for the tabs on the theme edit page."""

import re
from types import SimpleNamespace

import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse

from capy_theme.admin.fieldsets import THEME_FIELDSETS
from capy_theme.admin.tabs import LEFTOVER_TAB, STAY_FOLDED, THEME_TABS, theme_tabs
from capy_theme.admin.theme_admin import ThemeAdmin
from capy_theme.models import Theme

pytestmark = pytest.mark.django_db

TAB_LABELS = [label for label, _ in THEME_TABS]
PANEL = (
    r'<div class="capy-tab-panel" data-capy-tab="([^"]+)" '
    r'data-capy-tab-order="(\d+)" data-capy-tab-label="([^"]+)">'
)


def panels(html):
    """(tab id, tab label, panel HTML) for every tab panel, in page order."""
    starts = list(re.finditer(PANEL, html))
    ends = [m.start() for m in starts[1:]] + [len(html)]
    return [(m[1], m[3], html[m.end() : end]) for m, end in zip(starts, ends, strict=True)]


def change_page(client, theme=None):
    if theme is None:
        theme = Theme.objects.create(name="Main", slug="main")
    return client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content.decode()


def test_every_section_has_a_tab():
    in_tabs = {item for _, items in THEME_TABS for item in items}
    assert {name for name, _ in THEME_FIELDSETS} <= in_tabs


def test_only_the_color_advanced_and_expert_groups_stay_folded():
    assert STAY_FOLDED == {
        "Light colors: Advanced",
        "Light colors: Expert",
        "Dark colors: Advanced",
        "Dark colors: Expert",
    }


def test_the_page_has_its_tabs_in_order(admin_client):
    # tabs.js puts the tabs in the order given by data-capy-tab-order.
    found = {int(order): label for _, order, label in re.findall(PANEL, change_page(admin_client))}
    assert [found[order] for order in sorted(found)] == TAB_LABELS


def test_tab_ids_come_from_their_labels(admin_client):
    ids = {tab_id for tab_id, _, _ in panels(change_page(admin_client))}
    assert {"capy-tab-general", "capy-tab-light-colors", "capy-tab-images"} <= ids


def test_every_section_is_still_on_the_page_with_its_old_id(admin_client):
    html = change_page(admin_client)
    for index, (name, _) in enumerate(THEME_FIELDSETS):
        if name:
            assert f'id="fieldset-0-{index}-heading" class="fieldset-heading">{name}<' in html


def test_sections_are_in_their_tabs(admin_client):
    by_label = {}
    for _, label, body in panels(change_page(admin_client)):
        by_label[label] = by_label.get(label, "") + body
    assert ">Logos<" in by_label["Branding"]
    assert ">Light colors: Expert<" in by_label["Light colors"]
    assert re.search(r'id="[^"]*asset[^"]*-group"', by_label["Images"])
    assert "Published revisions" in by_label["Revisions"]
    assert ">Advanced<" in by_label["Advanced"]


def test_folded_sections_open_in_their_tab_except_color_groups(admin_client):
    sections = re.findall(
        r"<div( data-capy-unfold)?>\s*<fieldset[^>]*>\s*(?:<details><summary>)?\s*"
        r'<h2 id="[^"]+" class="fieldset-heading">([^<]+)<',
        change_page(admin_client),
    )
    unfold = {name: bool(flag) for flag, name in sections}
    assert unfold["Contrast"] and unfold["Shape and effects"] and unfold["Backgrounds"]
    assert not unfold["Light colors: Expert"] and not unfold["Dark colors: Advanced"]


def test_the_tab_script_and_stylesheet_are_loaded(admin_client):
    html = change_page(admin_client)
    assert "capy_theme/admin/tabs.js" in html
    assert "capy_theme/admin/tabs.css" in html
    assert finders.find("capy_theme/admin/tabs.js")
    assert finders.find("capy_theme/admin/tabs.css")


def test_the_add_page_has_tabs_too(admin_client):
    html = admin_client.get(reverse("admin:capy_theme_theme_add")).content.decode()
    assert [label for _, label, _ in panels(html)][0] == "General"


def test_a_section_without_a_tab_goes_to_more():
    adminform = [SimpleNamespace(name="Publishing"), SimpleNamespace(name="Something new")]
    tabs = theme_tabs(adminform, [])
    assert [tab["label"] for tab in tabs] == ["General", LEFTOVER_TAB]
    assert tabs[1]["fieldsets"][0]["index"] == 1
    assert [tab["id"] for tab in tabs] == ["capy-tab-general", "capy-tab-more"]
    assert [tab["order"] for tab in tabs] == [0, 1]


def test_empty_tabs_are_left_out():
    tabs = theme_tabs([SimpleNamespace(name="Fonts")], [])
    assert [tab["label"] for tab in tabs] == ["Fonts"]


def test_every_section_and_list_renders_foldable_and_opens_with_its_tab(admin_client):
    html = change_page(admin_client)
    sections = len(THEME_FIELDSETS) + len(ThemeAdmin.inlines)
    assert html.count("<details>") == sections  # every section and list can be folded
    # tabs.js opens each one when its tab is shown, except the colors' Advanced and
    # Expert sections, which stay folded.
    assert html.count("data-capy-unfold") == sections - len(STAY_FOLDED)


def test_tabs_script_moves_focus_off_the_save_button_on_load():
    # If Django focused Save while every section was still folded (add page), the
    # first field of the open tab gets focus instead (#259). Runs in the browser.
    script = finders.find("capy_theme/admin/tabs.js")
    with open(script, encoding="utf-8") as file:
        text = file.read()
    assert 'closest(".submit-row")' in text and "(first || start.button).focus()" in text
