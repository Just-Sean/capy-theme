# demo/static/css/tailwind.css

**What it is:** the demo's compiled stylesheet (about 580 KB). It's built, not written: `uv run python demo/manage.py tailwind build`, or automatically while `tailwind runserver` is running. It's git-ignored.

**What's in it:**

- Tailwind's utility classes used by the demo's templates and capy-theme's templates (as `tailwind/source.css` tells it to scan)
- all of daisyUI's components and its built-in themes

The demo's base template loads it with `{% tailwind_css %}`.

**How capy-theme relates to it:** this file supplies daisyUI's components and default colors. capy-theme's own stylesheet (`/theme/<version>.css`, from `{% theme_head %}`) loads after it and overrides daisyUI's CSS variables (colors, radii, sizes, fonts) with the published theme's values. So the published theme wins without rebuilding this file.
