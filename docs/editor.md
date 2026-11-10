# The live editor and the showcase

Code: `src/capy_theme/editor/` (Python) and `src/capy_theme/static/capy_theme/editor/` (the panel: `editor.js`, and one file per section in `controls/`). The showcase is in `src/capy_theme/showcase/` until it's replaced by the editor's Components view.

## The live theme editor

Staff who can change themes see an **Edit theme** button: on the showcase, and in
the bottom-right corner of **every page** that uses `{% theme_head %}`. It opens
a panel on the right and shows the theme's **draft** on the page you're on, in
your browser only. Visitors keep seeing the published theme, and a banner at the
top says so. **Close** (or **Exit** in the banner) puts the page back to the
published look.

The editor is loaded by `{% theme_head %}` only for staff with the change-theme
permission; visitors get none of its files. To hide the corner button (for
example, to put your own link to `?edit=<id>` somewhere), set
`CAPY_THEME_EDITOR_BUTTON = False`.

The panel has:

- **Base themes:** the light and dark base.
- **Colours:** Light and Dark tabs, with Basic open and Advanced and Expert
  folded. Each colour has the browser's colour picker, a text box (any format),
  **Reset** (back to the base colour) and its contrast rating, e.g. "AA 5.19" or
  "⚠ fail 2.1". Overridden colours are shown in bold with a dot.
- **Shape and effects:** the radii, sizes and border width, plus depth and noise.
- **Suggestions** (in the Colours section): click **Suggest colours** for colours
  that go with the current primary (analogous, complementary, triadic) and, if the
  theme has a logo, the logo's main colours. Clicking a suggestion fills in those
  colours for the current mode.

Every change shows on the page straight away (in your browser only).

- **Save draft** stores the panel's values in the theme's draft (needs the
  change permission). Visitors don't see it until it's published. Only the bases,
  colours and shape are changed; the name, branding and mode stay as they are.
- **Publish** (needs `publish_theme`) saves any unsaved changes first, then
  publishes, with an optional note, through the same revisions as the admin's
  Publish page.
- With unsaved changes, the panel says so, and closing it or leaving the page
  asks before throwing them away.

- It edits the active theme, or any theme with `?edit=<theme id>` on any page's
  URL, which also opens the panel straight away.
- The panel is plain CSS and JavaScript (`static/capy_theme/editor/`), not
  Tailwind or daisyUI classes, so it looks the same on any page. The script is a
  static file and the preview uses a constructed stylesheet, so both work under a
  strict Content Security Policy.
- It reads the draft from `/theme/editor/<id>/state/`, and previews unsaved
  values by POSTing them as JSON to `/theme/editor/<id>/preview/`, which returns
  the CSS, every colour's value and the contrast ratings. Both use the same code
  as publishing (so the preview matches what would be published), are for staff
  with change permission only, and **never write anything**. The preview needs
  Django's CSRF token, which the page passes to the script.

## The theme showcase

`/theme/showcase/` shows the active theme on every kind of daisyUI component
(buttons, badges, alerts, cards, tabs, a table, form fields, progress bars, a
modal, headings and text), with light and dark mode side by side. It also has a
swatch for each of the 20 colours (with its text colour, OKLCH and hex values,
contrast rating, and whether it's overridden, worked out or from the base
theme), and samples of every shape setting, and a **Fonts and type** section: each role's font
and source with a sample in every weight and style that's actually loaded (so
nothing shown is a browser-faked bold), the heading scale, body text at the base
size with its line height, a monospace code block, and a character sample for
the fonts' character sets. It also shows
the site name, tagline, logo and the base themes in use; a **Mode and visitors**
panel (the default mode, the light/dark/auto toggle, the visitor theme picker,
and the upcoming and running scheduled themes with their dates); and an **Images and
icons** section: every logo slot at the header height in both modes (saying
whether it's its own image, the light one, or what an empty slot falls back to)
with its generated sizes and formats; every icon at its real size (the maskable
icon inside a circle and a squircle, the monochrome icon on a dark tile); the
sharing image; and the background images. Staff only by default
(see `CAPY_THEME_SHOWCASE`). The demo's navbar links to it.

Each section is its own template in
`src/capy_theme/templates/capy_theme/showcase/sections/`, listed in
`SHOWCASE_SECTIONS` in `showcase/views.py`. To add a section, add a template there and
its name to the list. It's included once per mode, with `mode` set to `"light"`
or `"dark"`, so use `{{ mode }}` in any `id` or `name` that must be unique.

The showcase brings its own stylesheet, `src/capy_theme/static/capy_theme/showcase.css`
(daisyUI plus the Tailwind classes the showcase templates use), so it works in
any project. It's built from the showcase templates, so **rebuild it after
changing them** (or after updating daisyUI):

```bash
uv run python scripts/build_showcase_css.py
```

It uses the Tailwind CLI that the demo downloads. If it says the CLI isn't found,
run `uv run python demo/manage.py tailwind build` once first.
