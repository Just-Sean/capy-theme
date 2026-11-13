# tests/artifacts/test_api.py

**What it tests:** Tests for the JSON API, in its plain Django and DRF modes (issue #52).

**Code it covers:** `src/capy_theme/artifacts/`

**Its 12 tests** (each name says what must hold):

- returns the artifacts
- the issue check etag gives 304
- a new publish changes the etag
- both modes give identical json
- no published theme is 404
- drf mode stays public whatever the projects defaults
- auto uses drf when installed
- auto uses django without drf
- drf mode needs drf
- unknown mode is an error
- the issue check listed in the generated api docs
- not in the api docs in django mode

Run just this file with `uv run pytest tests/artifacts/test_api.py`.
