"""The admin: themes (with their Publish, Revisions and Restore pages), fonts and the
theme schedule. Importing the modules registers them with Django's admin."""

from . import fonts, schedule, theme_admin  # noqa: F401
