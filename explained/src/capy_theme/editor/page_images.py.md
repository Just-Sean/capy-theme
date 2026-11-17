# src/capy_theme/editor/page_images.py

**What it is:** the draft's logos and icon, so the live editor can show them on the page before publishing (#271).

**`page_images(snapshot)`** returns:

- **`logos`:** for every logo slot, the light image and the dark one (or none if it's the same), each with its URL, alt text, width and height. It follows the same fallbacks as the published logos (e.g. an empty slot uses the main logo).
- **`site_name`:** shown where there's no logo.
- **`icon`:** the light and dark icon URLs.

`preview.py` adds it to every preview. `static/capy_theme/editor/controls/page-images.js` puts it on the page, in the editing user's browser only.
