"""manage.py theme_publish <slug> [--note TEXT] [--activate]: publish a theme's draft."""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from ...models import Theme
from ...themes.active import NotPublished
from ...themes.active import activate as make_active
from ...themes.publishing import NothingToPublish
from ...themes.publishing import publish as publish_theme


class Command(BaseCommand):
    help = "Publish a theme's draft as a new revision (and optionally make it the site's theme)."

    def add_arguments(self, parser):
        parser.add_argument("slug", help="The theme's slug.")
        parser.add_argument("--note", default="", help="A note for the history.")
        parser.add_argument("--activate", action="store_true", help="Make it the site's theme.")

    def handle(self, slug, note="", activate=False, **options):
        theme = Theme.objects.select_related("live_revision").filter(slug=slug).first()
        if theme is None:
            raise CommandError(f"No theme with the slug {slug!r}.")
        try:
            revision = publish_theme(theme, note=note)
            self.stdout.write(
                self.style.SUCCESS(f"Published “{theme}” as revision {revision.number}.")
            )
        except NothingToPublish as error:
            self.stdout.write(str(error))
        except ValidationError as error:
            raise CommandError("Can't publish: " + " ".join(error.messages)) from error
        if activate:
            theme.refresh_from_db()
            try:
                make_active(theme)
            except NotPublished as error:
                raise CommandError(str(error)) from error
            self.stdout.write(f"“{theme}” is now the site's theme.")
