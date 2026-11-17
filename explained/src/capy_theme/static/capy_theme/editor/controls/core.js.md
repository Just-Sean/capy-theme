# src/capy_theme/static/capy_theme/editor/controls/core.js

**What it is:** the shared base for the section scripts (`editor.ui`).

- **State:**
  - `changes`: the unsaved values
  - `baseline`: the values as last saved, to tell whether anything changed
  - `spec`: what the panel offers
  - `latest`: the latest server values
  - `assets`: the theme's uploaded images (`image-slot.js` adds new uploads)
  - `changes.alts`: edited alt text, `{image id: text}`, saved with the draft (#271)
  - the current color tab
- **`ui.el()`:** a small helper to create elements.
- **`ui.section(title, children)`:** a section that folds (its title is a heading inside `<summary>`), folded to start with.
- **`ui.update()`:** previews the changes and updates the "Unsaved changes" note.
- **`ui.build(state)`:** (re)builds the whole panel from the server's state, section by section in order. Every fold (`data-capy-fold`) stays open or folded as you left it, after Save draft, Publish or Revert.
- **`ui.fill()`:** shows the latest values in every section.

It listens for `capy-editor:loaded` and `capy-editor:preview`.
