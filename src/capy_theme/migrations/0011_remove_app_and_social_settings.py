"""Remove the web app manifest and link-preview settings (#143).

capy-theme exposes theme artifacts but no longer serves a manifest or link-preview
tags, so the "app" and "social" settings keys go. The sharing image itself stays.
"""

from django.db import migrations


def remove_keys(apps, schema_editor):
    Theme = apps.get_model("capy_theme", "Theme")
    for theme in Theme.objects.all():
        if "app" in theme.settings or "social" in theme.settings:
            theme.settings.pop("app", None)
            theme.settings.pop("social", None)
            theme.save(update_fields=["settings"])


class Migration(migrations.Migration):
    dependencies = [("capy_theme", "0010_logo_slots")]

    operations = [migrations.RunPython(remove_keys, migrations.RunPython.noop)]
