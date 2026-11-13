# src/capy_theme/editor/components_view.py

**What it is:** the **Components view**, a page showing every daisyUI component and the theme's images in the draft, light and dark side by side. It's shown in an iframe next to the editor panel.

- **`editor_components`** (`editor/<id>/components/`):
  - renders `templates/capy_theme/editor/components.html`
  - takes the editor's **unsaved** values (`?changes=<JSON>`), so image and icon choices show before saving
  - shows which domain's theme it is
  - includes the custom CSS: the draft's for people allowed to edit it, the published one for others
  - staff only, and only the same site may frame it (clickjacking protection)
- **`editor_icon_preview`** (`editor/<id>/icon-preview.png`): the icon as it would look with the draft's background and padding, made on the fly. The real icon files are only made at publish.

Its own stylesheet (`components.css`) keeps daisyUI from touching the page being edited.
