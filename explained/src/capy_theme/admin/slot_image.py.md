# src/capy_theme/admin/slot_image.py

**What it is:** one image slot (and mode) on the theme edit page, with everything in one place (#271): the current image, a choice of earlier uploads, a new upload and the alt text.

- **`SlotImageWidget`:** draws `widgets/slot_image.html`:
  - a preview of the current image with its size, or the slot's empty text
  - a dropdown of this slot's uploads
  - a file input (it only offers SVG where the slot allows it)
  - the alt text box
  - its value is `{"choice", "upload", "alt"}`
  - it needs a multipart form, and loads `admin/images.css`
- **`SlotImageField`:** checks that value:
  - the choice must be one of this slot's images
  - a new upload goes through `uploads.prepare_upload` (too big is refused before reading it, then the usual checks)
  - alt text is trimmed and cut to 200 characters
  - it counts as changed when there's an upload, a different choice, or edited alt text

The upload is only checked here. `form_images.save_images` stores it once the theme is saved.
