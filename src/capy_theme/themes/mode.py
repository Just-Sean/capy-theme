"""The theme's configured color mode: the admin's default and whether switching is offered.

These are settings the admin configures; capy-theme exposes them (in the artifacts ``mode``
key). capy-theme never switches modes or applies one to a page — a consumer reads the
setting and does what it likes with it.
"""


def mode_settings(revision):
    """Return (default_mode, visitors_can_switch) from a published revision."""
    settings = revision.snapshot.get("settings", {})
    return settings.get("default_mode", "auto"), settings.get("visitors_can_switch", True)
