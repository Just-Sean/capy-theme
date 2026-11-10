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

## 6.1 Mode settings and toggle (#46), brought into v0.1.0

- **Chosen by Sean:** built now, before v0.1.0, after testing showed no way to
  switch between light and dark.

Recommended (made while building):

### Where the settings live
- **Chosen:** "Default mode" (auto, light, dark) and "Visitors can switch" are
  theme settings in a new **Mode** section of the admin, published like
  everything else. They're stored only when they differ from the defaults
  (auto, can switch).
- **Alternative:** project settings in `settings.py`.
- **Why:** they're part of a site's look, which operators control from the admin.

### No flash: server first, script as well
- **Chosen:** `{% theme_html_attrs %}` renders the forced mode on `<html>` from the
  cookie, so the page arrives in the right mode. The head script repeats it
  before the page draws (for cached pages) and makes the toggle instant.
- **Alternative:** only the script.
- **Why:** the server-side attribute works even without JavaScript.

### The toggle works without JavaScript
- **Chosen:** each button is a link to `/theme/mode/<mode>/?next=…`, which sets the
  cookie and redirects back (only to this site). With JavaScript, the click is
  handled in place.

### Cookie
- `capy_theme_mode`, one year, `SameSite=Lax`, readable by JavaScript (it holds
  only the mode). Ignored when the theme doesn't allow switching.

### CSP nonce
- The script gets Django 6.1's built-in CSP nonce
  (`django.middleware.csp.get_nonce`) when the CSP middleware is on, and none
  otherwise.

### Checking the script
- There's no Node.js here, so the generated script was checked by parsing it with
  `esprima` (run in a throwaway environment, not added to the project) for both
  settings combinations, and by the end-to-end check on the demo server.

## Plan reordered after v0.1.0 (#95)

All chosen by Sean, after testing v0.1.0 and asking for a live edit mode.

- **A live editor is the main way to edit a theme's look:** a panel on top of
  the real page, where every change shows instantly. The admin form stays as a
  plain fallback.
- **It comes straight after colours** (new Phase 3, was Phase 5). Fonts (now 4)
  and images (now 5) add their controls straight into it, instead of building
  admin widgets the editor would replace.
- **Phase 2 is the colours "engine":** data, colour maths and contrast on the
  server, with plain admin fields. The colour picker, contrast badges and palette
  suggestions (2.5, now 3.4) are in the editor.
- **The editor starts on the showcase**, then works on any page (3.6).
- **Data safety:** derived values (text colours, contrast) come from the server
  with the same code as publishing (3.2). Nothing is stored until Save draft,
  and nothing reaches visitors until Publish.
- Issue numbers stayed the same; titles, milestones and labels were updated.
  Entries above this one use the original step numbers (e.g. Phase 4 for
  images, now Phase 5; 5.4 for restore, now 3.7).
- **For this project only, Sean let Claude run the rest of the build on its own:**
  creating issues, opening and merging PRs, and tagging releases.

## 2.1 Colour overrides (#14)

Recommended (made while building autonomously).

- **Stored as** `settings["colors"]["light" | "dark"][name]`, using daisyUI's
  names without `--color-` (e.g. `primary`, `base-100`, `primary-content`). Only
  the colours set are stored.
- **Merged when the stylesheet is written**, from the revision's saved base
  values plus its overrides (`colors.effective_values`). The same function will
  serve the editor's preview.
- **Groups:** Basic = primary, secondary, accent, neutral, background (base-100),
  text on background (base-content); Advanced = info, success, warning, error,
  base-200, base-300; Expert = the eight `-content` colours. Advanced and Expert
  are folded in the admin.
- **OKLCH only for now:** fields accept `oklch(...)` values (daisyUI's own
  format). 2.2 adds hex, RGB and HSL input, converted to OKLCH.
- **Empty fields show the base colour as a greyed-out hint.**

## 2.2 Colour input (#15)

Recommended (made while building autonomously).

- **ColorAide** (`coloraide>=8,<9`) reads hex, rgb(), hsl(), oklch() and colour
  names, and converts to OKLCH, as the issue specified.
- **Stored text:** daisyUI-style `oklch(L% C H)`, rounded (2 decimals for L and H,
  4 for C) with trailing zeros dropped, and `/ alpha` only when transparent. So
  `oklch(62% 0.19 260)` comes back unchanged, and `#3b82f6` becomes
  `oklch(62.31% 0.188 259.81)`.
