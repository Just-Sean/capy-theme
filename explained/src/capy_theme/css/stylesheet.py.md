# src/capy_theme/css/stylesheet.py

**What it is:** builds the theme stylesheet.

- **`snapshot_css(snapshot)`:** the full CSS for a theme's look. It's used for published revisions and, in the editor, for unsaved drafts, so the preview always matches what would be published. In order:
  1. `:root { ... }` with the **light** values: colors, shape, background images, `--capy-focus`, `color-scheme`.
  2. The **dark** values inside `@media (prefers-color-scheme: dark)`.
  3. `[data-theme="capy-light"]` / `[data-theme="capy-dark"]` blocks that force a mode. The mode toggle and the Components view's side-by-side samples use these.
  4. A visible keyboard focus outline.
  5. Font faces and roles, the type scale, logo heights, background classes, accessibility rules.

  The variable rules aren't in a CSS layer, so they beat daisyUI's own theme values.
- **`render_css(revision)`:** the same for a revision, with a comment naming it.
- **`css_version(...)`:** the 12-character hash that names a revision's stylesheet. It must stay in step with migration 0004.
- **`stylesheet_url(revision)`:** `/theme/<hash>.css?v=<capy-theme version>`. The `?v=` makes browsers fetch again after a capy-theme upgrade changes how CSS is written.
