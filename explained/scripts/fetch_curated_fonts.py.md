# scripts/fetch_curated_fonts.py

**What it does:** downloads the 30 bundled open-license fonts from Fontsource and stores them in the app.

**How:**

1. The list of fonts (`CURATED`) is in the script: each font's Fontsource package and pinned version, and its fallback stack (sans, serif or mono).
2. For each font it downloads the npm package and keeps only the Latin regular (400), bold (700) and italic WOFF2 files that exist, plus the license.
3. It writes:
   - the files to `src/capy_theme/static/capy_theme/fonts/<font>/`
   - the list `src/capy_theme/fonts/curated.json`, which the `capy_theme_add_fonts` command reads to add them to a project's font library

**Run:** `uv run python scripts/fetch_curated_fonts.py` after changing the list. All 30 are under the SIL Open Font License 1.1.
