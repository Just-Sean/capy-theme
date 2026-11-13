# src/capy_theme/artifacts/downloads.py

**What it is:** two public downloads of the published theme.

- **`design_tokens`** (`/theme/tokens.json`): the W3C design tokens file, named `<slug>.tokens.json`, with the media type `application/design-tokens+json`.
- **`daisyui_theme`** (`/theme/daisyui-theme.css`): the daisyUI theme blocks, named `<slug>.daisyui-theme.css`.

Both are a 404 if nothing is published, and cacheable for 60 seconds.
