# src/capy_theme/static/capy_theme/editor/editor.css

**What it is:** the panel's look, about 200 lines of plain CSS.

- It's a fixed panel on the right, 24 rem wide, above everything else.
- It sets its own fonts and colors, so the page's theme never changes the panel.
- The banner, the controls and the file chooser all share the same button style (#223).
- **The page makes room:** with `capy-editor-open` on `<html>`, the page moves down below the banner and, in windows at least 48 rem (768 px) wide, left of the panel. That keeps the page's own controls usable. On narrow screens the panel covers the page.
- Visible focus outlines, and a Components view iframe area.
