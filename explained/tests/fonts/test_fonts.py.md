# tests/fonts/test_fonts.py

**What it tests:** Tests for the font library and font roles (issue #23).

**Code it covers:** `src/capy_theme/fonts/`

**Its 14 tests** (each name says what must hold):

- font and files
- theme picks fonts by role and snapshot copies them
- no fonts key without fonts
- the issue check heading font in the stylesheet
- body and mono set tailwinds variables
- default fallbacks by role
- published fonts dont change when the library does
- unknown font cant be saved
- bad role is rejected by the schema
- admin form picks fonts for roles
- font admin pages
- editor offers fonts and previews them
- editor refuses unknown fonts
- editor state lists fonts

Run just this file with `uv run pytest tests/fonts/test_fonts.py`.
