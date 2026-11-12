"""The settings a project can set in its settings.py, and their defaults.

Every CAPY_THEME_* setting is read through get(), so this is the one place that
lists them. The README's Settings table lists the same ones (a test checks).
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

MB = 1024 * 1024

DEFAULTS = {
    "CAPY_THEME_BUILTIN_THEMES": None,  # None: all of daisyUI's built-in themes
    "CAPY_THEME_CACHE_SECONDS": 300,
    "CAPY_THEME_API": "auto",
    "CAPY_THEME_VISITOR_THEMES": True,
    "CAPY_THEME_CUSTOM_CSS": True,
    "CAPY_THEME_EDITOR_BUTTON": True,
    "CAPY_THEME_FONT_MAX_BYTES": 5 * MB,
    "CAPY_THEME_IMAGE_MAX_BYTES": None,  # None: each image slot's own limit
    "CAPY_THEME_ANIMATION_MAX_FRAMES": 500,
    "CAPY_THEME_ANIMATION_MAX_SIZE": 2000,  # px wide or high, for animated images only
    "CAPY_THEME_ANIMATION_MAX_PIXELS": 100_000_000,  # frames × width × height
    "CAPY_THEME_IMPORT_MAX_BYTES": 50 * MB,
}


def get(name):
    """The project's value for a CAPY_THEME_* setting, or its default."""
    return getattr(settings, name, DEFAULTS[name])


def positive_int(name):
    """A setting that must be a positive whole number (e.g. a safety limit).

    Anything else, including None and 0, is a mistake in the project's settings
    rather than a way to switch the limit off, so it's reported clearly.
    """
    value = get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ImproperlyConfigured(f"{name} must be a positive whole number, not {value!r}.")
    return value
