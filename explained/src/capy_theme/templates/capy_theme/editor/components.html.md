# src/capy_theme/templates/capy_theme/editor/components.html

**What it is:** the **Components view** page, shown in an iframe beside the editor panel. It's a full HTML page with its own `components.css` (daisyUI), so it can't affect the page being edited.

- A line at the top says which domain's theme it shows.
- **Two columns** forced into light and dark with `data-theme="capy-light"` / `"capy-dark"`, each including every sample template in `components/` with `mode` set.
- The editor injects the draft's CSS into it on every change (`controls/components.js`).
- Any custom CSS is linked, with the selectors it styles listed.
