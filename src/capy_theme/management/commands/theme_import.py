"""manage.py theme_import FILE [--publish] [--activate]: import an export zip."""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from ...portability.importing import import_theme
from ...themes.active import activate as make_active
from ...themes.publishing import publish as publish_theme


class Command(BaseCommand):
    help = "Import a theme exported by capy-theme. It arrives as an unpublished draft."

    def add_arguments(self, parser):
        parser.add_argument("file", help="The export zip.")
        parser.add_argument("--publish", action="store_true", help="Publish it after importing.")
        parser.add_argument(
            "--activate", action="store_true", help="Publish it and make it the site's theme."
        )

    def handle(self, file, publish=False, activate=False, **options):
        try:
            with open(file, "rb") as handle:
                theme = import_theme(handle)
        except OSError as error:
            raise CommandError(f"Can't read {file}: {error}") from error
        except ValidationError as error:
            raise CommandError("Not imported: " + " ".join(error.messages)) from error
        self.stdout.write(self.style.SUCCESS(f"Imported “{theme}” (slug {theme.slug}) as a draft."))
        if publish or activate:
            _publish_and_activate(self, theme, activate)


def _publish_and_activate(command, theme, also_activate):
    revision = publish_theme(theme, note="Published from the command line")
    command.stdout.write(f"Published revision {revision.number}.")
    if also_activate:
        make_active(theme)
        command.stdout.write(f"“{theme}” is now the site's theme.")
