# pyproject.toml

**What it is:** the Python project's definition: the package's name and version, what it needs, and the settings for every tool.

**Sections:**

- **`[project]`:** name `capy-theme`, version `0.7.0`, MIT license, Python 3.14 or newer. The runtime dependencies, each with a comment saying why:
  - Django 6.1
  - coloraide (color formats and OKLCH)
  - defusedxml (safe SVG parsing)
  - fontTools (checking and converting fonts)
  - jsonschema (validating theme settings)
  - Pillow (images)

  The classifier `Private :: Do Not Upload` stops an accidental upload to the public PyPI.
- **`[build-system]` / `[tool.uv.build-backend]`:** builds with `uv_build`, and only `src/capy_theme` goes in the package.
- **`[dependency-groups] dev`:** tools only for developing:
  - pytest, pytest-django and pytest-cov
  - Postgres support for tests
  - ruff, pre-commit and pip-audit
  - the demo's Tailwind tool
  - DRF and drf-spectacular, only to test the optional DRF API
- **`[tool.pytest.ini_options]`:** tests use `tests.settings`, and a Django deprecation warning fails the tests, so Django upgrades never surprise you.
- **`[tool.ruff]`:**
  - lines up to 100 characters, migrations excluded
  - rule sets include `S` (security, instead of bandit) and `DJ` (Django)
  - tests may use `assert` and test passwords
  - the demo settings may have its dev-only secret key
- **`[tool.coverage]`:** measures `capy_theme` (not migrations), including both sides of every if/else, and fails below 80%.
