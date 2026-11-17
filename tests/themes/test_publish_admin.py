"""Tests for publishing from the admin (issue #12): the theme page's Save draft, Save
and publish, and Save, publish and activate buttons, the theme list's row buttons
(#273), and the revision list."""

import re
from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from capy_theme.models import Theme, ThemeAssignment, ThemeRevision
from capy_theme.themes.active import activate, get_active_theme
from capy_theme.themes.publishing import publish

from ..admin.test_admin_tabs_unchanged import _post_back

pytestmark = pytest.mark.django_db
CHANGELIST = reverse("admin:capy_theme_theme_changelist")


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")


@pytest.fixture
def admin(client, user):
    client.force_login(user)
    return client


def change_url(theme):
    return reverse("admin:capy_theme_theme_change", args=[theme.pk])


def row_url(theme, action):
    return reverse(f"admin:capy_theme_theme_{action}", args=[theme.pk])


def press(client, theme, button, **extra):
    """Send the theme page back as it is, with one of its buttons pressed."""
    data = _post_back(client.get(change_url(theme)).content.decode())
    data[button] = ""
    data.update(extra)
    return client.post(change_url(theme), data)


def test_edit_page_has_the_three_buttons_with_descriptions_and_status(admin, theme):
    content = admin.get(change_url(theme)).content.decode()
    for button, words in [
        ("_capy_save", "Visitors see nothing until you publish."),
        ("_capy_publish", "makes this version of the theme live"),
        ("_capy_publish_activate", "makes this the default theme"),
    ]:
        assert f'name="{button}"' in content and words in content, button
    assert "Not published yet" in content  # the status line
    assert "Never published" in content  # the Publishing section's status, as before
    # One place: no Publish link at the top, no Django save buttons, no separate page.
    assert 'name="_save"' not in content and 'name="_addanother"' not in content
    assert 'name="_continue"' not in content
    assert "/publish/" not in content


def test_save_draft_stays_on_the_page_and_doesnt_publish(admin, theme):
    response = press(admin, theme, "_capy_save", light_base="cupcake")
    assert response.status_code == 302 and response.url == change_url(theme)
    theme.refresh_from_db()
    assert theme.light_base == "cupcake" and theme.live_revision is None
    assert (
        "won&#x27;t see it until it&#x27;s published"
        in admin.get(change_url(theme)).content.decode()
    )


def test_save_and_publish_publishes_the_saved_draft_with_the_note(admin, theme, user):
    response = press(admin, theme, "_capy_publish", light_base="cupcake", _capy_note=" Launch ")
    assert response.status_code == 302 and response.url == change_url(theme)
    theme.refresh_from_db()
    revision = theme.live_revision
    assert (revision.number, revision.note, revision.published_by) == (1, "Launch", user)
    assert revision.snapshot["light_base"] == "cupcake"  # what was just saved
    assert get_active_theme() is None  # not activated


def test_save_publish_and_activate(admin, theme):
    response = press(admin, theme, "_capy_publish_activate")
    assert response.status_code == 302
    theme.refresh_from_db()
    assert theme.live_revision.number == 1
    assert get_active_theme().pk == theme.pk
    content = admin.get(change_url(theme)).content.decode()
    assert "“Main” is now the default theme." in content
    # Already the site's theme: no activate button.
    assert 'name="_capy_publish_activate"' not in content


def test_publishing_with_no_changes_says_so(admin, theme, user):
    publish(theme, user=user)
    response = press(admin, theme, "_capy_publish")
    assert response.status_code == 302
    assert "Nothing to publish" in admin.get(change_url(theme)).content.decode()
    assert theme.revisions.count() == 1


def test_publish_and_activate_with_no_changes_still_activates(admin, theme, user):
    publish(theme, user=user)
    press(admin, theme, "_capy_publish_activate")
    assert theme.revisions.count() == 1
    assert get_active_theme().pk == theme.pk


