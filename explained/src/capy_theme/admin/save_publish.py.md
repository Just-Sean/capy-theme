# src/capy_theme/admin/save_publish.py

**What it is:** `SavePublishMixin`, the one place to save, publish and activate a theme (#273). `ThemeAdmin` uses it. Publishing and activating need `publish_theme`. Activating makes a theme the **default theme**: the one every site uses unless a theme schedule is running or a domain has its own site theme.

- **The theme page's three buttons** (in `save_publish.html`):
  - **Save draft:** saves and stays on the page; nothing is published. If a note was typed, the message says it wasn't kept (notes are only kept when you publish).
  - **Save and publish:** saves, then publishes the draft.
  - **Save, publish and activate:** the same, then makes it the default theme.
  - `response_add` and `response_change` handle them after Django saves the form (`_after_save`), then go back to the theme page, keeping the list's filters as Django's own "Save and continue editing" does. Without `publish_theme`, the draft is saved and a message says publishing was refused.
  - In a popup, or for a user who can't open the theme page (say, one who may only add), Django answers as usual instead, so a popup closes and fills in the field it was opened from. Then no "Draft saved" message is added, and publishing in a popup only says something if it was refused.
  - An optional note for the history (at most `NOTE_MAX`, 2,000 characters, from `themes/publishing.py`).
- **`publish_status(theme)`:** the page's status line: whether the draft has unpublished changes, the published revision, and whether it's the default theme (or which one is). While a theme schedule is running, a **Showing now** item says which theme the site shows instead.
- **`activated_message(theme)`:** what activating did. Normally "“x” is now the default theme." (a success); a warning when a running schedule is showing another theme right now.
- **`run_publish(request, theme, activate_too, quiet=False)`:** publishes (and activates) and says what happened in messages. In a popup (`quiet`), success isn't said, as Django says nothing for a popup either; a refusal (nothing to publish, an invalid draft, a clash) is still said, so it shows on the next page.
- **`save_publish_context(request, theme)`:** what the template needs: the status line, whether it's the default theme, the note's limit, the note as typed (so it's kept when the page comes back with errors), and `can_publish`. When the page comes back after a failed save, it reloads the theme from the database first, so the status line describes the saved draft, not the unsaved values.
- **The theme list's row buttons:** **Publish** and **Publish and activate** (when the draft has unpublished changes) and **Activate** (when it's published but not the default theme; it uses the last published version). They're a column, "Publish or activate", shown only to users who may publish.
  - Each button has a `data-capy-confirm` question, so `admin/confirm.js` asks before it goes ahead: "Publish “x”? Visitors will see it wherever it's used.", or, for the two that activate, "... make it the default theme? Visitors will see it (unless a theme schedule is running)."
  - Each one posts to its own view (`<id>/publish-now/`, `<id>/publish-and-activate/`, `<id>/activate/`), which accepts only POST.
  - The theme is found with Django's `get_object`, so a missing or malformed id (e.g. `abc`) is a 404, not a server error.
  - Afterward it goes back to the list as it was (filters, search, page) when the browser's Referer is the theme list on this site; otherwise to the plain list. A user who may publish but can't view themes goes to the admin index instead, since they can't open the list.
  - The buttons use the list's own form, so they carry its CSRF token.
- **`get_queryset`** marks each theme with `capy_is_default` (whether it's the default theme) in the list's own query, so the row buttons don't look up the default theme once per row.
- Whether a theme is the default means the theme activated for every site, not the theme showing now, so a scheduled theme doesn't hide the activate buttons.
