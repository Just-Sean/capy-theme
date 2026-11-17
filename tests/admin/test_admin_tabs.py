"""Tests for the tabs on the theme edit page."""

import re
from types import SimpleNamespace

import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse

from capy_theme.admin.fieldsets import THEME_FIELDSETS
from capy_theme.admin.tabs import LEFTOVER_TAB, THEME_TABS, theme_tabs
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


def test_every_section_and_list_renders_foldable_and_starts_folded(admin_client):
    html = change_page(admin_client)
    sections = len(THEME_FIELDSETS) + len(ThemeAdmin.inlines)
    assert html.count("<details>") == sections  # every section and list, all folded
    assert "<details open" not in html
    assert "data-capy-unfold" not in html  # tabs.js no longer opens them (#267)


def test_tabs_script_opens_no_sections():
    # Every section starts folded; the script never opens one (#267).
    script = finders.find("capy_theme/admin/tabs.js")
    with open(script, encoding="utf-8") as file:
        text = file.read()
    assert not re.search(r"\.open\s*=|setAttribute\(\s*[\"']open|toggleAttribute", text)


def test_tabs_script_moves_focus_off_the_save_button_on_load():
    # If Django focused Save because every section is folded (add page), the first
    # field with an error gets focus, or else the title of the open tab's first
    # section (#259, #267). Runs in the browser.
    script = finders.find("capy_theme/admin/tabs.js")
    with open(script, encoding="utf-8") as file:
        text = file.read()
    assert 'closest(".submit-row")' in text
    assert (
        '(firstErrorField(start) || start.panels[0].querySelector("summary") || start.button)'
        ".focus()"
    ) in text
    assert 'closest(".errors, td")' in text


def test_a_failed_save_shows_the_section_with_the_error(admin_client):
    # Django renders a folding section that has errors unfolded (no <details>), so
    # the error is visible; tabs.js marks its tab (#267).
    data = {
        "name": "",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "settings": "{}",
        "assets-TOTAL_FORMS": "0",
        "assets-INITIAL_FORMS": "0",
        "revisions-TOTAL_FORMS": "0",
        "revisions-INITIAL_FORMS": "0",
        "revisions-MIN_NUM_FORMS": "0",
        "revisions-MAX_NUM_FORMS": "1000",
    }
    response = admin_client.post(reverse("admin:capy_theme_theme_add"), data)
    assert response.status_code == 200  # not saved: the page comes back with errors
    html = response.content.decode()
    heading = r'<h2 id="[^"]+" class="fieldset-heading">{}</h2>'
    assert re.search(r"<fieldset[^>]*>\s*" + heading.format("Name"), html)  # unfolded
    assert re.search(r"<details><summary>\s*" + heading.format("Base themes"), html)
    name_panel = next(body for _, label, body in panels(html) if label == "General")
    assert "errorlist" in name_panel
