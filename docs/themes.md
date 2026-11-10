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

The admin page is the plain fallback to the live editor. Its sections, top to
bottom:

1. Name and slug
2. Publishing status
3. Base themes
4. Branding
5. Colours (light and dark; Basic open, Advanced and Expert folded)
6. Contrast (folded)
7. Shape and effects (folded)
8. Mode
9. Advanced (folded: stored settings, ID and dates)

At the top right: **Edit live** opens the theme in the live editor (on the
showcase, or the home page if the showcase is off), next to **Revisions**,
**Publish** and Django's **History**.

## Branding

On a theme's admin page, the **Branding** section has the site name, tagline
and logo alt text, stored in the theme's `settings`. Logos are chosen in the
**Logos** section (see [Logos](images.md#logos)).

Like everything else, branding changes show on the site only after publishing.

## Drafts and publishing

Editing a theme in the admin changes only its **draft**. Pages will use the
theme's **live revision**, which changes only when someone publishes:

- On a theme's edit page, click **Publish** (needs the `publish_theme` permission). A confirmation page shows what's
  live now and has an optional note box. Publishing copies the draft's look
  (light base, dark base and `settings`) into a new numbered `ThemeRevision`,
  recording who published it and when, and makes it the live revision.
- If the draft matches the live revision, publishing is refused ("Nothing to publish").
- The name and slug aren't part of a revision, so renaming takes effect without publishing.
- Revisions can't be edited or deleted. They're listed on the theme's edit page,
  and removed only if the theme itself is deleted.
- **Revisions** (button on the theme's edit page) lists every revision and
  **compares** any two, showing exactly which values changed (bases, logo,
  branding, mode, each colour and each shape setting).
- **Restore** (needs `publish_theme`) copies an old revision into the draft and
  publishes it **as a new revision**, noted "Restored revision N". Nothing in the
  history is deleted, and the site shows it straight away.

From code: `from capy_theme.themes.publishing import publish` then `publish(theme, user=request.user, note="…")`.

## The active theme

One theme is the site's **active** theme. To choose it, tick it in the admin's
theme list and run the **Activate** action (needs the `publish_theme` permission). The list's "Active" column shows
which one it is. A theme must be published before it can be activated.

From code: `from capy_theme.themes.active import get_active_theme` then
`get_active_theme(request)` returns the active `Theme`, with its live revision
loaded, or `None` if no theme is active. It's cached (see
`CAPY_THEME_CACHE_SECONDS`), so a normal page load doesn't query the database.

## Scheduled themes

A theme can be live between two dates, e.g. a holiday theme. In the admin, go
to **Capy Theme → Theme schedule → Add**, choose a published theme and give a
start and/or end date (blank start: straight away; blank end: until removed).
While a schedule is running (start ≤ now < end) its theme replaces the site's
default; afterwards the default returns by itself. If schedules overlap, the one
that started most recently wins. A visitor's own choice (below) still wins over
both. The list shows each schedule as Upcoming, Running or Finished. Scheduling
needs the `publish_theme` permission, like activating.

The cached theme expires at the next start or end, so schedules switch on time
even with a long `CAPY_THEME_CACHE_SECONDS`.

## Visitor theme picker

Visitors can choose among themes the operator offers:

1. In the admin, tick **Offer to visitors** on each theme to offer, and publish it.
2. Put `{% theme_picker %}` where visitors should choose (the demo has it in a
   **Theme** dropdown in the navbar). It lists **Site default** and the offered
   themes, and outputs nothing if none are offered.

Each option is a link to `/theme/choose/<slug>/` (or `/theme/choose/default/`),
which stores the choice in the `capy_theme_choice` cookie and goes back to the
page. Only offered, published themes are used; any other value in the cookie is
ignored, so visitors can't force a theme. `CAPY_THEME_VISITOR_THEMES = False`
turns the whole feature off. Pages then depend on that cookie, so a project that
caches whole pages must vary its cache on it.

## Light and dark mode

On a theme's admin page, the **Mode** section has:

- **Default mode:** *Auto* (follow the visitor's device setting), *Light* or *Dark*.
- **Visitors can switch** (on by default): shows `{% theme_mode_toggle %}`, three
  buttons (Light, Dark, Auto). A visitor's choice is kept in the `capy_theme_mode`
  cookie for a year.

Like everything else, these take effect when the theme is published.

How it works: the server puts `data-theme="capy-light"` or `"capy-dark"` on
`<html>` (`{% theme_html_attrs %}`) when a mode is forced, so pages arrive in the
right mode with no flash. For "auto" it adds nothing, and the stylesheet follows
the device. The script from `{% theme_head %}` does the same before the page
draws (so cached pages are right too) and makes the buttons switch instantly.
Without JavaScript, each button is a link to `/theme/mode/<light|dark|auto>/`,
which sets the cookie and comes back to the page. The script carries Django's
CSP nonce when the project uses Django's CSP middleware.

## Permissions

Editing themes uses Django's normal model permissions (view, add, change, delete
theme). capy-theme adds three more, given to users or groups in the admin under
**Authentication and Authorization**:

| Permission | Allows |
| --- | --- |
| `capy_theme.publish_theme` | Publishing a theme, activating it, and restoring old revisions. Without it, the Publish button and the Activate action are hidden, and direct requests are refused. |
| `capy_theme.edit_custom_css` | Editing a theme's custom CSS (from 8.1). |
| `capy_theme.import_theme` | Importing themes (from 7.3). |

For example, a "Designer" group with view, add and change can edit drafts, while
only an "Editor" group with `publish_theme` as well can make changes live.
Superusers have every permission.
