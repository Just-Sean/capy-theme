# src/capy_theme/images/svg.py

**What it is:** **SVG sanitizing.** An SVG is code: it can carry scripts, event handlers (`onload=`), links to other sites and embedded HTML. `clean_svg(data)` keeps only what's needed to draw.

1. It must be UTF-8.
2. Any `DOCTYPE` or `ENTITY` is refused. Entities can expand to enormous sizes ("XML bombs") or read local files.
3. It's parsed with **defusedxml**, which also refuses entities and external references, as a second layer.
4. The root must be `<svg>`, with at most 20,000 elements.
5. **Allow-list cleaning** (`svg_allowlist.json`):
   - elements not listed are removed with everything inside them
   - some (like links) are "unwrapped": removed but their drawing kept
   - attributes not listed are removed
   - `href`s may only point inside the SVG or be embedded raster images
   - CSS with `@import`, external `url()` or `expression` is removed
6. A missing `xmlns` is added, and the width and height are read from the viewBox.

The result can only draw shapes, text, gradients and filters.
