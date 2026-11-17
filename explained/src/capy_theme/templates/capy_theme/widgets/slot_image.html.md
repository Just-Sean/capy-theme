# src/capy_theme/templates/capy_theme/widgets/slot_image.html

**What it is:** one image slot and mode on the theme edit page (`admin/slot_image.py`, #271):

- **the saved image:** the image saved for the slot, with "Saved:", its file name, size in px and file size, or the slot's empty text (e.g. "No image: the main logo is used.")
- **the image to use:** a dropdown of this slot's uploads ("Image to use: None", or "Same as light" for dark). The field's own label (e.g. "Main logo (light)") is for it.
- **Alt text of the saved image** (named by its file): a text box (at most 200 characters), only when there's a saved image, with a hidden field saying which image it belongs to
- **Upload a new image:** a file input, limited to the file types the slot takes ("it replaces the saved one when you save", or "it's used when you save" for an empty slot), and **Alt text for the new image**

Each input has its own label. No inline styles: the look is in `static/capy_theme/admin/images.css`.
