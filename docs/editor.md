# The live editor and its Components view

Code: `src/capy_theme/editor/` (Python) and `src/capy_theme/static/capy_theme/editor/` (the panel: `editor.js`, and one file per section in `controls/`). The Components view's page and samples are in `src/capy_theme/templates/capy_theme/editor/`.

## The live theme editor

Staff who can change themes see an **Edit theme** button in
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

## See it as a visitor

**See it as a visitor** at the top of the editor panel shows the page as visitors
see it right now: the **published** theme, not your draft. The draft controls
are hidden while it's on; turning it off brings the draft back. Nothing is saved
or changed. Options:

- **Mode:** as now, light, dark, or the device setting.
- **Theme:** the site's theme, or one of the themes offered to visitors (as a
  visitor's own choice would show it).
- **On date:** the site's theme at noon on that day, including scheduled themes,
  to check a schedule before it starts.

Below the options, a summary lists what's set up for visitors: the live theme,
its default mode and whether visitors can switch, the offered themes, and
running and upcoming schedules with their dates. The Components view follows the
same view while it's on. The data comes from `/theme/editor/visitor-view/`
(staff who can edit only; `?theme=<slug>` or `?date=YYYY-MM-DD`), using the same
rules as the live site.

## The Components view

**Show all components** at the top of the editor panel opens every daisyUI
component (buttons, badges, alerts, cards, tabs, a table, form fields, progress
bars, a modal, headings and text) and the theme's **images and icons** in the
**draft** theme, light and dark side by
side, beside the panel. Every change in the editor shows on them straight away.
**Close components** or Escape closes it.

The images section shows every logo slot in light and dark, saying whether it's
its own image, the light one, or what an empty slot falls back to, with its
generated sizes; the generated icons at their real size (from the published
theme, since they're made when publishing); the sharing image; and the
backgrounds. It shows the saved draft and reloads after **Save draft** or
**Publish**.

It's a page of its own (`/theme/editor/<id>/components/`, staff who can edit
themes only) shown in an iframe, so its daisyUI stylesheet can never change the page
being edited. The editor puts the draft theme's CSS into it each time the preview
changes. The page may only be framed by the same site.

Each sample is a template in
`src/capy_theme/templates/capy_theme/editor/components/`, listed in `COMPONENTS`
in `src/capy_theme/editor/views.py`. It's included once per mode, with `mode` set
to `"light"` or `"dark"`, so use `{{ mode }}` in any `id` or `name` that must be
unique.

The view brings its own stylesheet,
`src/capy_theme/static/capy_theme/editor/components.css` (daisyUI plus the
Tailwind classes the samples use), so it works in any project. It's built from
those templates, so **rebuild it after changing them** (or after updating daisyUI):

```bash
uv run python scripts/build_components_css.py
```

It uses the Tailwind CLI that the demo downloads. If it says the CLI isn't found,
run `uv run python demo/manage.py tailwind build` once first.
