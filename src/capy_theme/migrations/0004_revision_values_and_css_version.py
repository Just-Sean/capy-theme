"""Revisions store their base themes' full values, and get a stylesheet version.

Revisions published before this migration only stored the base theme names.
This fills in the values from the daisyUI catalogue the module ships with when
the migration runs, and gives each revision its css_version.
"""

import hashlib
import json

from django.db import migrations, models


def css_version(theme_id, number, snapshot):
    # A frozen copy of capy_theme.css.stylesheet.css_version, so this migration
    # keeps working even if that function changes later.
    data = json.dumps({"theme": theme_id, "number": number, "snapshot": snapshot}, sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:12]


def fill_values(snapshot, themes):
    """Return the snapshot with light_values and dark_values added from `themes`."""
    filled = dict(snapshot)
    for scheme in ("light", "dark"):
        if f"{scheme}_values" not in filled:
            theme = themes.get(filled.get(f"{scheme}_base"))
            filled[f"{scheme}_values"] = dict(theme["values"]) if theme else None
    return filled


def forwards(apps, schema_editor):
    from capy_theme.themes.catalogue import THEMES

    ThemeRevision = apps.get_model("capy_theme", "ThemeRevision")
    for revision in ThemeRevision.objects.all():
        revision.snapshot = fill_values(revision.snapshot, THEMES)
        revision.css_version = css_version(revision.theme_id, revision.number, revision.snapshot)
        revision.save(update_fields=["snapshot", "css_version"])


class Migration(migrations.Migration):
    dependencies = [
        ("capy_theme", "0003_themeassignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="themerevision",
            name="css_version",
            field=models.CharField(editable=False, max_length=16, null=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="themerevision",
            name="css_version",
            field=models.CharField(
                editable=False,
                help_text="Short hash naming this revision's stylesheet: /theme/<css_version>.css",
                max_length=16,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="themerevision",
            name="snapshot",
            field=models.JSONField(
                help_text="The theme's light and dark base names and their values, and its settings."
            ),
        ),
    ]
