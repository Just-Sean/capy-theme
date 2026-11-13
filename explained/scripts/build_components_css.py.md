# scripts/build_components_css.py

**What it does:** builds `components.css`, the stylesheet for the live editor's Components view, with Tailwind and daisyUI.

**How:**

- Runs the Tailwind program the demo downloaded (in `demo/.django_tailwind_cli/`) on `scripts/components.tailwind.css`.
- Only the Components view's templates are scanned, so the output holds just the classes they use.
- Uses the demo's `daisyui.mjs`.

The output is committed, so projects using capy-theme don't need Tailwind for the Components view to work.

**Run:** `uv run python scripts/build_components_css.py` after changing the Components view's templates or updating daisyUI. If the Tailwind program isn't downloaded yet, first run `uv run python demo/manage.py tailwind build`.
