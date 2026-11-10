"""manage.py theme_rebuild_images [<slug>]: remake every generated image.

Logo copies and sharing-image crops are made again from the uploaded originals,
and the icons of published revisions are made again. Useful after a capy-theme
update changes how they're made, or for logos moved into the main slot by
migration 0010 (which have no smaller copies).
"""

from django.core.management.base import BaseCommand, CommandError

from ...images.icons import make_icons
from ...images.sharing import make_sharing_image
from ...images.variants import make_variants
from ...models import Theme


class Command(BaseCommand):
    help = "Remake logo copies, sharing-image crops and icons (one theme, or every theme)."

    def add_arguments(self, parser):
        parser.add_argument("slug", nargs="?", help="Only this theme (default: every theme).")

    def handle(self, slug=None, **options):
        themes = Theme.objects.all()
        if slug:
            themes = themes.filter(slug=slug)
            if not themes.exists():
                raise CommandError(f"No theme with the slug {slug!r}.")
        images = icons = 0
        for theme in themes.prefetch_related("assets__variants", "revisions"):
            for asset in theme.assets.all():
                if asset.content_type == "image/svg+xml":
                    continue
                for variant in asset.variants.all():
                    variant.file.delete(save=False)
                    variant.delete()
                make_variants(asset)
                if asset.slot == "social":
                    make_sharing_image(asset)
                images += 1
            for revision in theme.revisions.all():
                make_icons(revision.snapshot)
                icons += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Remade the copies of {images} images and checked {icons} revisions' icons."
            )
        )
