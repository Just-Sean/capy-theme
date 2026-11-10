# Colours, shape, type and the stylesheet

Code: `src/capy_theme/colors/` (colour maths, values, suggestions) and `src/capy_theme/css/` (everything that writes the theme stylesheet).

## Colours

On a theme's admin page, the colour sections let you override any of daisyUI's
20 colours, separately for light and dark mode:

- **Basic** (shown open): primary, secondary, accent, neutral, background and
  text on background.
- **Advanced** (folded): info, success, warning, error, and the two darker
  background shades.
- **Expert** (folded): the text colour on each coloured element.

Leave a field blank to use the base theme's colour, which is shown greyed out
in the empty field. Only the colours you set are stored, in `settings["colors"]`;
the rest always come from the base. Enter colours any common way, such as `#3b82f6`, `rgb(59 130 246)`,
`hsl(217 91% 60%)`, `oklch(62% 0.19 260)` or a colour name, or use the colour
picker beside each field. They're converted to and stored as OKLCH (daisyUI's
format), so after saving the field shows e.g. `oklch(62.31% 0.188 259.81)`.
Like everything else, they show on the site after publishing.

**Readable text is worked out for you.** When you set a colour (say primary) but
not its text colour (primary text), the text colour is chosen automatically: a
very light or very dark tint of the same hue, whichever reads better, falling
back to pure white or black if a tint wouldn't meet WCAG AA (4.5:1). When you set
the background but not its darker shades or its text, those are worked out from
it as well. Anything you set yourself is always kept.

**Contrast warnings.** Each colour field shows the WCAG contrast of its pair
(e.g. *Primary / Primary text: 4.7:1, passes AA*), and the **Contrast** section
lists every pair for light and dark. AA needs 4.5:1 and AAA 7:1 for normal text.
Pairs below AA are marked "⚠ fails AA". They're warnings only: saving and
publishing still work. Ratings are for the saved draft, so save to update them.

## Browser colour, focus outline and email colours

- **Browser colour:** `{% theme_head %}` adds `<meta name="theme-color">` tags, so
  phones colour their address bar to match the page background. There's one per
  mode (chosen by the device), or a single one when a mode is forced.
- **Focus outline:** the stylesheet gives keyboard focus (`:focus-visible`) a 2 px
  outline in `--capy-focus`. That's the primary colour when it has at least 3:1
  contrast with the background (WCAG's minimum for non-text), otherwise the text
  colour, so it's always visible.
- **Email colours:** HTML emails can't use OKLCH or CSS variables, so templates
  get every light-mode colour as hex in `theme.email_colors`, e.g.
  `{{ theme.email_colors.primary }}` or `{{ theme.email_colors.base_100 }}`.

## Type scale

The **Type scale** section (and the editor's "Fonts and type") sets:

| Setting | Range | Effect |
| --- | --- | --- |
| Base text size | 14–24 px | The root font size: body text, and everything sized in rem, scales with it. **At least 14 px**, so text stays readable. |
| Heading scale | 1.05–1.6 | `h6` is 1 rem and each level up multiplies by this (1.25 gives `h1` ≈ 3 rem). |
| Line height | 1.1–2.2 | Space between lines of body text. |
| Heading weight | 100–900 | How bold headings are. |

Blank values leave the project's own styles alone. They're written as variables
(`--capy-base-size`, `--capy-h1` … `--capy-h6`, `--capy-line-height`,
`--capy-heading-weight`) plus default rules in `@layer base`, so utility classes on
an element (like the demo's `text-5xl` headings) still win.

**Font loading:** every `@font-face` uses `font-display: swap`, so text shows
straight away in a fallback font. `{% theme_head %}` also **preloads** the body
and heading fonts' regular files (`<link rel="preload" as="font">`), so the right
font arrives sooner.

## Shape and effects

The **Shape and effects** section overrides daisyUI's shape settings, for both
light and dark mode:

| Setting | daisyUI variable | Range |
| --- | --- | --- |
| Small corner radius (checkboxes, toggles, badges) | `--radius-selector` | 0–2 rem |
| Field corner radius (buttons, inputs, tabs) | `--radius-field` | 0–2 rem |
| Box corner radius (cards, alerts, modals) | `--radius-box` | 0–3 rem |
| Small control size / Field size | `--size-selector` / `--size-field` | 0.125–0.5 rem |
| Border width | `--border` | 0–4 px |
| Depth (3D shadow) / Noise (grain) | `--depth` / `--noise` | on or off |

Blank fields (and "From the base theme") use the base theme's value, which is
shown greyed out. A radius of 0 gives square corners. Stored in
`settings["shape"]`.

## Visitors' accessibility settings

The theme stylesheet respects two device settings, for every page, with nothing
to configure:

- **Reduce motion** (`prefers-reduced-motion: reduce`): animations and
  transitions finish at once and smooth scrolling is off. daisyUI only does this
  for a few components; this covers all of them.
- **More contrast** (`prefers-contrast: more`): no noise texture or depth
  shading, 2 px borders and a 3 px focus outline. The theme's colours stay as
  they are (every colour pair's contrast is already shown in the editor).

To try them: Chrome DevTools → **Rendering** → "Emulate CSS media feature".

## The theme stylesheet

Each published revision has its own stylesheet at `/theme/<version>.css`, where
`<version>` is a short hash unique to that revision (`ThemeRevision.css_version`).
It sets daisyUI's CSS variables (`--color-primary` and the rest): light values on
`:root`, and dark values inside `@media (prefers-color-scheme: dark)`. The rules
aren't in a CSS layer, so they override daisyUI's own theme rules.

- Browsers cache each stylesheet for a year. Publishing creates a new version,
  so pages link to a new URL and visitors get the change straight away.
- An old URL keeps returning the revision it was made for.
- Pages link it with `?v=<capy-theme version>` on the end (e.g.
  `/theme/52e3f01881d2.css?v=0.1.0`). When an upgrade changes how the module
  writes its CSS, the new version in the link makes browsers fetch it again
  instead of using a copy cached for a year. The view ignores `?v=`.
- The values come from the revision itself, not from today's daisyUI catalogue.
  Each publish saves both base themes' full values, so a later daisyUI update
  can't change or break a published theme. To pick up daisyUI's changes,
  publish again.
- After a daisyUI update (see [Updating daisyUI](development.md#updating-daisyui)), the admin
  shows which published themes are affected. The theme list's "Base changed in
  daisyUI" column ticks them, and each theme's page says whether a base was
  changed or removed. The site keeps using the saved version until someone publishes.

On a theme's admin page, "View its stylesheet" opens the live revision's
stylesheet. Pages link it with `{% theme_head %}` (see [Add it to a project](../README.md#add-it-to-a-project)).
