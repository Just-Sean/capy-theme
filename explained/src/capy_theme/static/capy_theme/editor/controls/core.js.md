# src/capy_theme/static/capy_theme/editor/controls/core.js

**What it is:** the shared base for the section scripts (`editor.ui`).

- **State:**
  - `changes`: the unsaved values
  - `baseline`: the values as last saved, to tell whether anything changed
  - `spec`: what the panel offers
  - `latest`: the latest server values
  - the current color tab
- **`ui.el()`:** a small helper to create elements.
- **`ui.update()`:** previews the changes and updates the "Unsaved changes" note.
- **`ui.build(state)`:** (re)builds the whole panel from the server's state, section by section in order.
- **`ui.fill()`:** shows the latest values in every section.

It listens for `capy-editor:loaded` and `capy-editor:preview`.