def test_a_new_theme_can_be_saved_and_published_at_once(admin):
    add = reverse("admin:capy_theme_theme_add")
    data = _post_back(admin.get(add).content.decode())
    data.update({"name": "New", "slug": "new", "_capy_publish": ""})
    response = admin.post(add, data)
    theme = Theme.objects.get(slug="new")
    assert response.status_code == 302 and response.url == change_url(theme)
    assert theme.live_revision.number == 1


def test_edit_page_lists_revisions_read_only(admin, theme, user):
    publish(theme, user=user, note="First")
    response = admin.get(change_url(theme))
    content = response.content.decode()
    assert "Published revisions" in content
    assert "First" in content
    assert "revisions-0-DELETE" not in content  # no delete checkbox
    assert 'name="revisions-0-note"' not in content  # not editable


def test_saving_the_edit_form_doesnt_publish(admin, theme, user):
    publish(theme, user=user)
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "cupcake",
        "dark_base": "dark",
        "settings": "{}",
        "assets-TOTAL_FORMS": "0",
        "assets-INITIAL_FORMS": "0",
        "revisions-TOTAL_FORMS": "1",
        "revisions-INITIAL_FORMS": "1",
        "revisions-MIN_NUM_FORMS": "0",
        "revisions-MAX_NUM_FORMS": "1000",
    }
    response = admin.post(change_url(theme), data)
    assert response.status_code == 302, response.content
    theme.refresh_from_db()
    assert theme.light_base == "cupcake"
    assert theme.live_revision.snapshot["light_base"] == "light"
    assert theme.has_unpublished_changes


def test_list_shows_live_revision_and_unpublished_changes(admin, theme, user):
    publish(theme, user=user)
    response = admin.get(reverse("admin:capy_theme_theme_changelist"))
    assert response.status_code == 200
    assert b"Live revision" in response.content
    assert b"Unpublished changes" in response.content


def test_a_simultaneous_publish_is_explained(admin, theme, monkeypatch):
    # Simulates someone else publishing at the same moment: the database
    # refuses the duplicate revision number.
    def collide(*args, **kwargs):
        raise IntegrityError("duplicate revision number")

    monkeypatch.setattr("capy_theme.admin.save_publish.publish", collide)
    response = admin.post(row_url(theme, "publish_now"), follow=True)
    assert response.status_code == 200
    assert b"Someone else just published this theme" in response.content
    assert not ThemeRevision.objects.exists()


def test_staff_without_change_permission_cant_publish(client, theme, django_user_model):
    viewer = django_user_model.objects.create_user("viewer", password="pw", is_staff=True)
    client.force_login(viewer)
    for action in ("publish_now", "publish_activate", "activate"):
        assert client.post(row_url(theme, action)).status_code == 403
    assert not ThemeRevision.objects.exists()


def test_publishing_explains_an_invalid_draft(client, django_user_model, theme, settings):
    # Issue #186: the draft uses a base the project no longer allows (the setting
    # changed after it was saved), so publishing is refused with the reason.
    # A staff user with only the permissions publishing needs.
    staff = django_user_model.objects.create_user("publisher", password="pw", is_staff=True)
    staff.user_permissions.set(
        Permission.objects.filter(codename__in=["view_theme", "change_theme", "publish_theme"])
    )
    client.force_login(staff)
    Theme.objects.filter(pk=theme.pk).update(light_base="cupcake")
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]
    response = client.post(row_url(theme, "publish_now"), follow=True)
    content = response.content.decode()
    assert "Can&#x27;t publish:" in content
    assert "&#x27;cupcake&#x27; is not an available light daisyUI theme." in content
    assert not ThemeRevision.objects.exists()


# The theme list's row buttons (#273)


def row_buttons(client, theme):
    content = client.get(CHANGELIST).content.decode()
    row = content[content.index(f"/{theme.pk}/change/") :]
    return row[: row.index("</tr>")]


