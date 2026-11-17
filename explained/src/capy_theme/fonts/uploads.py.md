# src/capy_theme/fonts/uploads.py

**What it is:** checking and converting font files, for font uploads in the admin, Google Fonts imports and theme imports. (The bundled fonts don't go through it: `capy_theme_add_fonts` copies their ready-made WOFF2 files straight into storage.)

**`prepare(data, name, subset)`:**

1. Refuses files over `CAPY_THEME_FONT_MAX_BYTES` (5 MB by default).
2. Refuses WOFF and WOFF2 files that would unpack past `CAPY_THEME_FONT_MAX_UNPACKED_BYTES` (`unpacking.check()`), before fontTools sees them.
3. **Hands the rest to fontTools in a separate process** with memory and time limits (`converting.py`). There it's parsed (anything that isn't really a font, such as a renamed image or a broken file, is refused), optionally **trimmed** to one character subset (Latin by default in the admin, often cutting it to a few percent of its size; refused if the font has no characters in that set), its weight, italic flag and family name are read, and it's converted to **WOFF2**, the smallest web font format. A font that needs more memory or time than the limits is refused as too complex.

`SUBSETS` and `SUBSET_CHOICES` come from `subsets.json`.
