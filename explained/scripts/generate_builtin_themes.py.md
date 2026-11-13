# scripts/generate_builtin_themes.py

**What it does:** builds `src/capy_theme/themes/builtin_themes.json`, the values of all of daisyUI's built-in themes (light, dark, cupcake, ...), which capy-theme uses as base themes.

**How:**

1. Downloads the published daisyUI package (pinned `DAISYUI_VERSION = "5.7.50"`) from the npm registry. Python only; no Node.js needed.
2. Reads two data files from it: `theme/object.js` (every theme's values) and `functions/themeOrder.js` (daisyUI's listing order).
3. Writes the JSON with each theme's name, whether it's light or dark, and all its variables.
4. Warns if the demo's `daisyui.mjs` is a different version, so the catalog matches what the demo shows.

**Run:** `uv run python scripts/generate_builtin_themes.py` after changing `DAISYUI_VERSION`. It's step 2 of "Updating daisyUI" in `docs/development.md`.
