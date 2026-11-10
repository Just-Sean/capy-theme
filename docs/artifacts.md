# Theme artifacts for other apps

Code: `src/capy_theme/artifacts/`.

## Theme artifacts for other modules

capy-theme owns the theme but only applies it to the page's own look (the
stylesheet, the logo tag, the tab icon). Everything else it produces is made
available for other parts of the project, e.g. an email module, an app shell,
or something that builds a web app manifest or link-preview tags:

```python
from capy_theme.artifacts import get_artifacts

artifacts = get_artifacts(request)  # None if no theme is published
artifacts["logos"]["logo_email"]["light"]["url"]  # every logo slot, light and dark
artifacts["colors_hex"]["light"]["primary"]  # also "colors" (OKLCH)
artifacts["icons"]["icon-512.png"]  # every generated icon
artifacts["sharing_image"]  # url, width, height, alt
```

In templates: `{% theme_artifacts as artifacts %}`, then e.g.
`{{ artifacts.logos.logo_email.light.url }}`.

What's in it (all from the published revision; with a request, URLs are absolute):

| Key | Contents |
| --- | --- |
| `theme` | `name`, `slug`, `revision` |
| `branding` | `site_name`, `tagline`, `logo_alt` |
| `colors`, `colors_hex` | The 20 colours per mode (`light`, `dark`), as OKLCH and as `#rrggbb` |
| `fonts` | Per role the theme sets: `family`, `stack` (CSS `font-family`), `source` |
| `logos` | The six logo slots, `light` and `dark`, after fallbacks: `url`, `width`, `height`, `alt`, `content_type`, `variants` (smaller copies: `url`, `width`, `format`) |
| `icons` | File name → URL: `favicon.ico`, `favicon.svg`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `icon-monochrome-512.png` |
| `sharing_image` | `url`, `width`, `height`, `alt` (1200 × 630), or `None` |
| `backgrounds` | `login` and `pattern`, each `light` and `dark` URL (or `None`) |
| `mode` | `default`, `visitors_can_switch` |
| `stylesheet_url` | The theme stylesheet |

## The JSON API

`/theme/api.json` (under wherever the project includes `capy_theme.urls`) serves
the same data as `get_artifacts()`, with absolute URLs, for React, Vue and other
front ends, mobile apps and other services. It's public and read-only.

- **Caching:** every response has an `ETag`. Send it back in `If-None-Match` and
  you get `304 Not Modified` until the theme is published again. Responses may
  be cached for 60 seconds (`Cache-Control: public, max-age=60`).
- **No published theme:** `404` with `{"error": "No theme is published."}`.
- **Other domains:** browsers only let apps on other domains read it if the
  project allows it with CORS (for example with `django-cors-headers` in the
  project's settings). capy-theme doesn't set CORS headers itself.

```js
const response = await fetch("https://example.com/theme/api.json");
const theme = await response.json();
document.title = theme.branding.site_name;
const logo = theme.logos.logo_main.light;   // { url, width, height, alt, variants }
```

### Django REST Framework and generated API docs (`CAPY_THEME_API`)

> **Note for projects:** how the API is served depends on whether the project
> uses Django REST Framework (DRF), and capy-theme decides this **by itself**
> when the project starts. Set `CAPY_THEME_API` to choose explicitly.

| `CAPY_THEME_API` | What serves `/theme/api.json` |
| --- | --- |
| `"auto"` (default) | A DRF view if `rest_framework` is in `INSTALLED_APPS`, otherwise a plain Django view |
| `"drf"` | Always the DRF view (an error at start-up if DRF isn't installed) |
| `"django"` | Always the plain Django view, even in a DRF project |

- **With DRF and drf-spectacular** set up in the project, the endpoint appears in
  the project's generated API docs (schema, Swagger or Redoc) automatically,
  with its full response described. Nothing else to configure.
- **The DRF view sets its own rules** (no login, no throttling, JSON only), so the
  project's DRF defaults, such as requiring login, don't change this public API.
- **Both views return exactly the same JSON** and the same ETag.
- capy-theme never requires DRF or drf-spectacular; they're only used when the
  project has them.

Upgrading from 0.5: migration `0011_remove_app_and_social_settings` removes the
web app manifest and link-preview settings from 0.5.0 (the manifest view and
the tags are gone; the icons and sharing image stay).

Upgrading from 0.4: migration `0010_logo_slots` moves each theme's old logo into
its main slot (light). It has no smaller copies; upload it again to get them.
Revisions published before 0.5 keep showing their old logo.

The "Overrides" section shows the theme's stored `settings` as read-only JSON.
They're edited through the fields above, not typed by hand.

## Design tokens

`/theme/tokens.json` downloads the published theme in the W3C
[Design Tokens Format Module 2025.10](https://www.designtokens.org/TR/2025.10/format/),
for design tools (Figma, Tokens Studio, Style Dictionary) and native app builds.
It's made from the same data as the JSON API. File name `<theme slug>.tokens.json`,
media type `application/design-tokens+json`.

- `light` and `dark` groups: `color` (all 20, as OKLCH components with a 6-digit
  `hex` fallback; colourless greys have hue `"none"`) and `shape` (radii and sizes
  as `rem`/`px` dimensions, depth and noise as numbers).
- `font`: a `fontFamily` token per role the theme sets (the stack as a list).
- `type`: base size, heading scale, line height and heading weight, if set.

Every token states its `$type`. The tests validate the download against the
format's official JSON Schema (`tests/artifacts/dtcg/`).

## daisyUI theme blocks

`/theme/daisyui-theme.css` downloads the published theme as two daisyUI theme
blocks, for projects that compile the theme into their own Tailwind stylesheet
instead of loading capy-theme's: `<slug>-light` (the default) and `<slug>-dark`
(used when the device prefers dark). Paste it into your Tailwind source after the
daisyUI plugin:

```css
@import "tailwindcss";
@plugin "daisyui";
/* the downloaded blocks: */
@plugin "daisyui/theme" { name: "main-light"; default: true; ... }
@plugin "daisyui/theme" { name: "main-dark"; prefersdark: true; ... }
```

With daisyUI's standalone plugin files (no npm), change `"daisyui/theme"` to the
path of your `daisyui-theme.mjs`. The blocks carry daisyUI's own variables only
(colours, radii, sizes, border, depth, noise); fonts, the type scale, logos and
the other extras need `{% theme_head %}` or the API. The download is a snapshot:
download it again after publishing changes.

