# src/capy_theme/images/svg_allowlist.json

**What it is:** the allow-list `svg.py` applies to uploaded SVGs.

- **`elements`:** drawing elements that may stay: shapes, paths, text, groups, gradients, patterns, masks, clip paths, filters and filter effects, `image` (embedded data only), and so on.
- **`unwrap`:** elements removed but whose contents are kept.
- **`attributes`:** attributes that may stay: geometry, fill, stroke, transforms, gradient and filter settings, `xlink:href`, and so on.

Anything not listed is removed. That includes `<script>`, `<foreignObject>` (embedded HTML), animation elements and every `on...` event attribute. Making this list longer makes uploads less safe, so change it carefully.
