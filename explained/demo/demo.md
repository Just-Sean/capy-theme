# demo/

**What it is:** a tiny Django project for running capy-theme by hand while it's built. It's development only: not installed with the package, never deployed, and not secure (`DEBUG = True`, a fixed secret key).

It's a stand-in for "any project that uses capy-theme". It installs the app, includes its URLs under `/theme/`, and uses its template tags in a base template, as a real project would. The tests also use it (`tests/test_demo.py`) to check that the demo starts and builds.

**Start it:** `uv run python demo/manage.py tailwind runserver`, then open http://localhost:8000/.

**What's in it:**

| Item | In git? | Purpose |
| --- | --- | --- |
| `manage.py` | yes | Django's command runner for the demo |
| `demo_site/` | yes | The demo's settings, URLs and server entry point |
| `templates/` | yes | The demo's two pages: the base layout and the home page |
| `tailwind/` | yes | The Tailwind source file and the daisyUI plugin files |
| `static/css/` | `.gitkeep` only | Where the built `tailwind.css` goes |
| `db.sqlite3` | no | The demo's database: themes, revisions, users. Delete it and run `migrate` to start fresh. |
| `media/` | no | Files uploaded in the demo: images, icons and fonts, under `media/capy_theme/` |
| `.django_tailwind_cli/` | no | The downloaded Tailwind program (build tool only) |
