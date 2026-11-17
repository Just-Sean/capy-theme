# src/capy_theme/admin/theme_admin.py

**What it is:** `ThemeAdmin`, the theme list and the theme edit page. It combines the Import/Export, Publish-pages and Save-and-publish mixins.

- **The list's columns:** name, slug, light and dark base, "Showing now" (whether it's the theme the site shows right now: the default, or a scheduled one), offered to visitors, live revision number, unpublished changes, "Base changed in daisyUI", and last updated. It can be filtered by base and searched by name or slug.
- **Publish, Publish and activate, and Activate** buttons on each row, for users who may publish (from `save_publish.py`, #273).
- **The edit page:**
  - **Edit live** opens it in the live editor, on the live edit page (`/theme/live-edit/?edit=<id>`)
  - buttons for Revisions and Export
  - the **Save and publish** area at the bottom (`save_publish.py`): a status line, Save draft, Save and publish, and Save, publish and activate
  - the **Contrast** table (every color pair's rating in light and dark)
  - the publish status (live revision and whether the draft differs)
  - the read-only stored settings as JSON (with custom CSS hidden from people who can't edit it)
  - notes when daisyUI changed a base
- **`change_view`** hands the template the **Edit live** link.
- **`render_change_form`** hands the template the Save and publish area's context (`save_publish_context`, for the theme Django already loaded, or none on the add page) and the page's tabs (`tabs.theme_tabs`). When the page is shown again after a failed save, it first asks each slot that had a new file to choose it again (`form_images.ask_to_choose_again`), whatever the error was.
- **`save_model`** saves the theme, then `form_images.save_images` stores new uploads and chooses them (they need the saved theme, #271).
- **`get_form`** tells the form whether this user may edit custom CSS. **`get_fieldsets`** leaves the custom CSS section out for people who can't edit it.
