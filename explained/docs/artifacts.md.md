# docs/artifacts.md

**Covers:** how other code gets the theme.

- `get_artifacts()` and `{% theme_artifacts %}`: everything published, as data
- **the JSON API** at `/theme/api.json`, with ETag caching and CORS notes
- `CAPY_THEME_API` (plain Django view or a DRF view that appears in generated API docs)
- **design tokens** in the W3C format, for Figma and similar tools
- **daisyUI theme blocks** for projects that compile the theme into their own Tailwind build

**Code it describes:** `src/capy_theme/artifacts/`.
