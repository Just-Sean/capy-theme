# src/capy_theme/css/typography.py

**What it is:** the type scale, read from `type_settings.json`.

- **`TYPE_SETTINGS`:** base text size, heading scale, line height and heading weight, each with label, unit, min, max, step and help.
- **`heading_sizes(scale)`:** h6 is 1 rem and each level up multiplies by the scale.
- **`type_css(settings)`:** CSS variables (`--capy-base-size`, `--capy-h1`...`h6`, `--capy-line-height`, `--capy-heading-weight`) plus default rules in `@layer base`, so a project's own utility classes (like `text-5xl`) still win. Unset values output nothing, leaving the project's own styles alone.
