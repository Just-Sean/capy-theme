# src/capy_theme/css/shape.py

**What it is:** daisyUI's shape and effect settings, read from `shape.json`.

- **`SIZES`:** for each size, its CSS variable, unit, min, max, label and help.
- **`SIZE_STEPS`:** how far the number boxes' arrows move each one (#224).
- **`EFFECTS`:** depth and noise (on/off).
- **`shape_values(settings)`:** turns a theme's shape overrides into CSS values, e.g. `--radius-box: 0rem`, `--depth: 0`.

Used by the stylesheet, the admin form, the editor, the revision comparison and the tokens.
