# src/capy_theme/editor/custom_css_view.py

**What it is:** the draft's custom CSS for the Components view.

- **`editor_custom_css`** (`editor/<id>/custom.css`): serves the **draft's** custom CSS, only to editors (active staff who can edit themes, like every editor address) who may also edit custom CSS, because the draft isn't public (#275).
- **`selectors(css)`:** the selectors the CSS styles (e.g. `.hero`, `h1`), up to 50. The Components view lists them, so you can see what the custom CSS affects.
