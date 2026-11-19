"""The CAPY_THEME_STORAGE setting and the theme_storage() helper (issue #280)."""

from django.core.files.storage import storages
from django.test import override_settings

from capy_theme.fonts.models import FontFile
from capy_theme.images.models import ThemeAsset, ThemeAssetVariant
from capy_theme.storage import theme_storage

# A project with a separate public storage, like a capy-project starter.
PUBLIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    "capy_public": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
}


def test_defaults_to_the_default_storage():
    assert theme_storage() is storages["default"]


@override_settings(STORAGES=PUBLIC_STORAGES, CAPY_THEME_STORAGE="capy_public")
def test_follows_the_setting():
    # Every save and URL goes through theme_storage(), so this covers all of them.
    assert theme_storage() is storages["capy_public"]


def test_model_file_fields_use_the_theme_storage_callable():
    # A callable keeps the choice out of migrations and lets the setting pick the
    # storage at startup; check every uploaded FileField uses it.
    for model, field in [(FontFile, "file"), (ThemeAsset, "original"), (ThemeAssetVariant, "file")]:
        _, _, _, kwargs = model._meta.get_field(field).deconstruct()
        assert kwargs["storage"] is theme_storage