def test_the_list_has_publish_buttons_on_each_row(admin, theme, user):
    row = row_buttons(admin, theme)
    assert ">Publish<" in row and ">Publish and activate<" in row
    assert ">Activate<" not in row  # never published
    assert 'form="changelist-form"' in row and 'formmethod="post"' in row
    assert "activate_theme" not in admin.get(CHANGELIST).content.decode()  # no dropdown action
    publish(theme, user=user)
    row = row_buttons(admin, theme)
    assert ">Publish<" not in row and ">Activate<" in row  # nothing new to publish
    activate(theme)
    assert "—" in row_buttons(admin, theme)  # published and the site's theme


def test_the_row_buttons_publish_and_activate(admin, theme):
    response = admin.post(row_url(theme, "publish_now"))
    assert response.status_code == 302 and response.url == CHANGELIST
    theme.refresh_from_db()
    assert theme.live_revision.number == 1 and get_active_theme() is None
    other = Theme.objects.create(name="Other", slug="other")
    admin.post(row_url(other, "publish_activate"))
    assert get_active_theme().pk == other.pk
    admin.post(row_url(theme, "activate"))
    assert get_active_theme().pk == theme.pk


def test_activating_an_unpublished_theme_is_refused(admin, theme):
    response = admin.post(row_url(theme, "activate"), follow=True)
    assert "Publish “Main” before activating it." in response.content.decode()
    assert get_active_theme() is None


def test_the_row_buttons_only_accept_post(admin, theme):
    for action in ("publish_now", "publish_activate", "activate"):
        assert admin.get(row_url(theme, action)).status_code == 405
    assert not ThemeRevision.objects.exists()


# QA for #273: edge cases


ADD = reverse("admin:capy_theme_theme_add")


def test_a_non_numeric_id_on_the_theme_page_isnt_a_server_error(admin):
    # Django's own change page redirects for an id that can't exist; it must not crash.
    response = admin.get("/admin/capy_theme/theme/abc/change/")
    assert response.status_code == 302


@pytest.mark.parametrize("path", ["publish-now", "publish-and-activate", "activate"])
def test_a_non_numeric_id_on_a_row_button_is_not_found(admin, path):
    assert admin.post(f"/admin/capy_theme/theme/abc/{path}/").status_code == 404


@pytest.mark.parametrize("action", ["publish_now", "publish_activate", "activate"])
def test_a_row_button_for_a_missing_theme_is_not_found(admin, action):
    assert admin.post(reverse(f"admin:capy_theme_theme_{action}", args=[999])).status_code == 404


def test_save_draft_in_a_popup_closes_the_popup(admin):
    # The Scheduled theme and Site theme pages add a theme in a popup ("+").
    url = ADD + "?_popup=1"
    data = _post_back(admin.get(url).content.decode())
    data.update({"name": "Pop", "slug": "pop", "_capy_save": "", "_popup": "1"})
    response = admin.post(url, data)
    assert response.status_code == 200  # Django's popup response, not a redirect
    assert Theme.objects.filter(slug="pop").exists()


def test_an_add_only_user_isnt_sent_to_a_page_they_cant_open(client, django_user_model):
    user = django_user_model.objects.create_user("adder", password="pw", is_staff=True)
    user.user_permissions.set(Permission.objects.filter(codename="add_theme"))
    client.force_login(user)
    data = _post_back(client.get(ADD).content.decode())
    data.update({"name": "New", "slug": "new", "_capy_save": ""})
    response = client.post(ADD, data)
    assert response.status_code == 302
    assert client.get(response.url).status_code == 200


def test_the_publish_note_survives_a_form_error(admin, theme):
    response = press(admin, theme, "_capy_publish", slug="", _capy_note="Launch notes")
    assert response.status_code == 200
    assert 'value="Launch notes"' in response.content.decode()


def running_schedule(theme):
    now = timezone.now()
    return ThemeAssignment.objects.create(
        theme=theme, site="", starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1)
    )


