# scripts/build_components_css.py

**What it does:** builds `components.css`, the stylesheet for the live editor's Components view and for the live edit page (`/theme/live-edit/`), with Tailwind and daisyUI.

**How:**

- Runs the Tailwind program the demo downloaded (in `demo/.django_tailwind_cli/`) on `scripts/components.tailwind.css`.
- Only those pages' templates are scanned, plus the mode toggle and the theme picker. So the output holds just the classes they use.
- Uses the demo's `daisyui.mjs`.

The output is committed, so projects using capy-theme don't need Tailwind for either page to work.

**Run:** `uv run python scripts/build_components_css.py` after changing those templates or updating daisyUI. If the Tailwind program isn't downloaded yet, first run `uv run python demo/manage.py tailwind build`.
