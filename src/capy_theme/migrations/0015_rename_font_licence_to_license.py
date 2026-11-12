"""Rename Font.licence to Font.license (American spelling, issue #199).

A rename, so every font's license note is kept.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("capy_theme", "0014_sitetheme")]

    operations = [
        migrations.RenameField(model_name="font", old_name="licence", new_name="license"),
        migrations.AlterField(
            model_name="font",
            name="license",
            field=models.TextField(blank=True, help_text="The font's license, or where to find it."),
        ),
    ]
