# src/capy_theme/themes/models/revision.py

**What it is:** the `ThemeRevision` model, a **published, frozen copy** of a theme's look. It's created only by `publish()` and never edited. It's deleted only along with its theme.

**Fields:**

- `theme`, `number`: 1, 2, 3... per theme, unique together.
- `snapshot`: the theme's `snapshot()` at publish time. Everything pages, the API and downloads read comes from here, never the draft.
- `css_version`: a short unique hash that names this revision's stylesheet URL (`/theme/<css_version>.css`). A new revision means a new URL, so browsers can cache each one for a year.
- `note`, `published_by` (a user, via `AUTH_USER_MODEL`), `published_at`.
