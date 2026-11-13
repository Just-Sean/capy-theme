# src/capy_theme/admin/theme_admin.py

**What it is:** `ThemeAdmin`, the theme list and the theme edit page. It combines the Import/Export and Publish-pages mixins.

- **The list's columns:** name, slug, light and dark base, whether it's active, offered to visitors, live revision number, unpublished changes, "Base changed in daisyUI", and last updated. It can be filtered by base and searched by name or slug.
- **The Activate action** (needs `publish_theme`): makes the chosen published theme the site's theme.
- **The edit page:**
  - **Edit live** opens it in the live editor
  - buttons for Revisions, Export and Publish
  - the **Contrast** table (every color pair's rating in light and dark)
  - the publish status (live revision and whether the draft differs)
  - the read-only stored settings as JSON (with custom CSS hidden from people who can't edit it)
  - notes when daisyUI changed a base
- **`get_form`** tells the form whether this user may edit custom CSS. **`get_fieldsets`** leaves the custom CSS section out for people who can't edit it.
