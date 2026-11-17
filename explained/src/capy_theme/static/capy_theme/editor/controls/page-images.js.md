# src/capy_theme/static/capy_theme/editor/controls/page-images.js

**What it is:** shows the draft's logos and icon on the page while the editor is open (#271).

- **Logos:** `{% theme_logo %}` marks each logo for editors with `data-capy-logo-slot` (and the attributes the template gave it). This script swaps them for the draft's, in light and dark. Where the draft has no logo, it shows the site name.
- **Icon:** it points the browser tab icon at the draft's icon, adding an icon link if the page has none.
- **When:** on load and after every preview (from the `page_images` the server sends).
- **Closing the editor** puts the published logos and icon back.

No reload and nothing saved. Visitors never see it.
