# tests/css/test_type_scale.py

**What it tests:** Tests for the type scale and font loading (issue #29).

**Code it covers:** `src/capy_theme/css/`

**Its 9 tests** (each name says what must hold):

- heading sizes follow the scale
- type css
- the issue check base size scales the page
- the issue check base size has a minimum
- admin form stores type settings
- preload picks the regular latin file of body and heading
- no preload for system fonts
- editor offers type controls
- base rules beat tailwinds reset whatever the order

Run just this file with `uv run pytest tests/css/test_type_scale.py`.