def test_activate_during_a_running_schedule_doesnt_claim_success(admin, theme, user):
    publish(theme, user=user)
    sale = Theme.objects.create(name="Sale", slug="sale")
    publish(sale, user=user)
    running_schedule(sale)
    content = admin.post(row_url(theme, "activate"), follow=True).content.decode()
    if "“Main” is now the default theme." in content:
        assert get_active_theme().pk == theme.pk, "told it's showing; Sale still is"
    # It says what happened instead: the default changed, the schedule still shows.
    assert "“Main” is now the default theme, but a theme schedule is showing “Sale”" in content


def test_the_default_theme_isnt_offered_activate_during_a_schedule(admin, theme, user):
    publish(theme, user=user)
    activate(theme)
    sale = Theme.objects.create(name="Sale", slug="sale")
    publish(sale, user=user)
    running_schedule(sale)
    assert 'name="_capy_publish_activate"' not in admin.get(change_url(theme)).content.decode()


def test_a_scheduled_theme_can_still_be_made_the_default(admin, user):
    sale = Theme.objects.create(name="Sale", slug="sale")
    publish(sale, user=user)
    running_schedule(sale)
    assert ">Activate<" in row_buttons(admin, sale)


# Coverage (passing)


def test_without_a_capy_button_django_buttons_still_work(admin, theme):
    for button, where in [("_save", CHANGELIST), ("_addanother", ADD), ("_continue", None)]:
        response = press(admin, theme, button, light_base="cupcake")
        assert response.status_code == 302
        assert response.url == (where or change_url(theme))
    assert not ThemeRevision.objects.exists()


def test_several_buttons_at_once_do_the_first_one(admin, theme):
    data = _post_back(admin.get(change_url(theme)).content.decode())
    data.update({"_capy_save": "", "_capy_publish_activate": ""})
    admin.post(change_url(theme), data)
    assert not ThemeRevision.objects.exists() and get_active_theme() is None
    data = _post_back(admin.get(change_url(theme)).content.decode())
    data.update({"_capy_publish": "", "_capy_publish_activate": ""})
    admin.post(change_url(theme), data)
    theme.refresh_from_db()
    assert theme.live_revision.number == 1 and get_active_theme() is None


def test_a_very_long_note_is_cut_to_2000_characters(admin, theme):
    press(admin, theme, "_capy_publish", _capy_note="é" * 5000)
    theme.refresh_from_db()
    assert theme.live_revision.note == "é" * 2000


def test_a_form_error_publishes_and_activates_nothing(admin, theme):
    response = press(admin, theme, "_capy_publish_activate", slug="")
    assert response.status_code == 200
    assert "Not published yet" in response.content.decode()
    assert not ThemeRevision.objects.exists() and get_active_theme() is None


def test_view_only_users_have_no_buttons_and_cant_post_them(client, django_user_model, theme):
    viewer = django_user_model.objects.create_user("viewer", password="pw", is_staff=True)
    viewer.user_permissions.set(
        Permission.objects.filter(codename__in=["view_theme", "publish_theme"])
    )
    client.force_login(viewer)
    content = client.get(change_url(theme)).content.decode()
    assert 'name="_capy_save"' not in content and 'name="_capy_publish"' not in content
    response = client.post(change_url(theme), {"_capy_publish": "", "name": "X", "slug": "x"})
    assert response.status_code == 403
    assert not ThemeRevision.objects.exists()


@pytest.mark.parametrize("action", ["publish_now", "publish_activate", "activate"])
def test_row_buttons_need_login(client, theme, action):
    response = client.post(row_url(theme, action))
    assert response.status_code == 302 and "login" in response.url
    assert not ThemeRevision.objects.exists()


def test_activating_the_site_theme_again_keeps_one_assignment(admin, theme, user):
    publish(theme, user=user)
    activate(theme)
    assert admin.post(row_url(theme, "activate")).status_code == 302
    assert ThemeAssignment.objects.count() == 1 and get_active_theme().pk == theme.pk


