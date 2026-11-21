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

> **Rendering a control (mode toggle, theme picker, logo)?** capy-theme exposes the
> data for it (below and in the table) but deliberately does **not** render the UI
> widget — the app-shell or module renders its own, so the theme never dictates
> another app's chrome. See "Mode and theme-picker controls" below.

What's in it (all from the published revision; with a request, URLs are absolute):

| Key | Contents |
| --- | --- |
| `theme` | `name`, `slug`, `revision` |
| `branding` | `site_name`, `tagline`, `logo_alt` |
| `colors`, `colors_hex` | The 20 colors per mode (`light`, `dark`), as OKLCH and as `#rrggbb` |
| `fonts` | Per role the theme sets: `family`, `stack` (CSS `font-family`), `source` |
| `logos` | The six logo slots, `light` and `dark`, after fallbacks: `url`, `width`, `height`, `alt`, `content_type`, `variants` (smaller copies: `url`, `width`, `format`) |
| `icons` | File name → URL: `favicon.ico`, `favicon.svg`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `icon-monochrome-512.png` |
| `sharing_image` | `url`, `width`, `height`, `alt` (1200 × 630), or `None` |
| `backgrounds` | `login` and `pattern`, each `light` and `dark` URL (or `None`) |
| `mode` | `default`, `visitors_can_switch` |
| `stylesheet_url` | The theme stylesheet |

## Mode and theme-picker controls

capy-theme owns *how* light/dark/auto and the theme choice work (the cookie, the
before-paint script, the endpoints), but it does **not** render the buttons — an
app-shell or any other module renders its own control from this data, so the theme
never dictates another app's chrome.

### Mode state — `{% theme_mode_state %}`

`{% theme_mode_state as mode %}` gives the light/dark/auto state (`None` if no theme
is active):

| Key | Contents |
| --- | --- |
| `can_switch` | Whether the theme lets visitors switch |
| `current` | The current mode: `light`, `dark` or `auto` |
| `options` | One per mode: `value`, `label`, `url`, `current` (empty when `can_switch` is `False`) |
| `next` | The mode a single cycling button advances to: `value`, `label`, `url` (`None` when `can_switch` is `False`) |

Each `url` sets that mode and returns to the current page, so a plain `<a>` works
without JavaScript. **Render the mode control only when `can_switch` is `True`:** when the
theme forbids switching, `options` is empty, `next` is `None`, and switching is a no-op
both server-side and in the script, so a control would be inert.

### Theme-picker state — `{% theme_picker_state %}`

`{% theme_picker_state as picker %}` gives the themes a visitor may choose (`None` if
no theme is active):

| Key | Contents |
| --- | --- |
| `allowed` | Whether visitors may choose a theme (`CAPY_THEME_VISITOR_THEMES`) |
| `current` | The chosen theme's slug, or `default` for the site's own |
| `options` | `default` ("Site default") then each offered theme: `value`, `label`, `url`, `current` |

Show the picker only when there's more than one option.

### The mode-switching protocol

`{% theme_head %}` includes a tiny script that applies the mode before the page draws
and enhances a consumer's control to switch with no reload. Put the hooks on a **native
`<a href>` or `<button>`** (never a `<div>`/`<span>`), so keyboard activation and focus
come for free and the no-JS fallback works:

- **`data-capy-mode="light|dark|auto"`** on a native control → clicking sets that mode,
  and the script marks the current one with `aria-current="true"` and `.btn-active`.
  Point its `href` at the option's `url`. These are link-style options tracked with
  `aria-current`; a consumer that wants button / `aria-pressed` semantics manages that
  state itself.
- **`data-capy-mode-cycle`** on a native control → clicking advances to the next mode
  (light → dark → auto → light). Point its `href` at `mode.next.url` so it still works
  without JavaScript.
- **`<html data-capy-color-mode="light|dark|auto">`** — set by the script (and
  server-side by `{% theme_html_attrs %}`), so a consumer can show the matching icon
  with CSS, e.g. `[data-capy-color-mode="dark"] .icon-sun { display: none }`.
- **`capy:modechange` event** — the script dispatches it on `document` (`detail: {mode}`)
  whenever a visitor switches, so a consumer can announce the change to assistive
  technology (WCAG 2.2 §4.1.3) without reinventing a `MutationObserver`:

  ```js
  document.addEventListener("capy:modechange", (e) => {
    liveRegion.textContent = e.detail.mode + " theme";  // an aria-live="polite" element
  });
  ```

Use links (`<a href=…>`) so switching degrades to a full-page reload without JavaScript.

**Make the current mode perceptible to assistive tech.** An icon swapped by CSS alone
reaches sighted users only. Give the control an accessible name that reflects the current
mode with visually-hidden, per-mode labels shown and hidden by the same
`data-capy-color-mode` CSS (the hidden ones must use `display: none` so they drop out of
the name), and announce changes with the `capy:modechange` event above.

### Rendering a mode control (example)

A single cycling button — gated on `can_switch`, with a no-JS fallback via `href`, and an
icon and accessible name driven by `html[data-capy-color-mode]` (the consumer owns the CSS):

```django
{% theme_mode_state as mode %}
{% if mode.can_switch %}
  <a href="{{ mode.next.url }}" data-capy-mode-cycle class="btn btn-ghost">
    <span class="capy-icon-light" aria-hidden="true">…</span>
    <span class="capy-icon-dark" aria-hidden="true">…</span>
    <span class="capy-icon-auto" aria-hidden="true">…</span>
    <span class="sr-only capy-name-light">Light theme</span>
    <span class="sr-only capy-name-dark">Dark theme</span>
    <span class="sr-only capy-name-auto">Auto theme</span>
  </a>
{% endif %}
```

Per-mode options instead: loop `mode.options`, putting `o.value` on `data-capy-mode` and
`o.url` on `href`.

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
the other extras need `{% theme_head %}` or the API. The download is a snapshot:
download it again after publishing changes.

