"""manage.py theme_export <slug> [--output FILE]: save a theme as an export zip."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ...models import Theme
from ...portability.export import export_theme


class Command(BaseCommand):
    help = "Export a theme (its draft, images and fonts) as a zip another site can import."

    def add_arguments(self, parser):
        parser.add_argument("slug", help="The theme's slug.")
        parser.add_argument(
            "--output", "-o", help="Where to write it (default <slug>.capy-theme.zip)."
        )

    def handle(self, slug, output=None, **options):
        theme = Theme.objects.filter(slug=slug).first()
        if theme is None:
            raise CommandError(f"No theme with the slug {slug!r}.")
        path = Path(output or f"{slug}.capy-theme.zip")
        path.write_bytes(export_theme(theme))
        self.stdout.write(self.style.SUCCESS(f"Exported “{theme}” to {path}"))
