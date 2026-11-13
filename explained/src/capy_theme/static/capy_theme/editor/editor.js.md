# src/capy_theme/static/capy_theme/editor/editor.js

**What it is:** the editor's shell, about 240 lines. It sets up `window.capyEditor`, which the section scripts use.

- **The corner button:** an "Edit theme" button, unless `CAPY_THEME_EDITOR_BUTTON` is off. Any element with `data-capy-editor-open` also opens the editor.
- **`open()`:**
  - builds the **banner** ("Previewing the draft... Only you see it", with Exit) and the **panel**
  - adds `capy-editor-open` to `<html>` so the page makes room
  - loads the draft from the `state` URL
  - fires `capy-editor:loaded` for the sections
- **`preview(changes)`:** POSTs the unsaved values to `preview/`, then puts the returned CSS into a **constructed stylesheet** added after the page's own, so the draft wins. That works under a strict CSP. It also links any external font stylesheets and fires `capy-editor:preview`.
- **`schedulePreview()`:** waits until changes pause (e.g. while dragging a color picker), so the server gets one request instead of dozens.
- **`post(url, data)`:** JSON POST with the CSRF token. It rejects with the server's error messages.
- **`status()`:** messages in a live region, so screen readers announce them.
- **`close()`:** asks first if there are unsaved changes, then removes the draft CSS so the page goes back to the published look. A `beforeunload` warning covers leaving the page.
- **`?edit=<id>`** in the URL opens it straight away.
