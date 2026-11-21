# Themes, publishing and permissions

Code: `src/capy_theme/themes/` (models, publishing, history, which theme is live, scheduling, light/dark) and `src/capy_theme/admin/`.

## Theme settings schema

Everything a theme overrides is stored in its `settings` field, a JSON object.
It's checked against `src/capy_theme/settings.schema.json` (a standard
[JSON Schema](https://json-schema.org/), validated with the `jsonschema` package)
every time a theme is saved, so data that doesn't match can't be saved. Keys the
schema doesn't list are rejected. It starts with no keys, and each phase adds its own.

When a change adds a new setting, add it to `settings.schema.json` in the same
change, with a test. No migration is needed, because `settings` is a single JSON column.

After pulling changes that add migrations, apply them to the demo database:

```bash
uv run python demo/manage.py migrate
```

## The theme's admin page

The admin page is the plain fallback to the live editor. Every section starts
folded (click its title to open it); Django shows a section with errors
unfolded. Its sections, top to bottom:

1. Name and slug
2. Publishing status
3. Base themes
4. Branding (site name and tagline, then Icon, Logos, More logo versions,
   Backgrounds and Sharing image, each uploaded and chosen in place)
5. Colors (light and dark; Basic, Advanced and Expert)
6. Contrast
7. Shape and effects
8. Mode
9. Advanced (stored settings, ID and dates)
10. Media (every uploaded image: edit its alt text, or delete one nothing uses)

At the top right: **Edit live** opens the theme in the live editor, on
capy-theme's live edit page (`/theme/live-edit/`, see [the editor](editor.md)), next to
**Revisions**, **Export** and Django's **History**.

At the bottom, **Save and publish** is the one place to save, publish and activate
(see [Drafts and publishing](#drafts-and-publishing)).

The **Advanced** section shows the theme's stored `settings` as read-only JSON.
They're edited through the fields above or the live editor, not typed by hand.

## Branding

On a theme's admin page, the **Branding** section has the site name, tagline
and logo alt text, stored in the theme's `settings`. Logos are uploaded and
chosen in the **Logos** section (see [Logos](images.md#logos)).

Like everything else, branding changes show on the site only after publishing.

## Drafts and publishing

Editing a theme in the admin changes only its **draft**. Pages will use the
theme's **live revision**, which changes only when someone publishes:

- At the bottom of a theme's edit page, **Save and publish** shows where the theme
  stands (whether the draft has unpublished changes, the published revision,
  whether it's the default theme, and, while a theme schedule is running, which
  theme the site is showing now) and has three buttons, each saying what it does:
  - **Save draft:** saves your changes and stays on the page. Visitors see nothing
    until you publish.
  - **Save and publish:** saves, then publishes. Visitors see it wherever this
    theme is used.
  - **Save, publish and activate:** saves, publishes, then makes it the default
    theme (see [The active theme](#the-active-theme)). Not shown when it already
    is, or in a popup.

  The two publishing buttons need the `publish_theme` permission (without it, only
  **Save draft** shows), and ask before going ahead. Above them is an optional
  note for the history, kept when you publish (and kept on the page if the save
  fails). The theme list has the same on each row: **Publish**, **Publish and
  activate** and **Activate** (which uses the last published version), shown when
  they apply and asking first. The live editor has the same three buttons.
- Saving and publishing with one button happen together: in the rare case that
  publishing fails unexpectedly (say the server can't write the icon files), the
  page shows an error and the draft isn't saved either, so nothing is half done.
- Publishing copies the draft's look (light base, dark base and `settings`) into a
  new numbered `ThemeRevision`, recording who published it and when, and makes it
  the live revision.
- If the draft matches the live revision, publishing is refused ("Nothing to
  publish"); **Save, publish and activate** still activates it.
- The name and slug aren't part of a revision, so renaming takes effect without publishing.
- Revisions can't be edited or deleted. They're listed on the theme's edit page,
  and removed only if the theme itself is deleted.
- **Revisions** (button on the theme's edit page) lists every revision and
  **compares** any two, showing exactly which values changed (bases, logo,
  branding, mode, each color and each shape setting).
- **Restore** (needs `publish_theme`) copies an old revision into the draft and
  publishes it **as a new revision**, noted "Restored revision N". Nothing in the
  history is deleted, and the site shows it straight away.

From code: `from capy_theme.themes.publishing import publish` then `publish(theme, user=request.user, note="…")`, or `publish_and_activate(theme, user=…, note="…")` to publish and make it the default theme in one step.

## The active theme

One theme is the site's **default** theme: the one it shows, unless a theme
schedule is running or a domain has a site theme of its own. To choose it, click
**Activate** on its row in the admin's theme list, or **Save, publish and activate**
on its page (both need the `publish_theme` permission). The list's "Showing now"
column shows which theme the site is showing right now (the default, or a scheduled
one), on every domain without a site theme of its own. A theme must be published
before it can be activated.

From code: `from capy_theme.themes.active import get_active_theme` then
`get_active_theme(request)` returns the active `Theme`, with its live revision
loaded, or `None` if no theme is active. It's cached (see
`CAPY_THEME_CACHE_SECONDS`), so a normal page load doesn't query the database.
If the cache is unreachable the theme is loaded straight from the database; if
the database is unreachable too, it returns `None` and the page renders unthemed
rather than erroring (the outage is logged — see the README's Logging section).

## Scheduled themes

A theme can be live between two dates, e.g. a holiday theme. In the admin, go
to **Capy Theme → Theme schedule → Add**, choose a published theme and give a
start and/or end date (blank start: straight away; blank end: until removed).
While a schedule is running (start ≤ now < end) its theme replaces the site's
default; afterwards the default returns by itself. If schedules overlap, the one
that started most recently wins. The list shows each schedule as Upcoming, Running or
Finished. Scheduling
needs the `publish_theme` permission, like activating.

The cached theme expires at the next start or end, so schedules switch on time
even with a long `CAPY_THEME_CACHE_SECONDS`.

## Multiple sites

One install can serve several domains (for example `shop.example.com` and
`blog.example.com`), each with its own theme:

1. Activate a theme as usual (**Activate** on the theme list, or **Save, publish and
   activate**): it's the theme for **every site**.
2. In **Admin → Capy Theme → Site themes → Add**, give a domain and the theme it
   should use. Only that domain uses it; every other domain uses the theme for
   every site. Needs the `publish_theme` permission.

The domain comes from the request (`request.get_host()`), without the port and in
lower case, so it must be in the project's `ALLOWED_HOSTS`. A scheduled theme can
also be limited to one domain (its **Site** field); on that domain it wins while
it's running. A domain's own theme or running schedule wins over the ones for
every site. The live editor, the API and the downloads
all follow the domain they're opened on. From code:
`capy_theme.themes.active.activate(theme, site="shop.example.com")`.

## Offering themes for visitors to choose

An admin can offer several themes for visitors to pick among:

1. In the admin, tick **Offer to visitors** on each theme to offer, and publish it.
2. The offered themes (plus the default) appear in the **catalog**
   (`/theme/themes.json`), each with its stylesheet URL and a light/dark preview swatch.

A consumer reads the catalog, builds its own picker, and links the chosen theme's
stylesheet — capy-theme renders no picker and remembers no choice (see
[docs/artifacts.md](artifacts.md#the-json-api)).

## Light and dark mode

On a theme's admin page, the **Mode** section has:

- **Default mode:** *Auto* (follow the visitor's device setting), *Light* or *Dark*.
- **Visitors can switch** (on by default).

Both are published with the theme and exposed as data (the `mode` key in a theme's
assets: `default`, `visitors_can_switch`), for a consumer to honor. capy-theme doesn't
switch modes or render a toggle itself.

How it works in the stylesheet: it carries both light and dark. For "auto" it follows
the device (`prefers-color-scheme`); to force a mode, set `data-theme="capy-light"` or
`"capy-dark"` on `<html>` (or any element). A consumer does this and builds its own
toggle, using the `mode` setting to know the admin's default and whether a toggle is
wanted.

## Permissions

Editing themes uses Django's normal model permissions (view, add, change, delete
theme). capy-theme adds three more, given to users or groups in the admin under
**Authentication and Authorization**:

| Permission | Allows |
| --- | --- |
| `capy_theme.publish_theme` | Publishing a theme, activating it, restoring old revisions, scheduling, Site themes, and **Offer to visitors**. Without it, those buttons and actions are hidden, and direct requests are refused. |
| `capy_theme.edit_custom_css` | Seeing and editing a theme's custom CSS. Without it, Export leaves the custom CSS out, Import leaves it out, and Restore keeps the draft's current custom CSS. |
| `capy_theme.import_theme` | Importing themes. An import that adds an external font also needs *Can add font*. |

A theme's images are part of the theme: anyone who can change a theme can upload
and choose its images, edit their alt text, and delete ones nothing uses (in
**Media**). The image model's own permissions aren't used.

*Can add font* also lets someone add an external font, whose stylesheet then
loads on every page once a theme using it is published, so treat it like
`edit_custom_css`.

For example, a "Designer" group with view, add and change can edit drafts, while
only an "Editor" group with `publish_theme` as well can make changes live.
Superusers have every permission.

## Export and import

Move a theme between sites (for example from staging to production):

1. On the theme's admin page, **Export** downloads `<slug>.capy-theme.zip`:
   `theme.json` (the draft: bases and settings) plus the images and font files it
   uses. Generated files (logo copies, icons) aren't included; they're made again.
2. On the other site, **Import theme** (on the theme list) uploads the zip. It
   needs the `import_theme` permission.

The import arrives as a new, **unpublished draft**; publish and activate it when
it looks right. Everything is checked first: the zip's size (50 MB unpacked at
most, or `CAPY_THEME_IMPORT_MAX_BYTES`) and file names, `theme.json` against
`src/capy_theme/portability/theme_file.schema.json`, the base themes and settings
like any theme, images through the same checks as uploads, and font files like
font uploads. Fonts already in the library (same family name) are reused. If a
theme with the same name or slug exists, " (imported)" / "-imported" is added. If
anything fails, nothing is kept.

From code: `capy_theme.portability.export.export_theme(theme)` returns the zip's
bytes, and `capy_theme.portability.importing.import_theme(file)` returns the new
theme. They don't check permissions themselves. From your own view, pass the
user's:

```python
can_css = user.has_perm("capy_theme.edit_custom_css")
export_theme(theme, keep_custom_css=can_css)
import_theme(
    file, keep_custom_css=can_css, can_add_external_fonts=user.has_perm("capy_theme.add_font")
)
```

### From the command line

The same, plus publishing, as management commands (in the demo, use
`uv run python demo/manage.py …`):

```bash
uv run python manage.py theme_export main -o main.capy-theme.zip   # default file: <slug>.capy-theme.zip
uv run python manage.py theme_import main.capy-theme.zip            # as a draft
uv run python manage.py theme_import main.capy-theme.zip --activate # publish it and make it the site's theme
uv run python manage.py theme_publish main --note "New colors" --activate
uv run python manage.py theme_rebuild_images                        # every theme, or give a slug
```

So a fresh install can be themed without the admin:

```bash
uv run python manage.py migrate
uv run python manage.py capy_theme_add_fonts        # only if the theme uses the bundled fonts
uv run python manage.py theme_import main.capy-theme.zip --activate
```

`theme_rebuild_images` remakes the logo copies and sharing-image crops from the
uploaded originals, and the icons of published revisions. Use it after a
capy-theme update changes how they're made, or for logos moved into the main
slot by migration 0010 (they have no smaller copies until then).

