# tests/settings.py

**What it is:** the smallest Django project that can run capy-theme. It stands in for "any project that installs the module". If capy-theme only worked inside one particular project, the tests would fail.

- **Apps:** Django's standard apps and capy-theme, plus Django REST Framework and drf-spectacular, so the API's DRF mode and API docs can be tested.
- **DRF defaults:** set to require login, which is stricter than DRF's own default, to **prove** the theme API stays public anyway.
- **Database:** SQLite in memory, or Postgres via `DATABASE_URL`.
- **Secret key:** a tests-only key. Ruff allows it in tests.
