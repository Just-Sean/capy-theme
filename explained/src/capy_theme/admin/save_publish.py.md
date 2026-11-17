# src/capy_theme/admin/save_publish.py

**What it is:** `SavePublishMixin`, the one place to save, publish and activate a theme (#273). `ThemeAdmin` uses it. Publishing and activating need `publish_theme`. Activating makes a theme the **default theme**: the one every site uses unless a theme schedule is running or a domain has its own site theme.

- **The theme page's three buttons** (in `save_publish.html`):
  - **Save draft:** saves and stays on the page; nothing is published. If a note was typed, the message says it wasn't kept (notes are only kept when you publish).
  - **Save and publish:** saves, then publishes the draft.
  - **Save, publish and activate:** the same, then makes it the default theme.
  - `response_add` and `response_change` handle them after Django saves the form, then go back to the theme page. Without `publish_theme`, the draft is saved and a message says publishing was refused.
  - In a popup, or for a user who can't open the theme page (say, one who may only add), Django answers as usual instead, so a popup closes and fills in the field it was opened from.
  - An optional note for the history (at most `NOTE_MAX`, 2,000 characters, from `themes/publishing.py`).
- **`publish_status(theme)`:** the page's status line: whether the draft has unpublished changes, the published revision, and whether it's the default theme (or which one is). While a theme schedule is running, a **Showing now** item says which theme the site shows instead.
- **`activated_message(theme)`:** what activating did. Normally "“x” is now the default theme." (a success); a warning when a running schedule is showing another theme right now.
- **`run_publish(request, theme, activate_too)`:** publishes (or publishes and activates) and says what happened in a message: nothing to publish, an invalid draft, someone else publishing at the same moment, or success (with `activated_message` when activating).
- **`save_publish_context(request, theme)`:** what the template needs: the status line, whether it's the default theme, the note's limit, the note as typed (so it's kept when the page comes back with errors), and `can_publish`.
- **The theme list's row buttons:** **Publish** and **Publish and activate** (when the draft has unpublished changes) and **Activate** (when it's published but not the default theme; it uses the last published version). They're a column, "Publish or activate", shown only to users who may publish.
  - Each button has a `data-capy-confirm` question, so `admin/confirm.js` asks before it goes ahead.
  - Each one posts to its own view (`<id>/publish-now/`, `<id>/publish-and-activate/`, `<id>/activate/`), which accepts only POST.
  - The theme is found with Django's `get_object`, so a missing or malformed id (e.g. `abc`) is a 404, not a server error.
  - Afterward it goes back to the list as it was (filters, search, page) when the browser's Referer is the theme list on this site; otherwise to the plain list.
  - The buttons use the list's own form, so they carry its CSRF token.
- Whether a theme is the default comes from `active.default_theme()`, not the theme showing now, so a scheduled theme doesn't hide the activate buttons.
