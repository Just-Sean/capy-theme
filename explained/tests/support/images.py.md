# tests/support/images.py

**What it is:** builders for test GIFs, shared by the animated GIF, animation limit and upload tests.

- **`gif()`:** a normal GIF via Pillow, with a chosen number of frames, comment, timing, looping and transparency.
- **`hand_built_gif()`:** GIF bytes assembled by hand, for edge cases Pillow won't write: frames reaching past the edges, mixed disposal, damaged or cut-off blocks.
- **`many_frames_gif()`:** a small file with many frames, to test the animation limits.
- **`reopen()`:** opens a cleaned upload again to inspect it.
