# tests/test_app.py

**What it tests:** checks every module should keep passing.

- the app is installed, under the name "Capy Theme"
- **migrations are up to date:** it fails if a model changed without `makemigrations`, which would break every project that installs that version
