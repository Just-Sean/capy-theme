"""Add capy-theme's curated font collection to the font library.

    uv run python manage.py capy_theme_add_fonts

Copies each bundled WOFF2 file into the project's media storage (so bundled fonts
work like uploaded ones, on any storage) and creates the Font and FontFile rows.
Fonts already in the library (by family name) are skipped, so it's safe to run
again.
"""

import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from capy_theme.models import Font, FontFile

MODULE = Path(__file__).resolve().parent.parent.parent
MANIFEST = MODULE / "curated_fonts.json"
STATIC_FONTS = MODULE / "static" / "capy_theme" / "fonts"


class Command(BaseCommand):
    help = "Add capy-theme's curated, open-licence fonts to the font library."

    def handle(self, *args, **options):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        added = skipped = 0
        for entry in manifest:
            if Font.objects.filter(family=entry["family"]).exists():
                skipped += 1
                continue
            with transaction.atomic():
                font = Font.objects.create(
                    family=entry["family"],
                    source="bundled",
                    fallback_stack=entry["fallback"],
                    licence=f"{entry['licence']}. Bundled with capy-theme from Fontsource "
                    f"(@fontsource/{entry['id']} {entry['version']}).",
                )
                for item in entry["files"]:
                    data = (STATIC_FONTS / item["path"]).read_bytes()
                    font_file = FontFile(
                        font=font, weight=item["weight"], style=item["style"], subset="latin"
                    )
                    font_file.file.save(Path(item["path"]).name, ContentFile(data), save=True)
            added += 1
            self.stdout.write(f"Added {entry['family']} ({len(entry['files'])} files)")
        self.stdout.write(
            self.style.SUCCESS(f"Done: {added} fonts added, {skipped} already in the library.")
        )
