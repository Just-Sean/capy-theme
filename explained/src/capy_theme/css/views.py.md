# src/capy_theme/css/views.py

**What it is:** the two public views that serve CSS.

- **`theme_css`** (`/theme/<version>.css`): the revision's stylesheet, made on request by `render_css`.
- **`custom_css_file`** (`/theme/custom/<version>.css`): the revision's custom CSS. It's a 404 if there's none or it's off.

Each URL names one revision, so its content never changes. Both are sent with `Cache-Control: public, max-age=<one year>, immutable`, so browsers and CDNs cache them for good. Publishing makes a new URL.
