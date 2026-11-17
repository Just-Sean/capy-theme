# src/capy_theme/admin/save_publish.py

**What it is:** `SavePublishMixin`, the one place to save, publish and activate a theme (#273). `ThemeAdmin` uses it. Publishing and activating need `publish_theme`.

- **The theme page's three buttons** (in `save_publish.html`):
  - **Save draft:** saves and stays on the page; nothing is published.
  - **Save and publish:** saves, then publishes the draft.
  - **Save, publish and activate:** the same, then makes it the site's theme.
  - `response_add` and `response_change` handle them after Django saves the form, then go back to the theme page. Without `publish_theme`, the draft is saved and a message says publishing was refused.
  - An optional note for the history (at most 2,000 characters).
- **`publish_status(theme)`:** the page's status line: whether the draft has unpublished changes, the published revision, and whether it's the site's theme.
- **`run_publish(request, theme, activate_too)`:** publishes (or publishes and activates) and says what happened in a message: nothing to publish, an invalid draft, someone else publishing at the same moment, or success.
- **The theme list's row buttons:** **Publish** and **Publish and activate** (when the draft has unpublished changes) and **Activate** (when it's published but not the site's theme). They're a column shown only to users who may publish.
  - Each one posts to its own view (`<id>/publish-now/`, `<id>/publish-and-activate/`, `<id>/activate/`), which accepts only POST and goes back to the list.
  - The buttons use the list's own form, so they carry its CSRF token.
- **`site_theme_id()`:** the id of the theme active for every site, or None. It hides the activate buttons for the theme that already is.
