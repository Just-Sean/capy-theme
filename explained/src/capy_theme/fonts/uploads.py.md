# src/capy_theme/fonts/uploads.py

**What it is:** checking and converting font files, for uploads, Google imports, theme imports and the bundled fonts.

**`prepare(data, name, subset)`:**

1. Refuses files over `CAPY_THEME_FONT_MAX_BYTES` (5 MB by default).
2. **Parses it with fontTools.** Anything that isn't really a font (a renamed image, a broken file) is refused.
3. Optionally **trims** it to one character subset (Latin by default in the admin), often cutting it to a few percent of its size. It's refused if the font has no characters in that set.
4. Reads its weight, italic flag and family name from the font's own tables.
5. Converts it to **WOFF2**, the smallest web font format.

`SUBSETS` and `SUBSET_CHOICES` come from `subsets.json`.
