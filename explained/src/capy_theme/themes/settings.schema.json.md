# src/capy_theme/themes/settings.schema.json

**What it is:** a standard JSON Schema (draft 2020-12) describing **everything a theme's `settings` may contain**. Keys it doesn't list are rejected, so bad or unexpected data can never be saved.

**Top-level keys:**

- **Branding:** `site_name`, `tagline`, `logo_alt`.
- **Mode:** `default_mode` (auto/light/dark) and `visitors_can_switch`.
- **`colors`:** light and dark, each with the 20 daisyUI color names.
- **`shape`:** radii, sizes, border, depth, noise, with min/max limits.
- **`fonts`:** a font ID per role.
- **`type`:** base size, heading scale, line height, heading weight.
- **`images`:** the chosen image ID per slot and mode.
- **`logo`:** header logo heights.
- **`icon`:** the icon's background and padding.
- **`custom_css`:** the CSS and whether it's on.

**When you'd touch it:** every new setting must be added here, with a test, in the same change. No database migration is needed, because settings is one JSON column.
