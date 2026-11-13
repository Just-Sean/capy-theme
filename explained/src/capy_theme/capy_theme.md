# src/capy_theme/

**The app itself:** everything a project installs. It's a normal Django app (`INSTALLED_APPS += ["capy_theme"]`), organized by job, one job per file.

| Folder | Job |
| --- | --- |
| `themes/` | The Theme and revision models, publishing, history, which theme is live (sites, schedules, visitor choice), light/dark mode, validation |
| `colors/` | Color math, the 20 color names, automatic text colors and contrast, palette suggestions |
| `css/` | Writing the theme stylesheet: colors, shape, type, fonts, logos, backgrounds, accessibility, custom CSS |
| `fonts/` | The font library: uploads, Google Fonts import, bundled fonts, font stacks |
| `images/` | Image uploads and cleaning, SVG sanitizing, logo slots and copies, icons, the sharing image |
| `editor/` | The live editor's server side: state, preview, save, publish, upload, visitor view, Components view |
| `artifacts/` | The theme as data for other code: `get_artifacts()`, the JSON API, design tokens, daisyUI blocks |
| `portability/` | Export and import as a zip |
| `admin/` | Django admin pages for themes, fonts, schedules and site themes |
| `templatetags/` | `{% theme_head %}`, `{% theme_logo %}` and the other template tags |
| `management/commands/` | Command-line commands (export, import, publish, rebuild images, add fonts) |
| `migrations/` | Database schema changes |
| `templates/capy_theme/` | HTML templates (admin pages, editor, mode toggle, picker) |
| `static/capy_theme/` | The editor's JavaScript and CSS, an admin script, the 30 bundled fonts |

**Files at this level:** `__init__.py`, `apps.py`, `models.py`, `conf.py`, `context_processors.py`, `urls.py`.

**Rules:** never imports from a project. Users are linked with `settings.AUTH_USER_MODEL`, data lives in JSON files, and settings start with `CAPY_THEME_`.

**`__pycache__/` folders** (here and in every subfolder) are Python's compiled-bytecode caches: build artifacts, git-ignored.
