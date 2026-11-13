# src/capy_theme/images/gif_frames.py

**What it is:** a small GIF reader that walks the file's block structure **without decoding any pixels**. It exists for safety (issues #188 and #189).

- **`frame_extent(data)`:** the number of frames, and the size the image really reaches once every frame is placed. A GIF states one size, but each frame has its own position and size and can reach past it. Pillow would then grow the image during decoding, after any size check. The upload code compares the two and refuses a mismatch.
- **`frame_disposals(data)`:** how each frame is cleared before the next (leave, clear to background, restore). Re-saving keeps this, so animations don't show leftover frames.
- **`_blocks(data)`:** a generator that yields one block at a time, so memory stays flat however many blocks there are.

It's stricter than Pillow on purpose. Stray bytes, an empty frame or a cut-off file raise `BrokenGif`, which becomes "not a supported image".
