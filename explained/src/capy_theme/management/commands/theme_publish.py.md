# src/capy_theme/management/commands/theme_publish.py

**`manage.py theme_publish <slug> [--note TEXT] [--activate]`** publishes a theme's draft (`publish`), optionally with a note, and optionally makes it the site's theme.

- **Nothing to publish** (the draft matches the live revision): it prints that as a plain message and carries on. With `--activate` it still activates the theme.
- **Invalid draft or unknown slug:** these are real errors (`CommandError`) and stop the command.
