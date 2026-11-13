# tests/images/test_animation_limits.py

**What it tests:** Limits on animated images, so one upload can't use huge amounts of memory or time (issue #188). The project settings that change them are tested in tests/test_project_settings.py.

**Code it covers:** `src/capy_theme/images/`

**Its 15 tests** (each name says what must hold):

- the issue check a small file with many frames is refused
- too many pixels in all is refused
- animated frames bigger than the animation limit are refused
- frames reaching past the edges are refused
- a one frame gif cant get past the slots size either
- a frame with no pixels is refused
- frames exactly at the edges are fine
- normal animations and still images are accepted
- still images arent limited by the animation settings
- a later frame with a cut off color table
- a later frame with a cut off header
- a later frame with too little data
- frame extent reads every frame
- frame extent accepts a missing trailer but not a cut block
- frame extent refuses junk where a block should start

Run just this file with `uv run pytest tests/images/test_animation_limits.py`.
