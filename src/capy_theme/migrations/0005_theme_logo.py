"""Themes get a main logo, and revisions record which logo file they published."""

from django.db import migrations, models


def add_empty_logo(apps, schema_editor):
    # Revisions published before logos existed had none.
    ThemeRevision = apps.get_model("capy_theme", "ThemeRevision")
    for revision in ThemeRevision.objects.all():
        if "logo" not in revision.snapshot:
            revision.snapshot = {**revision.snapshot, "logo": ""}
            revision.save(update_fields=["snapshot"])


class Migration(migrations.Migration):
    dependencies = [
        ("capy_theme", "0004_revision_values_and_css_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="theme",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="The main logo (PNG, JPEG, GIF or WebP). Shown at the size it's uploaded.",
                upload_to="capy_theme/logos/",
            ),
        ),
        migrations.AlterField(
            model_name="themerevision",
            name="snapshot",
            field=models.JSONField(
                help_text="The theme's light and dark base names and their values, logo and settings."
            ),
        ),
        migrations.RunPython(add_empty_logo, migrations.RunPython.noop),
    ]