def test_the_status_line_and_active_column_agree_after_activating(admin, theme, user):
    other = Theme.objects.create(name="Other", slug="other")
    for each in (theme, other):
        publish(each, user=user)
    activate(other)
    admin.get(CHANGELIST)  # both pages seen while Other is the site's theme
    admin.get(change_url(theme))
    admin.post(row_url(theme, "activate"))
    assert "<dt>Default theme</dt><dd>Yes</dd>" in admin.get(change_url(theme)).content.decode()
    assert "icon-yes" in row_buttons(admin, theme)
    assert "icon-no" in row_buttons(admin, other)


# Second round (#273 review fixes)


def test_the_status_says_when_a_schedule_shows_another_theme(admin, theme, user):
    publish(theme, user=user)
    activate(theme)
    sale = Theme.objects.create(name="Sale", slug="sale")
    publish(sale, user=user)
    running_schedule(sale)
    content = admin.get(change_url(theme)).content.decode()
    assert "<dt>Default theme</dt><dd>Yes</dd>" in content
    assert "<dt>Showing now</dt><dd>“Sale”, because a theme schedule is running</dd>" in content
    sale_page = admin.get(change_url(sale)).content.decode()
    assert "No (the default is “Main”)" in sale_page
    assert 'name="_capy_publish_activate"' in sale_page  # Sale can still be made the default


def test_publishing_buttons_ask_first_and_save_draft_doesnt(admin, theme):
    content = admin.get(change_url(theme)).content.decode()
    save = content[content.index('name="_capy_save"') - 120 : content.index('name="_capy_save"')]
    assert "data-capy-confirm" not in save
    assert content.count("data-capy-confirm=") == 2  # Save and publish; ... and activate
    assert "capy_theme/admin/confirm.js" in content
    listing = admin.get(CHANGELIST).content.decode()
    assert "capy_theme/admin/confirm.js" in listing
    assert 'data-capy-confirm="Publish “Main”? Visitors will see it."' in row_buttons(admin, theme)


def test_the_buttons_look_like_admin_buttons(admin, theme):
    content = admin.get(change_url(theme)).content.decode()
    assert 'class="button default" name="_capy_save"' in content
    assert 'class="button" name="_capy_publish"' in content


def test_the_note_is_above_the_buttons_and_a_draft_save_says_its_not_kept(admin, theme):
    content = admin.get(change_url(theme)).content.decode()
    assert content.index('name="_capy_note"') < content.index('name="_capy_save"')
    press(admin, theme, "_capy_save", _capy_note="For later")
    page = admin.get(change_url(theme)).content.decode()
    assert "The note wasn&#x27;t kept: notes are only kept when you publish." in page
    assert not ThemeRevision.objects.exists()


def test_a_popup_has_no_activate_button(admin):
    content = admin.get(ADD + "?_popup=1").content.decode()
    assert 'name="_capy_publish"' in content
    assert 'name="_capy_publish_activate"' not in content


def test_view_only_users_get_a_close_link(client, django_user_model, theme):
    viewer = django_user_model.objects.create_user("viewer", password="pw", is_staff=True)
    viewer.user_permissions.set(Permission.objects.filter(codename="view_theme"))
    client.force_login(viewer)
    content = client.get(change_url(theme)).content.decode()
    assert 'class="closelink">Close</a>' in content


def test_the_delete_link_keeps_the_lists_filters(admin, theme):
    filters = "_changelist_filters=light_base%3Dlight"
    content = admin.get(change_url(theme) + "?" + filters).content.decode()
    assert re.search(r'href="[^"]*/delete/\?_changelist_filters=light_base%3Dlight"', content)


def test_row_buttons_go_back_to_the_filtered_list(admin, theme):
    listing = CHANGELIST + "?q=Main"
    response = admin.post(row_url(theme, "publish_now"), HTTP_REFERER="http://testserver" + listing)
    assert response.url == "http://testserver" + listing
    elsewhere = admin.post(row_url(theme, "activate"), HTTP_REFERER="https://evil.example/")
    assert elsewhere.url == CHANGELIST  # never back to another site
