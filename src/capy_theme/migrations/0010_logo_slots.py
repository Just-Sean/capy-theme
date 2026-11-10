"""Move each theme's single logo into the main logo slot (a ThemeAsset)."""

import io

from django.db import migrations


def move_logos(apps, schema_editor):
    from PIL import Image

    Theme = apps.get_model("capy_theme", "Theme")
    ThemeAsset = apps.get_model("capy_theme", "ThemeAsset")
    types = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "GIF": "image/gif"}
    for theme in Theme.objects.exclude(logo=""):
        width = height = size = 0
        content_type = "image/png"
        try:
            with theme.logo.open("rb") as file:
                data = file.read()
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size
                content_type = types.get(image.format, content_type)
            size = len(data)
        except (OSError, ValueError):
            pass  # file missing: the asset keeps the name, with unknown size
        asset = ThemeAsset.objects.create(
            theme=theme,
            slot="logo_main",
            mode="light",
            original=theme.logo.name,
            alt_text=theme.settings.get("logo_alt", ""),
            width=width,
            height=height,
            size=size,
            content_type=content_type,
        )
        theme.settings.setdefault("images", {})["logo_main"] = {"light": asset.pk}
        theme.save(update_fields=["settings"])


class Migration(migrations.Migration):
    dependencies = [("capy_theme", "0009_themeasset_themeassetvariant")]

    operations = [
        migrations.RunPython(move_logos, migrations.RunPython.noop),
        migrations.RemoveField(model_name="theme", name="logo"),
    ]
