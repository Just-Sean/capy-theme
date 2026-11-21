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

> **Building a control (a light/dark toggle, a theme picker, a logo)?** capy-theme
> exposes the data for it but renders no widget and applies nothing to the page — the
> app-shell or module builds its own chrome from this data (and the catalog / per-theme
> endpoints below), so the theme never dictates another app's chrome.

What's in it (all from the published revision; with a request, URLs are absolute):

| Key | Contents |
| --- | --- |
| `theme` | `name`, `slug`, `revision` |
| `branding` | `site_name`, `tagline`, `logo_alt` |
| `colors`, `colors_hex` | The 20 colors per mode (`light`, `dark`), as OKLCH and as `#rrggbb` |
| `fonts` | Per role the theme sets: `family`, `stack` (CSS `font-family`), `source`, `stylesheet` (external-font URL, else `""`), `files` (each `url`, `weight`, `style`, `unicode_range`) |
| `logos` | The six logo slots, `light` and `dark`, after fallbacks: `url`, `width`, `height`, `alt`, `content_type`, `variants` (smaller copies: `url`, `width`, `format`) |
| `icons` | File name → URL: `favicon.ico`, `favicon.svg`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `icon-monochrome-512.png` |
| `sharing_image` | `url`, `width`, `height`, `alt` (1200 × 630), or `None` |
| `backgrounds` | `login` and `pattern`, each `light` and `dark` URL (or `None`) |
| `mode` | `default`, `visitors_can_switch` |
| `stylesheet_url` | The theme stylesheet |

## The JSON API

A consumer reads these public, read-only JSON endpoints (under wherever the project
includes `capy_theme.urls`) and does all the using itself — capy-theme decides nothing
for it:

- **`GET /theme/themes.json`** — the catalog of available themes (the ones the admin
  offers to visitors, plus the default). Each entry:

  | Field | Contents |
  | --- | --- |
  | `slug`, `name` | The theme's slug and display name |
  | `default` | `true` for the admin's default theme |
  | `light`, `dark` | Each `{ "base": <daisyUI base>, "swatch": <primary #rrggbb>, "background": <base-100 #rrggbb> }` — enough to show a light/dark preview |
  | `assets_url` | The theme's assets endpoint (below) |
  | `stylesheet_url` | The theme's stylesheet |

  Always `200` (an empty list when nothing is published).

- **`GET /theme/themes/<slug>.json`** — one theme's full assets: the same data as
  `get_artifacts()` (the table above), by slug. `<slug>` may be `default` for the admin's
  default theme. `404` for an unknown, unpublished, or not-offered theme.

Both carry an `ETag` (send it back in `If-None-Match` for `304 Not Modified` until the
theme changes) and `Cache-Control: public, max-age=60`. They're keyed only by slug (no
visitor cookie), so they cache cleanly for everyone. Browsers only let apps on other
domains read them if the project allows it with CORS (for example with
`django-cors-headers`); capy-theme doesn't set CORS headers itself.

```js
const themes = await (await fetch("/theme/themes.json")).json();
const chosen = themes.find((t) => t.slug === mySavedChoice) ?? themes.find((t) => t.default);
const assets = await (await fetch(chosen.assets_url)).json();
// link chosen.stylesheet_url, set data-theme on <html>, etc. — all on the consumer's side.
```

In Python (another Django module): `from capy_theme.artifacts import theme_catalog,
build_artifacts, get_artifacts` (`get_artifacts(request)` is the published default theme's
assets).

**In a Django template** (the same data, for a server-rendered consumer — e.g. a theme
picker — with no client-side fetch):

```django
{% theme_catalog as themes %}           {# the list above #}
{% for t in themes %}<option value="{{ t.slug }}">{{ t.name }}</option>{% endfor %}

{% theme_assets chosen_slug as assets %} {# one theme's assets by slug (or "default") #}
<link rel="stylesheet" href="{{ assets.stylesheet_url }}">
```

`{% theme_assets %}` is `None` for an unknown, unpublished, or not-offered theme. The
consumer owns the picker UI and remembers the choice itself (capy-theme stores nothing).

### Building an accessible control

Since you render the mode toggle / theme picker yourself, make it accessible:

- Put the control on a native `<button>` or `<a href>` — never a `<div>`/`<span>` — so
  keyboard activation and focus come for free.
- Give it an **accessible name that reflects the current state** (e.g. "Theme: dark"),
  not just an icon, and expose the selected option (`aria-pressed` on a toggle button, or
  a radio group for mutually-exclusive choices).
- **Announce changes** to assistive tech via an `aria-live="polite"` region when you
  switch with JavaScript (no reload).
- The catalog's `light`/`dark` entries are **colors** (`swatch`/`background`); a color
  swatch alone is not an accessible label, so each theme option must also carry the
  theme's text `name` (WCAG 1.4.1).

### Django REST Framework and generated API docs (`CAPY_THEME_API`)

> **Note for projects:** how the API is served depends on whether the project
> uses Django REST Framework (DRF), and capy-theme decides this **by itself**
> when the project starts. Set `CAPY_THEME_API` to choose explicitly.

| `CAPY_THEME_API` | What serves the catalog and per-theme endpoints |
| --- | --- |
| `"auto"` (default) | DRF views if `rest_framework` is in `INSTALLED_APPS`, otherwise plain Django views |
| `"drf"` | Always the DRF views (an error at start-up if DRF isn't installed) |
| `"django"` | Always the plain Django views, even in a DRF project |

- **With DRF and drf-spectacular** set up in the project, the endpoints appear in
  the project's generated API docs (schema, Swagger or Redoc) automatically,
  with their full responses described. Nothing else to configure.
- **The DRF views set their own rules** (no login, no throttling, JSON only), so the
  project's DRF defaults, such as requiring login, don't change this public API.
- **Both ways return exactly the same JSON** and the same ETag.
- capy-theme never requires DRF or drf-spectacular; they're only used when the
  project has them.

## Design tokens

`/theme/tokens.json` downloads the published theme in the W3C
[Design Tokens Format Module 2025.10](https://www.designtokens.org/TR/2025.10/format/),
for design tools (Figma, Tokens Studio, Style Dictionary) and native app builds.
It's made from the same data as the JSON API. File name `<theme slug>.tokens.json`,
media type `application/design-tokens+json`.

- `light` and `dark` groups: `color` (all 20, as OKLCH components with a 6-digit
  `hex` fallback; colorless grays have hue `"none"`) and `shape` (radii and sizes
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
(colors, radii, sizes, border, depth, noise); fonts, the type scale, logos and
the other extras come from the theme stylesheet or the API. The download is a snapshot:
download it again after publishing changes.

