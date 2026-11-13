# demo/static/css/

Where Tailwind writes the demo's built stylesheet. Only `.gitkeep` is committed.

**`tailwind.css`** (git-ignored, so it isn't explained file by file):

- **What it is:** the compiled stylesheet, about 580 KB. It holds Tailwind's classes used by the demo's and capy-theme's templates, plus all of daisyUI.
- **How it's made:** `uv run python demo/manage.py tailwind build`, or automatically while `tailwind runserver` runs.
- **How it's loaded:** the demo's base template loads it with `{% tailwind_css %}`.
- **How capy-theme relates to it:** capy-theme's own stylesheet (from `{% theme_head %}`) loads after it and overrides daisyUI's variables with the published theme's values, so the theme applies without rebuilding this file.
