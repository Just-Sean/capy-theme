"""The storage capy-theme saves and serves its uploads from.

``CAPY_THEME_STORAGE`` names an entry in the project's ``STORAGES`` setting
(default ``"default"``). A project whose default storage is private — e.g. a
capy-project starter, where media is staff-only — sets it to a public storage so
theme images, icons and fonts are reachable by visitors.

It's a callable, so model ``FileField``s can use it as ``storage=theme_storage``
without baking the choice into a migration: Django keeps the reference and
resolves the storage from the setting at startup.
"""

from django.core.files.storage import storages

from . import conf


def theme_storage():
    """The storage capy-theme uses for its uploads (``CAPY_THEME_STORAGE``)."""
    return storages[conf.get("CAPY_THEME_STORAGE")]
