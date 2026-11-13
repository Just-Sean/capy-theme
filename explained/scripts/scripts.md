# scripts/

Helper scripts you run by hand, from the repo root, to regenerate files the app ships with. They aren't part of the installed package, and the app never runs them. Each one's command is in the README.

| Script | Regenerates | When |
| --- | --- | --- |
| `generate_builtin_themes.py` | `src/capy_theme/themes/builtin_themes.json` | After updating daisyUI |
| `build_components_css.py` (+ `components.tailwind.css`) | `src/capy_theme/static/capy_theme/editor/components.css` | After changing the Components view's templates, or updating daisyUI |
| `fetch_curated_fonts.py` | The 30 bundled fonts and `src/capy_theme/fonts/curated.json` | After changing the font list |
