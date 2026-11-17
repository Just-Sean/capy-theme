# src/capy_theme/static/capy_theme/editor/controls/page-images.js

**What it is:** shows the draft's logos and icon on the page while the editor is open (#271).

- **Logos:** `{% theme_logo %}` marks each logo for editors with `data-capy-logo-slot` (and the attributes the template gave it). This script swaps them for the draft's, in light and dark. Where the draft has no logo, it shows the site name.
- **Only safe attributes are copied:** a page could hold a forged marker (e.g. in content its users wrote), so only `<img>`, `<picture>` and `<span>` markers for a real logo slot count, and only `class`, `id`, `title`, `aria-*` and `data-*` attributes with text values are copied onto the draft's logo. Event handlers, `style`, `src` and the rest are ignored. Nodes are built, never parsed from HTML.
- **Only while the editor is shown:** a preview that arrives after closing is ignored.
- **Icon:** it points the browser tab icon at the draft's icon, adding an icon link if the page has none.
- **When:** on load and after every preview (from the `page_images` the server sends).
- **Closing the editor** puts the published logos and icon back.

No reload and nothing saved. Visitors never see it.
