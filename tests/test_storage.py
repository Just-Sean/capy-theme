"""The CAPY_THEME_STORAGE setting and the theme_storage() helper (issue #280)."""

from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import override_settings

from capy_theme.fonts.library import file_url
from capy_theme.fonts.models import FontFile
from capy_theme.images.models import ThemeAsset, ThemeAssetVariant
from capy_theme.storage import theme_storage

# A project with a separate public storage, like a capy-project starter. The
# base_urls let .url() work so an end-to-end test can compare the served URL.
PUBLIC_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
        "OPTIONS": {"base_url": "/media/"},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    "capy_public": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
        "OPTIONS": {"base_url": "/public/"},
    },
}


def test_defaults_to_the_default_storage():
    assert theme_storage() is storages["default"]


@override_settings(STORAGES=PUBLIC_STORAGES, CAPY_THEME_STORAGE="capy_public")
def test_follows_the_setting():
    # The manual save/URL call sites all resolve the backend via theme_storage();
    # test_a_manual_save_and_url_route_through_the_configured_storage proves one end to end.
    assert theme_storage() is storages["capy_public"]


@override_settings(STORAGES=PUBLIC_STORAGES, CAPY_THEME_STORAGE="capy_public")
def test_a_manual_save_and_url_route_through_the_configured_storage():
    # Prove a real call site routes through the configured storage, not just that
    # theme_storage() resolves it — a call site left on default_storage would fail here.
    name = "capy_theme/fonts/x.woff2"
    theme_storage().save(name, ContentFile(b"font-bytes"))
    assert storages["capy_public"].exists(name)
    assert not storages["default"].exists(name)
    assert file_url(name) == storages["capy_public"].url(name)


def test_model_file_fields_use_the_theme_storage_callable():
    # A callable keeps the choice out of migrations and lets the setting pick the
    # storage at startup; check every uploaded FileField uses it.
    for model, field in [(FontFile, "file"), (ThemeAsset, "original"), (ThemeAssetVariant, "file")]:
        _, _, _, kwargs = model._meta.get_field(field).deconstruct()
        assert kwargs["storage"] is theme_storage
