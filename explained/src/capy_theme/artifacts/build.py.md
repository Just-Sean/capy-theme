# src/capy_theme/artifacts/build.py

**What it is:** **`get_artifacts(request=None)`**. Everything the active theme's **published** revision produces, as plain data, or None if nothing is published. With a request, every URL is absolute (needed for emails and manifests).

| Key | Contents |
| --- | --- |
| `theme` | name, slug, revision |
| `branding` | site name, tagline, logo alt |
| `colors`, `colors_hex` | the 20 colors per mode, as OKLCH and hex |
| `fonts` | per role: family, CSS stack, source, files |
| `shape`, `type` | shape values per mode; type scale |
| `logos` | all six slots, light and dark, after fallbacks, with smaller copies |
| `icons` | every icon file's URL |
| `sharing_image` | URL, size and alt, or None |
| `backgrounds` | login and pattern, light and dark |
| `mode`, `stylesheet_url` | the mode settings; the theme stylesheet |

The JSON API, the design tokens and `{% theme_artifacts %}` are all built from this, so they always agree.
