# The live editor and its Components view

Code: `src/capy_theme/editor/` (Python) and `src/capy_theme/static/capy_theme/editor/` (the panel: `editor.js`, and one file per section in `controls/`). The Components view's page and samples are in `src/capy_theme/templates/capy_theme/editor/`.

## The live edit page

**`/theme/live-edit/`** is capy-theme's own page for building a theme, in every
project that includes `capy_theme.urls`. It shows the header (the logo, or the site
name, with the tagline, **Light / Dark / Auto**, **Switch theme** and a link to the
admin) and every daisyUI component (buttons, badges, a card, alerts, a
table, form fields, headings), with the live editor open on it. The admin's **Edit
live** button opens it on that theme (`?edit=<id>`). Without `?edit=`, it opens on
the active theme (or the first theme, if none is active). With no themes yet, it
links to the admin to add one; for a theme that doesn't exist (e.g. deleted), it
says so and links to the active theme and the theme list.

**Switch theme** lists every theme, unpublished ones too (marked "not published"),
and opens the editor on the one you pick. It doesn't change the theme you see as a
visitor. With unsaved changes it asks first: Cancel, then **Save draft**, keeps them.

The tab title names the theme being edited. The header shows the theme being
edited, from its draft (its logo, site name and tagline), and the editor previews
the draft's colors, shape, fonts and logo on everything, so the whole page is what
visitors will see once it's published. (Light / Dark / Auto is your own setting.) The sample headings have no size or weight
classes, so the theme's heading scale and weight show on them. There's a skip
link to the components, and the header wraps on narrow screens.

