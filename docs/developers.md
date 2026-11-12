# For developers

What a developer using the theme from their own code needs: in their CSS, in a
React, Vue or other front end, in a mobile app, or in another Django module.
capy-theme owns the theme and makes it available; other code applies it.

## CSS variables

`{% theme_head %}` links the theme stylesheet (`/theme/<version>.css`). It
defines these variables on `:root`, with the light values by default, the dark
values when the visitor's device prefers dark, and either set forced by
`data-theme="capy-light"` or `"capy-dark"` on any element (the mode toggle sets it
on `<html>`). Use them in your own CSS, e.g. `color: var(--color-primary)`.

daisyUI's classes (`btn-primary`, `bg-base-200`…) already use the daisyUI
variables, so most pages never name them directly.

### daisyUI's variables (always set)

| Variable | What it is |
| --- | --- |
| `--color-primary` | Primary color (OKLCH) |
| `--color-primary-content` | Text on primary |
| `--color-secondary` | Secondary color |
| `--color-secondary-content` | Text on secondary |
| `--color-accent` | Accent color |
| `--color-accent-content` | Text on accent |
| `--color-neutral` | Neutral color |
| `--color-neutral-content` | Text on neutral |
| `--color-base-100` | Page background |
| `--color-base-200` | Background, darker |
| `--color-base-300` | Background, darkest |
| `--color-base-content` | Text on the background |
| `--color-info` | Info color |
| `--color-info-content` | Text on info |
| `--color-success` | Success color |
| `--color-success-content` | Text on success |
| `--color-warning` | Warning color |
| `--color-warning-content` | Text on warning |
| `--color-error` | Error color |
| `--color-error-content` | Text on error |
| `--radius-selector` | Corner radius of checkboxes, toggles and badges |
| `--radius-field` | Corner radius of buttons and inputs |
| `--radius-box` | Corner radius of cards, modals and alerts |
| `--size-selector` | Base size of checkboxes, toggles and badges |
| `--size-field` | Base size of buttons and inputs |
| `--border` | Border width |
| `--depth` | Depth effect: `1` on, `0` off |
| `--noise` | Noise texture: `1` on, `0` off |

### capy-theme's own variables

| Variable | When it's set | What it is |
| --- | --- | --- |
| `--capy-focus` | Always | The keyboard-focus outline color (primary, or the text color if primary has too little contrast) |
| `--font-sans` | A body font is chosen | Tailwind's sans font family (the body font) |
| `--font-mono` | A monospace font is chosen | Tailwind's monospace font family |
| `--capy-font-body` | A body font is chosen | The body font family |
| `--capy-font-heading` | A heading font is chosen | The heading font family (used by `h1`–`h6`) |
| `--capy-font-mono` | A monospace font is chosen | The monospace font family (used by `code`, `pre`…) |
| `--capy-font-display` | A display font is chosen | The display font family (used by `.capy-display`) |
| `--capy-base-size` | A base size is set | The root font size, e.g. `18px` |
| `--capy-line-height` | A line height is set | Body line height, e.g. `1.6` |
| `--capy-heading-weight` | A heading weight is set | Heading font weight, e.g. `700` |
| `--capy-h1` | A heading scale is set | `h1` size in rem (likewise `h2`–`h6`) |
| `--capy-h2` | A heading scale is set | `h2` size |
| `--capy-h3` | A heading scale is set | `h3` size |
| `--capy-h4` | A heading scale is set | `h4` size |
| `--capy-h5` | A heading scale is set | `h5` size |
| `--capy-h6` | A heading scale is set | `h6` size |
| `--capy-bg-login` | A login background is chosen | `url(...)` of the login background (class `capy-bg-login` uses it) |
| `--capy-bg-pattern` | A page pattern is chosen | `url(...)` of the page pattern (class `capy-bg-pattern` uses it) |

## The JSON API

`GET /theme/api.json` returns the active theme's published values and asset URLs
(absolute): colors (OKLCH and hex), fonts with file URLs, shape, type, every
logo slot (after fallbacks, with smaller copies), icons, the sharing image,
backgrounds and mode settings. Full details: [artifacts.md](artifacts.md#the-json-api).

```js
const response = await fetch("https://example.com/theme/api.json");
if (response.ok) {
  const theme = await response.json();
  document.documentElement.style.setProperty("--brand", theme.colors.light.primary);
  const logo = theme.logos.logo_main.light; // { url, width, height, alt, variants }
}
```

- **Caching:** send the `ETag` back in `If-None-Match` and you get `304` until the
  theme is published again. Responses may be cached for 60 seconds.
- **Which view serves it:** with Django REST Framework installed it's a DRF view,
  listed automatically in the project's drf-spectacular API docs; otherwise a
  plain Django view. `CAPY_THEME_API = "auto"` (default), `"drf"` or `"django"`
  chooses. Both return the same JSON.
- **Apps on other domains** need the project to allow them with CORS (for example
  `django-cors-headers`). capy-theme doesn't set CORS headers.

In Python (another Django module): `from capy_theme.artifacts import get_artifacts`.
In templates: `{% theme_artifacts as artifacts %}`.

## Downloads

| Address | What it is |
| --- | --- |
| `/theme/api.json` | The JSON API |
| `/theme/tokens.json` | W3C design tokens (format 2025.10), for design tools and native app builds ([details](artifacts.md#design-tokens)) |
| `/theme/daisyui-theme.css` | daisyUI theme blocks (light and dark), to compile the theme into your own Tailwind CSS ([details](artifacts.md#daisyui-theme-blocks)) |

All three hold the published theme, are public, and return `404` when no theme is
published. They're under the prefix the project gave `capy_theme.urls` (`/theme/`
in these docs).
