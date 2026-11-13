# tests/

**The automated tests**, about 740 of them, run with `uv run pytest`. They're written with pytest and pytest-django. The folders mirror `src/capy_theme/`, so each section's tests sit in a folder of the same name.

**How they run:**

- **Against a minimal stand-in project** (`tests/settings.py` and `tests/urls.py`), not the demo. This proves capy-theme works in any project.
- **On SQLite in memory** by default, or Postgres with `DATABASE_URL`. CI runs both.
- **With no internet:** Google Fonts is faked, and fonts and images are built in code.
- **Strictly:** a Django deprecation warning fails them, and coverage must stay at least 80% (`uv run pytest --cov`).

| Item | What |
| --- | --- |
| `settings.py`, `urls.py` | The stand-in project |
| `support/` | Shared helpers: tiny real fonts, a fake Google Fonts, GIF builders |
| `test_app.py`, `test_demo.py`, `test_logging.py`, `test_project_settings.py`, `test_developer_docs.py` | Whole-app checks |
| `admin/`, `artifacts/`, `colors/`, `css/`, `editor/`, `fonts/`, `images/`, `portability/`, `themes/` | Each section's tests |

Every test file's opening line names the issue it came from. Each `__init__.py` is empty and only makes its folder a package.
