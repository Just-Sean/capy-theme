# src/capy_theme/static/capy_theme/admin/images.css

**What it is:** the look of the image slots on the theme edit page (`widgets/slot_image.html`) and the previews in the **Media** list (#271).

- The current image and the inputs sit side by side and wrap on narrow screens.
- Previews are at most 10 × 5 rem, on a checkerboard so transparent and white images can be seen.
- It uses the admin's own color variables where it can, with plain fallbacks.

It's loaded by `SlotImageWidget`'s `Media`, so it's only on pages with an image slot.
