# src/capy_theme/admin/form_colors.py

**What it is:** the form's color fields: 20 colors × light and dark, each a `ColorField`.

- **Blank fields** show the base color grayed out as a placeholder.
- **Each field's help** shows its pair's contrast, e.g. "Primary / Primary text: 4.7:1, passes AA".
- **`clean`** stores only the colors you set, as OKLCH.
- **`color_fieldsets()`** makes the Basic, Advanced and Expert sections per mode.
