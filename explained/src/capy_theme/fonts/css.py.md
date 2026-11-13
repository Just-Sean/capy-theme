# src/capy_theme/fonts/css.py

**What it is:** `font_css(fonts)`, the font part of the theme stylesheet:

- an `@font-face` rule per file, with `font-display: swap` so text shows straight away in a fallback font
- **Body** sets Tailwind's `--font-sans` and the body font
- **mono** sets `--font-mono`
- **headings** and **display** set `--capy-font-heading` / `--capy-font-display`, used by h1–h6 and the `.capy-display` class

The element rules are in `@layer base`, so a project's own classes (like `font-serif`) still win.