It's self-contained. It has its own template
(`templates/capy_theme/editor/live_edit.html`) and capy-theme's bundled daisyUI
stylesheet (the Components view's, `static/capy_theme/editor/components.css`), and
it supplies its own `theme` and `request` template variables. So it doesn't use
the project's base template, home page, Tailwind build or context processors, and
it looks and works the same in every project and in the demo. It has nothing
inline, so a strict Content Security Policy blocks nothing on it.

Only staff who can change themes may open it. Logged-out visitors are sent to the
admin login, and anyone else gets the project's 403 page. It sends
`X-Frame-Options: DENY` itself (even without Django's clickjacking middleware), so
no site can frame the editor and trick a click on Save or Publish. It needs Django's
admin at its usual `admin` namespace (`admin.site.urls`), as the rest of
capy-theme does. Code: `editor/live_edit_view.py` (issue #229).

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

Every section of the panel except **Save and publish** folds (click its title),
and every fold starts folded, including Suggestions, Basic, Advanced and Expert
inside Colors. Each stays as you left it after Save draft, Publish or Revert;
reloading the page starts them folded again. The panel has:

- **Base themes:** the light and dark base.
- **Colors:** Light and Dark tabs, with Basic, Advanced and Expert groups.
  Each color has the browser's color picker, a text box (any format),
  **Reset** (back to the base color) and its contrast rating, e.g. "AA 5.19" or
  "⚠ fail 2.1". Overridden colors are shown in bold with a dot.
- **Logos:** the main logo in light and dark, and the header logo heights; the
  other logo versions are folded under **More logo versions (optional)**.
- **Icon:** the icon in light and dark, its background and padding, and a preview
  of them.
- **Backgrounds** and **Sharing image**.
- **Shape and effects:** the radii, sizes and border width, plus depth and noise.

Each image slot says what it's for, its limits and what an empty slot does, and
shows its current image with its alt text (which can be edited). Pick an earlier
upload, or open **Upload a new image**, choose a file and its alt text, and click
**Upload and use**: the image is checked and stored straight away, and chosen in
your unsaved changes (the button is off while it uploads, so it can't be sent
twice). **Save draft** keeps the choice and any alt text you changed; **Revert**
drops them (an uploaded image stays in the theme's list). See
[images](images.md).

While the editor is open, the draft's logos show wherever the page has a
`{% theme_logo %}` (in light and dark), and the browser tab shows the draft's
icon. That's only in your browser; closing the editor puts the published ones
back. (For staff who can edit themes, `{% theme_logo %}` marks each logo with
`data-capy-logo-slot` so the editor can find it; visitors get the same HTML as
always. If a project caches whole pages or template fragments with the logo in
them, keep editors' pages out of that cache (or vary it by user): otherwise a
visitor could be served the marked HTML, which is harmless, or an editor the
unmarked HTML, where the preview can't swap the logo. Of the attributes given to
`{% theme_logo %}`, the preview keeps only `class`, `title` and `aria-*`; others,
such as `style`, `width` or `id`, only show on the published logo.) The generated
favicons and app icons are made when you publish.
- **Suggestions** (in the Colors section): click **Suggest colors** for colors
  that go with the current primary (analogous, complementary, triadic) and, if the
  theme has a logo, the logo's main colors. Clicking a suggestion fills in those
  colors for the current mode.

Every change shows on the page straight away (in your browser only).

- **Save draft** stores the panel's values in the theme's draft (needs the
  change permission). Visitors don't see it until it's published. Only the
  panel's settings and the images' alt text are changed; the name, site name,
  tagline and mode stay as they are.
- **Revert** throws away the unsaved changes and goes back to the saved draft
  (it asks first). Nothing on the server changes.
- **Publish** (needs `publish_theme`) saves any unsaved changes first, then
  publishes, with an optional note, through the same revisions as the admin's
  Publish page.
- With unsaved changes, the panel says so, and closing it or leaving the page
  asks before throwing them away.

- While it's open, the page makes room for it: it moves down below the editor's
  banner and, in windows at least 48rem (768 px) wide, left of the panel, so the
  page's own controls (like the Light / Dark / Auto buttons) can still be used.
  Parts of the page it fixes in place or makes sticky (e.g. a sticky navbar)
  don't move. On narrow screens the panel covers the page.
- It edits the active theme, or any theme with `?edit=<theme id>` on any page's
  URL, which also opens the panel straight away.
- The panel is plain CSS and JavaScript (`static/capy_theme/editor/`), not
  Tailwind or daisyUI classes, so it looks the same on any page. The script is a
  static file and the preview uses a constructed stylesheet, so both work under a
  strict Content Security Policy.
- It reads the draft from `/theme/editor/<id>/state/`, and previews unsaved
  values by POSTing them as JSON to `/theme/editor/<id>/preview/`, which returns
  the CSS, every color's value and the contrast ratings. Both use the same code
  as publishing (so the preview matches what would be published), are for staff
  with change permission only, and **never write anything**. The preview needs
  Django's CSRF token, which the page passes to the script.

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

Every editor setting shows there: colors, shape, fonts, the type scale (all six
heading levels and the display font) and base themes through the draft CSS;
logo, icon, sharing-image and background choices, logo heights and the icon's
background and padding through the page itself, including **unsaved** choices
(the page gets them in its address and reloads when they change; nothing is
saved). The icon is previewed with the draft's background and padding (made on
the fly; the real icon files are made when publishing), and the dark icon too.
A line at the top says which domain the view is for and which theme visitors on
that domain see. Custom CSS: people who may edit it get the draft's custom CSS
applied, with the selectors it styles listed; others get the published custom
CSS.

**Accessibility:** the view's own page passes Chrome's checks in light and dark
(every control and image has a name, language and title set, unique ids, a main
landmark). The component samples show the theme's own colors, so a color pair
with too little contrast shows there too; the editor's contrast badges flag the
same pairs. Lighthouse itself isn't run (it's not a dependency).

It's a page of its own (`/theme/editor/<id>/components/`, staff who can edit
themes only) shown in an iframe, so its daisyUI stylesheet can never change the page
being edited. The editor puts the draft theme's CSS into it each time the preview
changes. The page may only be framed by the same site.

Each sample is a template in
`src/capy_theme/templates/capy_theme/editor/components/`, listed in `COMPONENTS`
in `src/capy_theme/editor/components_view.py`. It's included once per mode, with `mode` set
to `"light"` or `"dark"`, so use `{{ mode }}` in any `id` or `name` that must be
unique.

The view brings its own stylesheet,
`src/capy_theme/static/capy_theme/editor/components.css` (daisyUI plus the
Tailwind classes the samples use), so it works in any project. The live edit page
uses it too. It's built from those templates, the live edit page's
(`live_edit.html`, `live_edit_components.html`) and the mode toggle and theme
picker, so **rebuild it after changing any of them** (or after updating daisyUI):

```bash
uv run python scripts/build_components_css.py
```

It uses the Tailwind CLI that the demo downloads. If it says the CLI isn't found,
run `uv run python demo/manage.py tailwind build` once first.
