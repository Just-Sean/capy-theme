"""What visitors see, for the editor's "See it as a visitor" switch.

The summary lists what's set up for visitors; the view gives the published CSS
visitors would get, optionally with an offered theme or on a given date.
"""

from datetime import datetime, time

from django.core.exceptions import ValidationError
from django.utils import timezone

from ..css.stylesheet import render_css
from ..themes.active import (
    get_active_theme,
    offered_themes,
    scheduled_assignments,
    theme_at,
    visitor_themes_allowed,
)
from ..themes.mode import MODE_LABELS, mode_settings


def visitor_summary():
    """The live theme, its mode settings, the offered themes and the schedule."""
    live = get_active_theme()
    now = timezone.now()
    default_mode, can_switch = mode_settings(live.live_revision) if live else ("auto", True)
    return {
        "live_theme": live.name if live else None,
        "default_mode": MODE_LABELS[default_mode],
        "can_switch": can_switch,
        "visitor_themes": visitor_themes_allowed(),
        "offered": [{"slug": t.slug, "name": t.name} for t in offered_themes()],
        "schedule": [
            {
                "theme": a.theme.name,
                "starts_at": a.starts_at.isoformat() if a.starts_at else None,
                "ends_at": a.ends_at.isoformat() if a.ends_at else None,
                "running": a.is_running(now),
            }
            for a in scheduled_assignments()
            if a.ends_at is None or a.ends_at > now
        ],
    }


def visitor_view(theme_slug="", day=""):
    """The published CSS visitors get: {"theme", "css"}.

    `theme_slug` picks an offered theme (as a visitor's choice would); `day`
    ("YYYY-MM-DD") shows the site's theme at noon that day, to check schedules.
    Raises ValidationError for an unknown theme or a bad date.
    """
    if theme_slug:
        theme = next((t for t in offered_themes() if t.slug == theme_slug), None)
        if theme is None:
            raise ValidationError("That theme isn't offered to visitors.")
    elif day:
        try:
            date = datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError as error:
            raise ValidationError("Use a date like 2026-12-10.") from error
        when = timezone.make_aware(datetime.combine(date, time(12)))
        theme = theme_at(when)
    else:
        theme = get_active_theme()
    if theme is None or theme.live_revision is None:
        return {"theme": None, "css": ""}
    return {"theme": theme.name, "css": render_css(theme.live_revision)}
