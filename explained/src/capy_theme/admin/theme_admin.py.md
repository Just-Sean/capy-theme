# src/capy_theme/admin/theme_admin.py

**What it is:** `ThemeAdmin`, the theme list and the theme edit page. It combines the Import/Export and Publish-pages mixins.

- **The list's columns:**
  - live revision number
  - unpublished changes
  - whether it's active
  - "Base changed in daisyUI"
  - publish status
- **The Activate action** (needs `publish_theme`): makes the chosen published theme the site's theme.
- **The edit page:**
  - **Edit live** opens it in the live editor
  - buttons for Revisions, Export and Publish
  - the **Contrast** table (every color pair's rating in light and dark)
  - the read-only stored settings as JSON (with custom CSS hidden from people who can't edit it)
  - notes when daisyUI changed a base
- **`get_form`** tells the form whether this user may edit custom CSS. **`get_fieldsets`** leaves the custom CSS section out for people who can't edit it.
