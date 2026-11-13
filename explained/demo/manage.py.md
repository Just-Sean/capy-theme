# demo/manage.py

**What it is:** Django's standard command runner, set up for the demo. Every demo command goes through it:

- `uv run python demo/manage.py runserver`, or `... tailwind runserver` to rebuild the CSS too
- `uv run python demo/manage.py migrate` to create or update the demo database
- `uv run python demo/manage.py createsuperuser` for an admin login
- capy-theme's own commands: `theme_export`, `theme_import`, `theme_publish`, `theme_rebuild_images`, `capy_theme_add_fonts`

It only points Django at `demo_site.settings`, then hands the command to Django.
