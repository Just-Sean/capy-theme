"""Add the ready-made system font stacks to the font library.

They use fonts already on visitors' devices, so nothing is downloaded. A frozen
copy of fonts.SYSTEM_STACKS at the time of this migration. Fonts that already
exist (by family name) are left as they are.
"""

from django.db import migrations

STACKS = [
    ('System sans', 'ui-sans-serif, system-ui, sans-serif'),
    ('System serif', 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif'),
    ('System mono', 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'),
    ('Transitional', 'Charter, "Bitstream Charter", "Sitka Text", Cambria, serif'),
    ('Old Style', '"Iowan Old Style", "Palatino Linotype", "URW Palladio L", P052, serif'),
    ('Humanist', 'Seravek, "Gill Sans Nova", Ubuntu, Calibri, "DejaVu Sans", source-sans-pro, sans-serif'),
    ('Geometric Humanist', 'Avenir, Montserrat, Corbel, "URW Gothic", source-sans-pro, sans-serif'),
    ('Neo-Grotesque', 'Inter, Roboto, "Helvetica Neue", "Arial Nova", "Nimbus Sans", Arial, sans-serif'),
    ('Rounded', 'ui-rounded, "Hiragino Maru Gothic ProN", Quicksand, Comfortaa, Manjari, "Arial Rounded MT", "Arial Rounded MT Bold", Calibri, source-sans-pro, sans-serif'),
    ('Slab Serif', 'Rockwell, "Rockwell Nova", "Roboto Slab", "DejaVu Serif", "Sitka Small", serif'),
    ('Didone', 'Didot, "Bodoni MT", "Noto Serif Display", "URW Palladio L", P052, Sylfaen, serif'),
    ('Monospace Code', 'ui-monospace, "Cascadia Code", "Source Code Pro", Menlo, Consolas, "DejaVu Sans Mono", monospace'),
    ('Industrial', 'Bahnschrift, "DIN Alternate", "Franklin Gothic Medium", "Nimbus Sans Narrow", sans-serif-condensed, sans-serif'),
]

LICENCE = "System fonts: nothing is downloaded. Stacks from Modern Font Stacks (CC0)."


def add_stacks(apps, schema_editor):
    Font = apps.get_model("capy_theme", "Font")
    for family, stack in STACKS:
        Font.objects.get_or_create(
            family=family,
            defaults={"source": "system", "fallback_stack": stack, "licence": LICENCE},
        )


def remove_stacks(apps, schema_editor):
    Font = apps.get_model("capy_theme", "Font")
    Font.objects.filter(source="system", family__in=[family for family, _ in STACKS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("capy_theme", "0007_font_fontfile"),
    ]

    operations = [
        migrations.RunPython(add_stacks, remove_stacks),
    ]
