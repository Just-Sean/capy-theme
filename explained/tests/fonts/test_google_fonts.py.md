# tests/fonts/test_google_fonts.py

**What it tests:** Tests for importing Google Fonts (issue #27). No network: downloads are faked.

**Code it covers:** `src/capy_theme/fonts/`

**Its 20 tests** (each name says what must hold):

- parse reads each face
- css url
- import stores the files locally
- pages load the font from this site never from google
- missing weights are skipped
- chosen subsets only
- unknown family is reported
- bad names and duplicates are refused
- only google addresses are downloaded
- admin import page
- admin import shows errors
- every weight gets a rule even when files are shared
- fetch sends a browser user agent and a timeout
- lookalike addresses are never downloaded
- file addresses not on fonts gstatic are refused
- faces without an https address are skipped
- google unreachable is a clear error
- a server error isnt mistaken for a missing weight
- a server error while retrying each weight is raised
- a server error tells the user google couldnt be reached

Run just this file with `uv run pytest tests/fonts/test_google_fonts.py`.
