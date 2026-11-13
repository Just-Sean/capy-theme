# tests/images/test_animated_gifs.py

**What it tests:** Animated GIF uploads: metadata, timing, transparency and disposal survive the cleaning (issues #185 and #189). Limits on animations are in test_animation_limits.py.

**Code it covers:** `src/capy_theme/images/`

**Its 9 tests** (each name says what must hold):

- animated gifs keep every frame
- animated gif comments are removed from every frame
- animated gifs keep only the looping and frame blocks
- animated gifs keep their timing and looping
- animated gifs keep their transparency
- animated gifs look the same after cleaning
- frame disposals are read from the file
- identical frames with different disposals dont crash
- the frame reader handles short and odd files

Run just this file with `uv run pytest tests/images/test_animated_gifs.py`.
