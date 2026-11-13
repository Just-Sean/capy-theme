# src/capy_theme/themes/models/theme.py

**What it is:** the `Theme` model, a theme's **draft**.

**Fields:**

- `name`, `slug`: admin labels. Renaming needs no publish.
- `light_base`, `dark_base`: the names of built-in daisyUI themes to start from. They're checked in `clean()` rather than stored as fixed choices, because the allowed list depends on a setting.
- `settings`: a JSON field holding **every override** (colors, shape, fonts, type, images, branding, mode, custom CSS). It's validated against `settings.schema.json` on every save.
- `offered_to_visitors`: whether visitors can pick it in the theme picker.
- `live_revision`: the published revision pages use. Only publishing changes it.
- `public_id`, `created_at`, `updated_at`.

**The three extra permissions** are defined here: `publish_theme`, `edit_custom_css`, `import_theme`.

**Important behavior:**

- **`save()`:**
  - validates settings even when called from code, not just forms
  - **never overwrites `live_revision`** in an ordinary save, so a stale copy can't undo someone's publish
- **`clean()`:**
  - chosen fonts must exist in the library
  - chosen images must be this theme's own, uploaded for that slot
  - the bases must be allowed
- **`snapshot()`:** the draft's whole look as a dict, which is what a revision stores:
  - the bases **and their full daisyUI values**, so a later daisyUI update can't change a published theme
  - the settings
  - details of the chosen images and fonts
- **`base_changes()`:** notes for the admin when daisyUI has changed or removed a published theme's base.
- **`has_unpublished_changes`:** whether the draft differs from the live revision.
