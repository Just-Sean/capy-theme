# src/

Holds only the Python package `capy_theme`. This "src layout" means the tests run against the package as installed, not by accident against loose files in the repo root. Only `src/capy_theme/` is built into the package (`pyproject.toml`: `module-name = "capy_theme"`).
