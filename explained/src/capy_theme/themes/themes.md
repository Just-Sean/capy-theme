# src/capy_theme/themes/

**The heart of the app:** what a theme is, how it's published, and which theme a page shows.

**The key idea:** a `Theme` row is the **draft**. Editing changes only the draft. **Publishing** copies the draft's whole look into a frozen, numbered `ThemeRevision`, and pages always use the theme's live revision. The live theme is chosen by **assignments**: a default, per-domain ones, and scheduled ones. A visitor may override it with an offered theme.

| File | Job |
| --- | --- |
| `models/` | The Theme, ThemeRevision and assignment models |
| `catalog.py` + `builtin_themes.json` | daisyUI's built-in themes, the bases a theme starts from |
| `validation.py` + `settings.schema.json` | Checking a theme's settings against a JSON Schema |
| `publishing.py` | `publish()`: draft → new live revision |
| `history.py` | Comparing two revisions; restoring an old one |
| `active.py` | Which theme is live for a request, cached |
| `mode.py` | Light / dark / auto: the cookie, the head script, browser-color tags |
| `branding.py` | The published site name, tagline and logo |
| `views.py` | The two visitor URLs: set mode, choose theme |
| `signals.py` | Clear the cache when themes change |