- **Admin picker:** the browser's own `<input type="color">` beside the text box,
  linked by a small static script (not inline, so it works under a strict CSP).
  It works in hex, so picking writes hex into the box, which is converted to OKLCH
  on save. The full picker is the editor's (3.3).

## 2.3 Automatic text colours and background shades (#16)

Recommended (made while building autonomously).

- **When it applies:** only for colours the theme overrides. A colour's text
  colour is worked out when the colour is set but its `-content` isn't. base-200,
  base-300 and base-content are worked out when base-100 is set but they aren't.
  Untouched colours keep the base theme's values, and anything set by hand wins.
- **Text colour:** a very light (98%) or very dark (22%) tint of the colour's own
  hue, whichever has the higher WCAG contrast. If neither tint reaches AA (4.5:1),
  which happens only on some mid-tones, pure white or black is used instead,
  because nothing reads better on those.
- **Background shades:** 2.5% and 5% darker in OKLCH lightness (daisyUI's own
  themes step about the same). Very dark backgrounds get lighter shades instead.
- **Worked out when the stylesheet is written,** from the revision's saved values,
  in `colors.effective_values()`, the same function the editor will use.

## 2.4 Contrast warnings (#17)

Recommended (made while building autonomously).

- **Pairs rated:** each of the eight colours with its text colour, plus the three
  backgrounds (base-100/200/300) with the text on them.
- **Ratings:** WCAG 2 contrast for normal-size text: AAA at 7:1, AA at 4.5:1,
  otherwise "fails AA". Calculated on the server with ColorAide (`wcag21`).
- **Where:** in each colour field's help text (both colours of a pair show it),
  and a full table in a **Contrast** section. Both use the **saved draft**,
  through the same merging as publishing, so they match what would be published.
  Live ratings as you type come with the editor (3.3).
- **Warnings only:** nothing stops saving or publishing.

## 2.6 Shape and effects (#19)

Recommended (made while building autonomously).

- **One set for both modes:** shape settings apply to light and dark alike.
  daisyUI's own light and dark themes share their shape, and a card shouldn't
  change roundness when the mode changes.
- **Stored as numbers and booleans** in `settings["shape"]` (rem for radii and
  sizes, px for border), written out with their units.
- **Limits:** radii 0–2 rem (boxes 0–3), sizes 0.125–0.5 rem (daisyUI uses
  0.1875–0.3125), border 0–4 px. They keep the components usable.
