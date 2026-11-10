# Decisions

Design decisions made while building capy-theme, newest last. Each says which
issue it came from, what was chosen, the alternatives, and why. Any of them can
be revisited: open an issue that names the decision.

"Chosen by Sean" means it was asked and answered. "Recommended" means it was
made using Claude's recommendation while building without a stop for every
decision (from 1.7 onwards), to be reviewed later.

## 1.1 Built-in theme catalogue (#4)

### Where the theme data comes from
- **Chosen by Sean:** the generator script downloads the published daisyUI package
  from npm (pinned version) and reads `theme/object.js` and `functions/themeOrder.js`.
- **Alternative:** extract the themes from the demo's bundled `daisyui.mjs`.
- **Why:** the npm files are plain data meant for this. The bundle is JavaScript
  code and would need fragile pattern matching (and Node.js isn't installed).

### Generated data and function in separate files
- **Chosen by Sean:** `builtin_themes.py` is generated data only; `get_builtin_themes()`
  lives in hand-written `catalogue.py`.
- **Alternative:** the script writes both into `builtin_themes.py`.
- **Why:** regenerating never touches hand-written code.

### Unknown names in `CAPY_THEME_BUILTIN_THEMES`
- **Chosen by Sean:** raise `ImproperlyConfigured` naming the unknown theme.
- **Alternative:** silently ignore them.
- **Why:** typos are caught immediately.

## 1.2 Theme model (#5)

### Validating `Theme.settings`
- **Chosen by Sean:** a JSON Schema file (`settings.schema.json`) checked with the
  `jsonschema` package.
- **Alternative:** hand-written Python checks.
- **Why:** clear error messages, and the same schema can be reused for import (7.3)
  and the API (7.1).

### Which themes can be bases
- **Chosen by Sean:** the light base must be a light theme, the dark base a dark theme.
- **Alternative:** any theme for either.
- **Why:** prevents a dark theme being used in light mode by mistake.

### Name and slug
- **Chosen by Sean:** both unique; the slug is filled in from the name and editable.
- **Alternative:** only the slug unique.

### Bases aren't Django `choices`
- **Made by Claude, explained to Sean:** the allowed list depends on the
  `CAPY_THEME_BUILTIN_THEMES` setting, and `choices` would be written into migrations
  and create new ones whenever a project's setting differs. Checked in validation
  instead; the admin builds the dropdowns when the form loads.

### Bad data is refused on every save
- **Made by Claude:** `Theme.save()` runs the checks, not only the admin form.
- **Why:** the issue says bad data can't be saved, from code as well.

## 1.3 Revisions and publishing (#6)

### What a revision copies
- **Chosen by Sean:** the look only (light base, dark base, settings), not the
  name or slug, so renaming needs no publish.

### Publish button
- **Chosen by Sean:** a confirmation page with an optional note.
- **Alternative:** one click, no note.

### Publishing with no changes
- **Chosen by Sean:** refused with "Nothing to publish".
- **Alternative:** allow an identical revision.

### Revisions can't be edited or deleted
- **Chosen by Sean:** they're kept as history (for compare and restore in 5.4) and
  go only when their theme is deleted.
- **Alternative:** deletable except the live one.

### Simple `publish()`, no lock
- **Chosen by Sean (after a bug):** `publish()` works on the theme object it's given,
  with no reload or row lock. A normal save never writes `live_revision`; only
  publishing does.
- **Why:** the first version reloaded the theme with a lock, and the second copy
  caused a bug where saving undid a publish. The database's unique revision
  numbers already stop duplicates.

### Two publishes at the same moment
- **Chosen by Sean:** the second person sees "Someone else just published this
  theme…" instead of a server error.

## 1.4 Active theme selection (#7)

### Activating an unpublished theme
- **Chosen by Sean:** refused with "Publish “X” before activating it".

### Admin
- **Chosen by Sean:** an Activate action and an "Active" column only; no separate
  assignments page until scheduling (6.3) and multiple sites (8.2) need one.

### Cache time
- **Chosen by Sean:** 5 minutes by default, changeable with `CAPY_THEME_CACHE_SECONDS`.
- **Alternative:** never expire.
- **Why:** with Django's default in-memory cache, each server process has its own
  cache, so clearing it in one doesn't clear the others. The time limit makes
  them catch up.

### Smaller choices (made by Claude)
- Activating switches the single default assignment rather than adding rows.
- "No active theme" is cached too.
- The cache is cleared on any theme, revision or assignment change (simpler than
  working out which changes matter).

## 1.5 Theme stylesheet (#8)

### Revisions store full base values
- **Chosen by Sean:** each publish copies both bases' 28 values, not just their names.
- **Alternative:** store names and look values up in the catalogue.
- **Why:** a daisyUI update can't change or break a published theme. To pick up
  daisyUI changes, publish again.

### Old stylesheet URLs
- **Chosen by Sean:** each `/theme/<version>.css` always returns the revision it
  was made for.
- **Alternative:** old URLs return the current live CSS.
- **Why:** consistent with browsers caching each URL for a year.

### Smaller choices (made by Claude)
- Light and dark follow the visitor's device setting (`prefers-color-scheme`)
  until the toggle in 6.1.
- The rules aren't in a CSS layer, so they override daisyUI's `@layer base` rules
  wherever the stylesheet is loaded.
- Any revision's stylesheet can be opened by URL, not only the live one's.
- Migration 0004 was written by hand to fill in values and versions for older revisions.

## Notice when daisyUI changes a base (#78)

### A separate issue
- **Chosen by Sean:** done as its own issue right after 1.5.

### Smaller choices (made by Claude)
- A project limiting themes with `CAPY_THEME_BUILTIN_THEMES` isn't flagged; only
  real daisyUI changes are.

## 1.6 `{% theme_head %}` tag and theme context (#9)

### `{% theme_html_attrs %}`
- **Chosen by Sean:** added to templates now but outputs nothing until 6.1 gives it
  a job (forcing light or dark).
- **Alternative:** output `data-theme="<theme slug>"`.

### Smaller choices (made by Claude)
- The `theme` template variable holds name, slug, revision, both bases and the
  stylesheet URL, all from the **published** revision, or `None` without an
  active theme.

## 1.7 Site name, tagline and main logo (#10)

All recommended (made while building without a stop for every decision).

### Branding gets proper admin fields
- **Chosen:** site name, tagline and logo alt text get their own fields in the
  admin. They're stored as keys in `settings`. The raw `settings` JSON box is
  replaced by a read-only view.
- **Alternative:** keep editing `settings` as a JSON text box.
- **Why:** typing JSON by hand is error-prone, and every later setting will get
  a proper field too.

### Logo upload uses Django's ImageField and Pillow
- **Chosen:** `Theme.logo` is an `ImageField` (PNG, JPEG, GIF, WebP), adding
  `pillow>=13,<14` as a dependency.
- **Alternative:** a plain file upload with no image check.
- **Why:** Pillow confirms the file really is an image. Phase 4 needs it anyway
  for resizing. SVG logos and stricter upload checks come in 4.1 and 4.2.

### Revisions record the logo's file name
- **Chosen:** the snapshot stores the logo file's stored name. Replacing a logo
  saves a new file (Django never overwrites), so old revisions keep their logo.
- **Alternative:** copy the file per revision.
- **Why:** no duplicate files. Phase 4's assets are never edited in place either.

### `{% theme_logo %}`
- **Chosen:** outputs `<img src alt>` for the logo, or `<span>` with the site
  name. Extra attributes are passed through (`class="h-8"`). Alt text falls back
  to the site name. Outputs nothing if there's no active theme, or no logo and
  no site name.

### The demo's tests use a throwaway database
- **Chosen:** `tests/test_demo.py` runs the demo against an in-memory database it
  migrates itself, instead of `demo/db.sqlite3`.
- **Why:** since 1.6 the home page reads the database. The test failed whenever
  the local demo database wasn't migrated, and would fail on a fresh copy of the repo.

## 1.8 Theme showcase page (#11)

All recommended (made while building without a stop for every decision).

### A trimmed stylesheet instead of daisyUI's prebuilt CSS
- **Chosen:** bundle `showcase.css`, built by `scripts/build_showcase_css.py` with
  the Tailwind CLI and the daisyUI plugin from only the showcase templates
  (about 96 KB).
- **Alternative (the issue's wording):** bundle daisyUI's prebuilt `daisyui.css`.
- **Why:** that file is 1.1 MB (every component in every variant) and has no
  Tailwind layout classes (grid, flex, gap), which the showcase needs. The
  trimmed file has exactly what the showcase uses. The cost is a rebuild step
  after changing showcase templates or updating daisyUI (in the README).
- The build adds daisyUI's MIT licence notice back, since minifying drops it.

### Forcing light or dark on part of a page
- **Chosen:** the theme stylesheet also has `[data-theme="capy-light"]` and
  `[data-theme="capy-dark"]` rules, so any element can be forced into either
  mode. The showcase uses them to show both side by side. The light/dark toggle
  (6.1) can use the same rules on `<html>`.
- **Why:** before this, the stylesheet only set colours for the whole page from
  the device setting, so both modes couldn't appear at once.
- **Note:** this changed the CSS that existing stylesheet URLs return. Browsers
  that cached an older copy (for up to a year) won't see the new rules. That only
  affects development so far (nothing is released). How to handle future format
  changes is a separate issue.

### Access
- **Chosen:** with `"staff"`, logged-out visitors and non-staff users are sent to
  the admin login (like Django's staff-only views). `"off"` returns 404. An
  unknown value raises `ImproperlyConfigured`.

### Smaller choices
- With no active theme, the showcase shows daisyUI's default light and dark
  themes, with a notice.
- The modal and tabs work without JavaScript (checkbox and radio based), and
  their `id`s and `name`s include the mode so both copies work.
- The showcase's stylesheet link sits inside the `content` block, so it loads
  whether the showcase uses its standalone page or the project's base template.
- The demo's navbar gets a "Showcase" link.

## Stylesheet URL includes the package version (#86)

Recommended (made while building without a stop for every decision).

- **Chosen:** pages link the stylesheet as `/theme/<version>.css?v=<capy-theme version>`
  (`stylesheet.stylesheet_url()`, used by `{% theme_head %}`, the `theme` context
  and the admin link).
- **Alternatives:** a format number bumped by hand whenever `render_css()`
  changes; or naming the URL by a hash of the rendered CSS (needs rendering on
  every page).
- **Why:** browsers cache each stylesheet URL for a year, and the theme's
  version only changes on publish. A project only gets new CSS output by
  upgrading capy-theme, which changes the package version, so the new version in
  the URL makes browsers fetch it again. Nothing has to be remembered by hand.
  Found while building the showcase (1.8), which changed the CSS output.

## 1.9 Permissions (#12)

Recommended (made while building without a stop for every decision).

### `publish_theme` alone allows publishing and activating
- **Chosen:** publishing and activating check only `publish_theme`, not also the
  change permission.
- **Why:** publishing doesn't edit the draft; it makes the existing draft live.
  A user still needs view permission to reach the theme's page.

### How things are hidden
- The Publish button is hidden on the theme page without `publish_theme`, and the
  publish page returns 403 ("forbidden").
- The Activate action uses Django's action permissions, so it's left out of the
  actions menu, and Django ignores it if requested directly.
- Restore doesn't exist yet. It will check the same permission when it arrives
  in 5.4.

## 1.10 Release v0.1.0 (#13)

- **No version bump:** `pyproject.toml` was already `0.1.0` (the template's
  starting version), and nothing had been released, so v0.1.0 is that version.
- **Postgres tests (chosen by Sean):** run against a throwaway Docker container
  (`postgres:17` on port 55432), removed afterwards. The README has the commands
  for future releases.
- **Tagging:** follows the README's release steps. The release PR is merged first,
  then `v0.1.0` is tagged on the merged `main` and only the tag is pushed.