- **Depth and noise** have three choices, "From the base theme", On and Off, so
  "not set" is possible (a plain checkbox can't express it).
- **Hints:** blank fields show the light base's value.

## 2.7 Browser colour, focus colour and email colours (#20)

Recommended (made while building autonomously).

- **theme-color** comes from the page background (base-100), as hex (browsers
  don't all accept OKLCH there). Two tags with `prefers-color-scheme` media
  queries when the mode follows the device; one tag when a mode is forced.
- **Focus colour** is worked out, not a separate setting: primary if it has at
  least 3:1 contrast with base-100 (WCAG 2's non-text minimum), else base-content.
  It's written as `--capy-focus` in each block, and an unlayered
  `:focus-visible { outline: 2px solid var(--capy-focus) }` rule applies it
  everywhere, overriding daisyUI's own focus outlines.
- **Email colours** are the light-mode colours (emails have no dark mode to rely
  on) as `#rrggbb`, keyed with underscores (`base_100`) so templates can use dot
  lookups.

## 2.8 Showcase: colours and shape (#21)

Recommended (made while building autonomously).

- **Swatches use the live CSS variables** (`var(--color-primary)`) inside each
  mode's column, so they show exactly what pages get. The values and ratings
  shown next to them come from the same `effective_values()` as the stylesheet.
- **Where a colour comes from** is labelled "overridden", "worked out" (automatic
  text colours and background shades from 2.3) or "base theme".
- **Contrast** uses the same ratings and "⚠ fails AA" wording as the admin.
- **Shape samples** draw boxes with each radius, real controls for sizes and
  border, and every effect shown both off and on (by setting `--depth` / `--noise`
  on the sample), plus a table of the current values.
- A small `capy_get` template filter looks up each mode's data by name.

## 2.9 Release v0.2.0 (#22)

- Released with tests passing on SQLite and PostgreSQL 17 (throwaway Docker
  container), and the package checked. No database migrations were needed in
  Phase 2: colours and shape live in the theme's `settings` JSON.

## 3.1 Editor on the showcase (#42)

Recommended (made while building autonomously).

- **Who:** staff with the change-theme permission (`editor.can_edit`). Publishing
  from the editor will also need `publish_theme` (3.5).
- **Which theme:** the active theme, or `?edit=<id>`. `?edit` also opens the panel
  on load, which the admin's "Edit live" link (3.8) will use.
- **Preview for that user only:** the draft's CSS is added in the browser as a
  constructed stylesheet (`document.adoptedStyleSheets`) after the page's own, so
  it wins. Constructed stylesheets aren't blocked by a CSP the way `<style>`
  elements are, and nothing changes for anyone else.
- **One source of truth:** the draft's CSS comes from `/theme/editor/<id>/state/`,
  written by `stylesheet.snapshot_css()`, the same function as published
  stylesheets (a test checks they match).
- **Self-contained panel:** plain CSS and JavaScript, no Tailwind or daisyUI
  classes and no framework, so it works on any project page later (3.6).
- **Tested in a real browser:** headless Chrome, driven over the DevTools
  protocol by a script kept outside the repo. It checked that the panel opens,
  the page shows the draft colour, Close restores the published one, and
  reopening works.

## 3.2 Draft preview endpoint (#96)

Recommended (made while building autonomously).

- **One endpoint:** `POST /theme/editor/<id>/preview/` takes JSON with any of
  `light_base`, `dark_base` and `settings` (`colors`, `shape`) and returns
  `css`, `values` (every variable, per mode), `contrast` (per mode) and the
  cleaned `settings`.
- **Same code as publishing:** it applies the changes to an unsaved copy of the
  theme (`editor.apply_changes`) and runs `snapshot()`, `effective_values()` and
  `snapshot_css()`, so the preview matches what publishing would produce (tested).
- **Never writes:** no save on the copy, `no-store` on the response. Other
  settings (site name, mode and so on) are left as they are.
- **Validation:** colours in any format are converted to OKLCH, bases are
  checked against the catalogue, and the schema is checked. All problems come back
  as a 400 with a list, which the panel shows.
- **CSRF:** a normal Django POST. The token is passed to the script with a data
  attribute, because Django's CSRF cookie may be HttpOnly in projects.
- **Debounced in the browser:** `capyEditor.schedulePreview()` waits 150 ms after
  the last change, so dragging a picker sends one request, not dozens.

## 3.3 Colour and shape controls (#97)

Recommended (made while building autonomously).

- **Controls come from the server:** the state endpoint lists the allowed bases
  (following `CAPY_THEME_BUILTIN_THEMES`), the colour groups and labels, and the
  shape settings with their limits, so the panel never duplicates that knowledge.
- **Colour rows:** the browser's colour picker, a text box for any format, Reset
  and a contrast badge. Picking writes hex, and the server converts it to OKLCH.
  The picker is set from hex values the server provides (`hex` in the preview).
- **Light and dark tabs** edit each mode's colours separately. Shape is shared.
- **Every change is previewed** through the 150 ms debounce. `capyEditor.changes`
  holds the unsaved values for Save (3.5).
- **A separate script**, `editor-controls.js`, listens to the editor's
  `capy-editor:loaded` and `capy-editor:preview` events, so the panel shell
  stays small.
- **Tested in headless Chrome** with real input events: picking a colour,
  switching tabs, reset, changing a base and changing a radius all update the
  page as expected, and nothing is saved.

## 3.4 Palette suggestions (#18)

Recommended (made while building autonomously).

- **From the primary colour:** three classic colour schemes in OKLCH, each
  keeping the primary's lightness and strength and changing only the hue:
  analogous (±30°), complementary (180° and 150°) and triadic (120° and 240°).
  Neutral is a dark (27%), nearly grey version of the primary's hue.
- **From the logo:** Pillow shrinks the logo and reduces it to 12 colours. It
  ignores transparent, near-white, near-black and grey areas and colours too
  close in hue to one already picked, then uses the rest in order of area as
  primary, secondary and accent.
- **Endpoint:** `POST /theme/editor/<id>/suggestions/` with the current primary.
  It writes nothing.
- **Applying** a suggestion fills those colours into the current mode's controls
  and previews them. Suggestions use the primary at the moment "Suggest colours"
  is clicked; click again after changing the primary for fresh ones.
- **Swatch colours** are set through the CSSOM (`element.style`), which a strict
  CSP allows, unlike `style=""` attributes.

## 3.5 Save draft and publish from the editor (#98)

Recommended (made while building autonomously).

- **Save draft** (`POST /theme/editor/<id>/save/`) runs the same validation as the
  preview, then saves only the bases, colours and shape. Other settings are read
  fresh from the database and kept, so an editor save doesn't undo branding or
  mode changes made in the admin meanwhile.
- **Publish** (`POST /theme/editor/<id>/publish/`, needs `publish_theme`)
  publishes the **saved** draft through the existing `publish()`, so revisions,
  the "Nothing to publish" check and the simultaneous-publish message all work
  as in the admin. If the panel has unsaved changes, it saves them first.
- **Unsaved changes** are tracked against what was last loaded or saved. The panel
  shows "Unsaved changes", and Close and leaving the page ask before discarding
  them.
- **Publish asks for confirmation**, with a browser confirm dialog, since it
  changes what visitors see.

## 3.6 Edit on any page (#43)

Recommended (made while building autonomously).

- **Loaded by `{% theme_head %}`** for staff with the change permission, so it
  works on every page that uses it, with no template changes. Visitors get none
  of its files. The showcase no longer loads it separately (one editor per page).
- **Settings on the `<script>` tag:** `{% theme_head %}` is in `<head>`, where a
  `<div>` isn't allowed, so the editor's URLs and token are data attributes on
  its script element.
- **Corner button and banner:** a small "Edit theme" button in the corner of
  every page (`CAPY_THEME_EDITOR_BUTTON = False` hides it). While editing, a
  banner says only this user sees the draft, with an Exit button.
- **`?edit=<id>` works on any page,** even when no theme is active.
- **No crash without auth:** requests without a user (no auth middleware) simply
  don't get the editor.

## 3.7 History: compare and restore (#44)

Recommended (made while building autonomously).

- **A Revisions page in the admin** (next to History and Publish on the theme
  page): the compare form, the result, and every revision with a Restore button.
- **Compare** lists only what differs, by readable name (e.g. "Light colour:
  Primary", "Shape: Box corner radius"). "Base theme / not set" means the value
  came from the base theme. Defaults to the last two revisions.
- **Restore never rewrites history:** it copies the revision's bases, logo and
  settings into the draft and publishes a new revision noted "Restored revision
  N". Restoring what's already live says so. It replaces unpublished draft
  changes, and the confirmation page says so and shows what will change.
- **Base values on restore:** as with any publish, the base themes' values come
  from the catalogue the module ships now. If daisyUI changed a base since the old
  revision, the restored look uses today's base, and the #78 notice explains it.
  (Keeping the old values exactly would need a second publishing path.)

## 3.8 Admin form tidy-up (#41)

Recommended (made while building autonomously).

- **Order follows how people work:** name, publishing, base themes, branding,
  colours, contrast, shape, mode, then Advanced (stored JSON, ID and dates).
  Contrast, Shape and Advanced are folded, as are the Advanced and Expert colours.
- **Edit live** on the theme page opens the live editor for that theme: on the
  showcase (all components at once), or on the home page if the showcase is turned
  off. Only for staff who can edit.
- **Short descriptions** on the first sections point people to Edit live and
  explain what the bases do.

## 3.9 Release v0.3.0 (#45)

- Released with tests on SQLite and PostgreSQL 17, the package checked, and each
  editor step checked in headless Chrome while it was built. No database
  migrations were needed in Phase 3.

## 4.1 Font library and roles (#23)

Recommended (made while building autonomously).

- **Models:** `Font` (family, source, fallback stack, licence, stylesheet URL for
  external fonts) and `FontFile` (weight, style, subset, unicode-range, WOFF2
  file), as the issue described.
- **Themes pick fonts by id** in `settings["fonts"]` for body, heading, mono and
  display. Unknown ids are refused when saving.
- **Copied into revisions:** at publish, each chosen font's family, source,
  fallbacks and file URLs go into the snapshot, the same principle as base colour
  values. Library changes can't change a published theme. The `fonts` key is only
  added when fonts are chosen, so existing revisions still compare equal.
- **How fonts apply:** body sets Tailwind's `--font-sans`, so Tailwind/daisyUI
  pages pick it up, and mono sets `--font-mono`. Headings and display get their
  own variables, used by `h1`–`h6` and `.capy-display`. Element rules are in
  `@layer base`, so project utility classes still win. The variables themselves
  are unlayered, so they override Tailwind's defaults.
- **Fonts are the same in light and dark mode.**
- **Editor:** a Fonts section with a dropdown per role, previewed live, saved
  and published like everything else.

## 4.2 System font stacks (#24)

Recommended (made while building autonomously).

- **Fonts in the library** with source "system" and no files: the stack is their
  fallback stack, written out as-is (no `@font-face`, no download).
- **Added by migration 0008,** so every project has them after `migrate`.
  Existing fonts with the same name are left alone. Removing the migration
  deletes only these system fonts.
- **13 stacks:** System sans, serif and mono, plus ten from Modern Font Stacks
  (CC0), which list fonts that ship with Windows, macOS, Linux, iOS and Android.

## 4.3 Curated font collection (#25)

Recommended (made while building autonomously).

- **30 fonts:** 15 sans, 9 serif, 4 mono and 2 display, chosen as widely used,
  well-made Google Fonts families. All are SIL Open Font License 1.1, which
  allows bundling as long as the licence goes with them; the script refuses any
  other licence.
- **From Fontsource npm packages, pinned by version,** fetched by
  `scripts/fetch_curated_fonts.py`, the same approach as the daisyUI catalogue.
  Each package's LICENSE is kept next to its files.
- **Only Latin regular, bold and italic** (where the font has them): 84 files,
  about 1.9 MB, keeping the package small. Other weights and character sets can
  be uploaded (4.4) or imported from Google Fonts (4.5).
- **The command copies the files into the project's media storage**
  (`capy_theme_add_fonts`), so bundled fonts are stored and served exactly like
  uploaded ones, on any storage backend, and their URLs go into revisions the same
  way. Existing families are skipped.
- **Previews:** the admin font list draws a sample of each font, and the editor
  shows a sample line under each font choice.
- **Tested in Chrome:** all 30 fonts loaded from the copied files, with none
  failing.

## 4.4 Font uploads (#26)

Recommended (made while building autonomously).

- **fontTools with WOFF support** (`fonttools[woff]`, which brings Brotli and
  Zopfli), as the issue specified.
- **Every upload is parsed by fontTools**: anything that isn't a font is refused.
  Size limit: 5 MB per file (`CAPY_THEME_FONT_MAX_BYTES`).
- **Converted to WOFF2** whatever the input (WOFF2, WOFF, TTF, OTF).
- **Trimmed to Latin by default,** since most sites need only that and it shrinks
  files a lot (a 692 KB DejaVu Sans Bold became 24 KB). Other subsets use Google
  Fonts' standard ranges, the file gets the matching `unicode-range`, and "All
  characters" keeps everything.
- **Weight and style are read from the font** (OS/2 weight class, italic flags)
  when left blank. The family name read from the font is available for the
  Google Fonts import (4.5).
- **fontTools' notes about dropped tables are silenced** while trimming, to keep
  project logs clean.

## 4.5 Google Fonts import (#27)

Recommended (made while building autonomously).

- **The official Google Fonts CSS API** (`fonts.googleapis.com/css2`) says which
  WOFF2 files a family has, per character subset. The server downloads them once
  from `fonts.gstatic.com` and stores them like uploads, so pages never contact
  Google (checked in Chrome: no Google requests).
- **A browser User-Agent** is sent, because the API picks the file format from it.
  It's a generic Chrome string, nothing about the site or user.
- **Missing weights:** the API refuses the whole request if one weight is missing,
  so the import then asks weight by weight and keeps those that exist.
- **Variable fonts** reuse one file for several weights: each file is downloaded
  and stored once, and shared by the weights' FontFile rows.
- **Safety:** family names must be letters, digits and spaces; downloads are only
  allowed from the two Google Fonts addresses over https; each file is checked by
  fontTools (as uploads are).
- **Default:** regular, bold and italic in Latin, changeable in the form.
